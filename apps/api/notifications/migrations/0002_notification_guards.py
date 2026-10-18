from django.db import migrations

GUARDS = r"""
CREATE FUNCTION notifications_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable notification evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER notifications_versions_immutable BEFORE UPDATE OR DELETE
ON notifications_deadlineversion
FOR EACH ROW EXECUTE FUNCTION notifications_immutable();
CREATE TRIGGER notifications_audit_immutable BEFORE UPDATE OR DELETE
ON notifications_notificationaudit
FOR EACH ROW EXECUTE FUNCTION notifications_immutable();

CREATE FUNCTION notifications_active_student(who uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
SELECT EXISTS(SELECT 1 FROM identity_account u WHERE u.id=who AND u.role='STUDENT'
 AND u.state='ACTIVE' AND u.email_verified_at IS NOT NULL
 AND u.birth_date <= (statement_timestamp() AT TIME ZONE 'UTC')::date-INTERVAL '18 years')
$$;
CREATE FUNCTION notifications_current_source(ver uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
SELECT EXISTS(
 SELECT 1 FROM catalog_scholarshipversion v JOIN catalog_scholarship s ON s.id=v.scholarship_id
 JOIN catalog_sourcerevision p ON p.id=v.source_revision_id
 JOIN catalog_source src ON src.current_id=p.id
 WHERE v.id=ver AND s.visibility='PUBLISHED' AND s.published_version_id=v.id AND s.latest_id=v.id
 AND p.permission_status='APPROVED' AND p.date_checked<=statement_timestamp()
 AND length(btrim(p.license_basis))>0 AND length(btrim(p.permission_evidence))>0
 AND (p.valid_until IS NULL OR p.valid_until>statement_timestamp())
 AND ((v.origin='MANUAL' AND p.allow_manual) OR (v.origin='IMPORT' AND p.allow_import))
 AND p.freshness_days IS NOT NULL AND v.source_checked_at<=statement_timestamp()
 AND v.source_checked_at+make_interval(days=>p.freshness_days)>statement_timestamp()
 AND EXISTS(SELECT 1 FROM catalog_moderationevent m WHERE m.version_id=v.id
  AND m.scholarship_id=s.id AND m.action='APPROVE' AND m.content_hash=v.content_hash))
$$;
CREATE FUNCTION notifications_relationship(who uuid, ev uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
SELECT EXISTS(SELECT 1 FROM notifications_deadlineevent e WHERE e.id=ev AND (
 EXISTS(SELECT 1 FROM applications_savedscholarship s WHERE s.owner_id=who
  AND s.scholarship_id=e.scholarship_id AND s.active)
 OR EXISTS(SELECT 1 FROM applications_application a WHERE a.owner_id=who
  AND a.scholarship_id=e.scholarship_id AND a.round_key=e.round_key
  AND a.state NOT IN ('ACCEPTED','REJECTED','WITHDRAWN'))))
$$;

CREATE FUNCTION notifications_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE scholarship uuid; fact catalog_scholarshipversion; matched boolean;
BEGIN
 SELECT e.scholarship_id INTO scholarship FROM notifications_deadlineevent e
 WHERE e.id=NEW.event_id;
 SELECT * INTO fact FROM catalog_scholarshipversion v WHERE v.id=NEW.scholarship_version_id;
 IF NEW.version<1 OR fact.scholarship_id IS DISTINCT FROM scholarship THEN
  RAISE EXCEPTION 'deadline version scholarship mismatch' USING ERRCODE='23514'; END IF;
 IF NEW.state<>'CANCELLED' THEN
  SELECT EXISTS(SELECT 1 FROM jsonb_array_elements(fact.rounds) r WHERE r=NEW.source_round)
   INTO matched;
  -- Empty source rounds map to one explicitly UNKNOWN fallback, never a fixed instant.
  IF NOT notifications_current_source(NEW.scholarship_version_id) OR
   (NOT matched AND NOT (NEW.state='UNKNOWN' AND jsonb_array_length(fact.rounds)=0
                        AND NEW.source_round->>'kind'='UNKNOWN')) THEN
   RAISE EXCEPTION 'exact published source round required' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.state='CONFIRMED' AND (
   NEW.source_round->>'kind' IS DISTINCT FROM 'CONFIRMED'
   OR NEW.source_round->>'timezone' IS DISTINCT FROM NEW.source_timezone
   OR NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=NEW.source_timezone)
   OR length(btrim(COALESCE(NEW.source_round->>'source_text','')))=0
   OR (NEW.source_round->>'closes_at')::timestamptz IS DISTINCT FROM NEW.closes_at) THEN
  RAISE EXCEPTION 'verified instant and source timezone required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notifications_version_evidence BEFORE INSERT ON notifications_deadlineversion
FOR EACH ROW EXECUTE FUNCTION notifications_version_guard();

CREATE FUNCTION notifications_head_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.scholarship_id<>OLD.scholarship_id OR NEW.round_key<>OLD.round_key
  OR NEW.revision<>OLD.revision+1 OR NOT EXISTS(
   SELECT 1 FROM notifications_deadlineversion v WHERE v.id=NEW.current_id
   AND v.event_id=NEW.id AND v.version=NEW.revision) THEN
  RAISE EXCEPTION 'invalid deadline head' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notifications_head_update BEFORE UPDATE ON notifications_deadlineevent
FOR EACH ROW EXECUTE FUNCTION notifications_head_guard();
CREATE FUNCTION notifications_head_complete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM notifications_deadlineevent e JOIN notifications_deadlineversion v
  ON e.current_id=v.id WHERE e.id=NEW.id AND v.event_id=e.id AND v.version=e.revision) THEN
  RAISE EXCEPTION 'deadline head must commit complete' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER notifications_head_complete_guard AFTER INSERT OR UPDATE
ON notifications_deadlineevent DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION notifications_head_complete();

CREATE FUNCTION notifications_reminder_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE ev notifications_deadlineevent; ver notifications_deadlineversion;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'reminder history immutable' USING ERRCODE='23514'; END IF;
 SELECT * INTO ev FROM notifications_deadlineevent WHERE id=NEW.event_id;
 SELECT * INTO ver FROM notifications_deadlineversion WHERE id=NEW.event_version_id;
 IF ver.event_id IS DISTINCT FROM NEW.event_id OR ver.state<>'CONFIRMED'
  OR NEW.due_at IS DISTINCT FROM ver.closes_at-make_interval(mins=>NEW.offset_minutes) THEN
  RAISE EXCEPTION 'exact source reminder instant required' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' AND NEW.status<>'SCHEDULED' THEN
  RAISE EXCEPTION 'reminder starts scheduled' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (
  OLD.status<>'SCHEDULED' OR NEW.status NOT IN ('CANCELLED','DELIVERED')
  OR NEW.id<>OLD.id OR NEW.owner_id<>OLD.owner_id OR NEW.event_id<>OLD.event_id
  OR NEW.event_version_id<>OLD.event_version_id OR NEW.due_at<>OLD.due_at
  OR NEW.offset_minutes<>OLD.offset_minutes OR NEW.created_at<>OLD.created_at) THEN
  RAISE EXCEPTION 'only scheduled reminder can finalize once' USING ERRCODE='23514'; END IF;
 IF NEW.status IN ('SCHEDULED','DELIVERED') AND (
  ev.current_id IS DISTINCT FROM ver.id
  OR NOT notifications_current_source(ver.scholarship_version_id)
  OR NOT notifications_active_student(NEW.owner_id)
  OR NOT notifications_relationship(NEW.owner_id,NEW.event_id)
  OR EXISTS(SELECT 1 FROM notifications_notificationpreference p WHERE p.owner_id=NEW.owner_id
            AND NOT p.deadline_enabled)) THEN
  RAISE EXCEPTION 'live source and recipient required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notifications_reminder_lifecycle BEFORE INSERT OR UPDATE OR DELETE
ON notifications_deadlinereminder FOR EACH ROW EXECUTE FUNCTION notifications_reminder_guard();

CREATE FUNCTION notifications_inbox_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rem notifications_deadlinereminder; ver notifications_deadlineversion;
 app applications_application; req applications_applicationrequirement;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'inbox history immutable' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' THEN
  IF (to_jsonb(NEW)-'read_at') IS DISTINCT FROM (to_jsonb(OLD)-'read_at')
   OR OLD.read_at IS NOT NULL OR NEW.read_at IS NULL THEN
   RAISE EXCEPTION 'inbox allows one read acknowledgment only' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF NOT notifications_active_student(NEW.owner_id) OR NEW.read_at IS NOT NULL THEN
  RAISE EXCEPTION 'active owned inbox recipient required' USING ERRCODE='23514'; END IF;
 IF NEW.application_id IS NOT NULL THEN
  SELECT * INTO app FROM applications_application WHERE id=NEW.application_id;
  IF app.owner_id IS DISTINCT FROM NEW.owner_id THEN
   RAISE EXCEPTION 'private notification destination ownership' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.category='DEADLINE' THEN
  SELECT * INTO rem FROM notifications_deadlinereminder WHERE id=NEW.reminder_id;
  SELECT * INTO ver FROM notifications_deadlineversion WHERE id=rem.event_version_id;
  IF rem.owner_id IS DISTINCT FROM NEW.owner_id OR NEW.event_id IS DISTINCT FROM rem.id
   OR NEW.event_version IS DISTINCT FROM ver.version OR rem.status<>'SCHEDULED'
   OR NOT notifications_current_source(ver.scholarship_version_id)
   OR NOT notifications_relationship(NEW.owner_id,rem.event_id)
   OR EXISTS(SELECT 1 FROM notifications_deadlineevent e WHERE e.id=rem.event_id
     AND (e.current_id<>ver.id OR COALESCE(NEW.scholarship_id,app.scholarship_id)<>e.scholarship_id
       OR (NEW.application_id IS NOT NULL AND app.round_key<>e.round_key))) THEN
   RAISE EXCEPTION 'one exact owned reminder destination required' USING ERRCODE='23514'; END IF;
 ELSIF NEW.category='SOURCE_CHANGE' THEN
  IF NEW.application_id IS NULL OR NEW.event_id IS DISTINCT FROM app.id OR NOT EXISTS(
   SELECT 1 FROM catalog_scholarshipversion v WHERE v.scholarship_id=app.scholarship_id
    AND v.version=NEW.event_version AND v.id<>app.scholarship_version_id
    AND notifications_current_source(v.id)) OR EXISTS(
   SELECT 1 FROM notifications_notificationpreference p WHERE p.owner_id=NEW.owner_id
    AND NOT p.source_enabled) THEN
   RAISE EXCEPTION 'verified source change evidence required' USING ERRCODE='23514'; END IF;
 ELSIF NEW.category='DOCUMENT_MISSING' THEN
  SELECT * INTO req FROM applications_applicationrequirement WHERE id=NEW.event_id;
  IF NEW.application_id IS NULL OR req.application_id IS DISTINCT FROM app.id
   OR req.scholarship_version_id IS DISTINCT FROM app.scholarship_version_id
   OR NEW.event_version<>1 OR NOT app.requirements_known
   OR app.state NOT IN ('PREPARING','READY')
   OR NOT notifications_current_source(app.scholarship_version_id)
   OR EXISTS(SELECT 1 FROM applications_selectedartifact a WHERE a.requirement_id=req.id
     AND applications_artifact_valid(NEW.owner_id,a.version_id,a.asset_id,a.content_hash))
   OR EXISTS(SELECT 1 FROM notifications_notificationpreference p WHERE p.owner_id=NEW.owner_id
             AND NOT p.document_enabled) THEN
   RAISE EXCEPTION 'exact known missing requirement required' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notifications_inbox_lifecycle BEFORE INSERT OR UPDATE OR DELETE
ON notifications_notification FOR EACH ROW EXECUTE FUNCTION notifications_inbox_guard();

CREATE FUNCTION notifications_delivery_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid; state text; linked integer;
BEGIN
 IF TG_TABLE_NAME='notifications_deadlinereminder' THEN rid=NEW.id;
 ELSE rid=NEW.reminder_id; END IF;
 IF rid IS NULL THEN RETURN NULL; END IF;
 SELECT status INTO state FROM notifications_deadlinereminder WHERE id=rid;
 SELECT count(*) INTO linked FROM notifications_notification WHERE reminder_id=rid;
 IF (state='DELIVERED' AND linked<>1) OR (state<>'DELIVERED' AND linked<>0) THEN
  RAISE EXCEPTION 'delivery and one inbox effect must commit atomically'
  USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER notifications_delivery_complete_reminder AFTER INSERT OR UPDATE
ON notifications_deadlinereminder DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION notifications_delivery_complete();
CREATE CONSTRAINT TRIGGER notifications_delivery_complete_inbox AFTER INSERT
ON notifications_notification DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION notifications_delivery_complete();

CREATE FUNCTION notifications_preference_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=NEW.timezone) THEN
  RAISE EXCEPTION 'valid IANA display timezone required' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.owner_id<>OLD.owner_id OR NEW.revision<>OLD.revision+1) THEN
  RAISE EXCEPTION 'preference owner and revision protected' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER notifications_preference_lifecycle BEFORE INSERT OR UPDATE
ON notifications_notificationpreference
FOR EACH ROW EXECUTE FUNCTION notifications_preference_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial"), ("applications", "0002_application_guards")]
    operations = [migrations.RunSQL(GUARDS)]
