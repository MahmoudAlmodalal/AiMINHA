from django.db import migrations

GUARDS = r"""
CREATE FUNCTION catalog_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable catalog evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER catalog_source_version_immutable BEFORE UPDATE OR DELETE ON catalog_sourcerevision
FOR EACH ROW EXECUTE FUNCTION catalog_immutable();
CREATE TRIGGER catalog_version_immutable BEFORE UPDATE OR DELETE ON catalog_scholarshipversion
FOR EACH ROW EXECUTE FUNCTION catalog_immutable();
CREATE TRIGGER catalog_event_immutable BEFORE UPDATE OR DELETE ON catalog_moderationevent
FOR EACH ROW EXECUTE FUNCTION catalog_immutable();
CREATE TRIGGER catalog_audit_immutable BEFORE UPDATE OR DELETE ON catalog_catalogaudit
FOR EACH ROW EXECUTE FUNCTION catalog_immutable();

CREATE FUNCTION catalog_admin_proof(actor uuid, proof bigint, scope text) RETURNS boolean
LANGUAGE sql STABLE AS $$
SELECT EXISTS (
  SELECT 1 FROM identity_account a JOIN identity_identitysession s ON s.account_id=a.id
  WHERE a.id=actor AND a.role='ADMIN' AND a.state='ACTIVE' AND a.email_verified_at IS NOT NULL
    AND a.admin_scopes ? scope AND s.id=proof AND s.epoch=a.session_epoch
    AND s.revoked_at IS NULL AND s.expires_at > statement_timestamp()
    AND s.last_seen_at > statement_timestamp()-interval '24 hours'
    AND s.mfa_verified_at <= statement_timestamp()
    AND s.mfa_verified_at > statement_timestamp()-interval '15 minutes'
) $$;

CREATE FUNCTION catalog_source_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT catalog_admin_proof(NEW.editor_id, NEW.session_proof_id, 'MODERATION') THEN
    RAISE EXCEPTION 'catalog source editor proof required' USING ERRCODE='23514';
  END IF;
  IF NEW.permission_status='APPROVED' AND (
    NOT catalog_admin_proof(NEW.editor_id, NEW.session_proof_id, 'SOURCE_APPROVAL') OR
    length(btrim(NEW.license_basis))=0 OR length(btrim(NEW.permission_evidence))=0 OR
    NEW.date_checked IS NULL OR NEW.date_checked > statement_timestamp() OR
    (NEW.valid_until IS NOT NULL AND NEW.valid_until <= statement_timestamp())
  ) THEN
    RAISE EXCEPTION 'individually checked source permission required' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER catalog_source_evidence_guard BEFORE INSERT ON catalog_sourcerevision
FOR EACH ROW EXECUTE FUNCTION catalog_source_evidence();

CREATE FUNCTION catalog_source_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.revision <> OLD.revision+1 OR NOT EXISTS (
    SELECT 1 FROM catalog_sourcerevision v WHERE v.id=NEW.current_id
      AND v.source_id=NEW.id AND v.revision=NEW.revision
  ) THEN RAISE EXCEPTION 'invalid source head' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER catalog_source_head_guard BEFORE UPDATE ON catalog_source
FOR EACH ROW EXECUTE FUNCTION catalog_source_head();

CREATE FUNCTION catalog_version_search() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE permission catalog_sourcerevision;
BEGIN
  SELECT v.* INTO permission FROM catalog_sourcerevision v
    JOIN catalog_source s ON s.current_id=v.id WHERE v.id=NEW.source_revision_id FOR UPDATE OF s;
  IF permission.id IS NULL OR permission.permission_status <> 'APPROVED'
    OR permission.date_checked IS NULL
    OR (permission.valid_until IS NOT NULL AND permission.valid_until <= statement_timestamp())
    OR (NEW.origin='MANUAL' AND NOT permission.allow_manual)
    OR (NEW.origin='IMPORT' AND NOT permission.allow_import) THEN
    RAISE EXCEPTION 'source use denied' USING ERRCODE='23514';
  END IF;
  IF jsonb_typeof(NEW.rounds) <> 'array' OR jsonb_array_length(NEW.rounds)=0 THEN
    RAISE EXCEPTION 'explicit deadline uncertainty required' USING ERRCODE='23514';
  END IF;
  NEW.search_document :=
    setweight(to_tsvector('simple', NEW.title || ' ' || NEW.provider), 'A') ||
    setweight(to_tsvector('simple', NEW.summary || ' ' || NEW.disciplines::text || ' ' ||
      NEW.countries::text || ' ' || NEW.education_levels::text || ' ' || NEW.languages::text), 'B');
  RETURN NEW;
END $$;
CREATE TRIGGER catalog_version_search_guard BEFORE INSERT ON catalog_scholarshipversion
FOR EACH ROW EXECUTE FUNCTION catalog_version_search();

CREATE FUNCTION catalog_moderation_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT catalog_admin_proof(NEW.actor_id, NEW.session_proof_id, 'MODERATION') OR
    NEW.action NOT IN ('APPROVE','REJECT','REVERIFY','SUSPEND','ARCHIVE','RESTORE') OR
    length(btrim(NEW.reason))=0 OR NOT EXISTS (
      SELECT 1 FROM catalog_scholarshipversion v WHERE v.id=NEW.version_id
      AND v.scholarship_id=NEW.scholarship_id AND v.content_hash=NEW.content_hash
    ) THEN RAISE EXCEPTION 'exact human moderation evidence required' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER catalog_moderation_evidence_guard BEFORE INSERT ON catalog_moderationevent
FOR EACH ROW EXECUTE FUNCTION catalog_moderation_evidence();

CREATE FUNCTION catalog_scholarship_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v catalog_scholarshipversion;
DECLARE source_permission catalog_sourcerevision;
DECLARE last_action text;
BEGIN
  IF NEW.revision <> OLD.revision+1 THEN
    RAISE EXCEPTION 'catalog revision must advance once' USING ERRCODE='23514';
  END IF;
  SELECT * INTO v FROM catalog_scholarshipversion WHERE id=NEW.latest_id;
  IF v.id IS NULL OR v.scholarship_id <> NEW.id THEN
    RAISE EXCEPTION 'candidate belongs to another listing' USING ERRCODE='23514';
  END IF;
  IF NEW.published_version_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM catalog_scholarshipversion p WHERE p.id=NEW.published_version_id
      AND p.scholarship_id=NEW.id
  ) THEN RAISE EXCEPTION 'publication belongs to another listing' USING ERRCODE='23514'; END IF;
  IF NEW.visibility='PUBLISHED' THEN
    SELECT * INTO source_permission FROM catalog_sourcerevision
      WHERE id=(SELECT current_id FROM catalog_source WHERE id=(
        SELECT source_id FROM catalog_sourcerevision WHERE id=v.source_revision_id
      ));
    SELECT e.action INTO last_action FROM catalog_moderationevent e
      WHERE e.scholarship_id=NEW.id AND e.version_id=v.id AND e.content_hash=v.content_hash
      ORDER BY e.created_at DESC, e.id DESC LIMIT 1;
    IF NEW.published_version_id IS DISTINCT FROM v.id OR
      last_action IS NULL OR last_action <> 'APPROVE' OR
      source_permission.id IS DISTINCT FROM v.source_revision_id OR
      source_permission.permission_status <> 'APPROVED' OR
      source_permission.date_checked IS NULL OR
      (source_permission.valid_until IS NOT NULL AND
        source_permission.valid_until <= statement_timestamp()) OR
      (v.origin='MANUAL' AND NOT source_permission.allow_manual) OR
      (v.origin='IMPORT' AND NOT source_permission.allow_import) THEN
      RAISE EXCEPTION 'unapproved or unpermitted publication' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER catalog_scholarship_head_guard BEFORE UPDATE ON catalog_scholarship
FOR EACH ROW EXECUTE FUNCTION catalog_scholarship_head();

CREATE FUNCTION catalog_complete_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='catalog_source' THEN
    IF NOT EXISTS (SELECT 1 FROM catalog_source s JOIN catalog_sourcerevision v ON v.id=s.current_id
                   WHERE s.id=NEW.id AND v.source_id=s.id AND v.revision=s.revision) THEN
      RAISE EXCEPTION 'source must commit complete' USING ERRCODE='23514';
    END IF;
  ELSE
    IF NOT EXISTS (SELECT 1 FROM catalog_scholarship s
                   JOIN catalog_scholarshipversion v ON v.id=s.latest_id
                   WHERE s.id=NEW.id AND v.scholarship_id=s.id) THEN
      RAISE EXCEPTION 'listing must commit complete' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER catalog_source_complete AFTER INSERT OR UPDATE ON catalog_source
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION catalog_complete_head();
CREATE CONSTRAINT TRIGGER catalog_scholarship_complete AFTER INSERT OR UPDATE ON catalog_scholarship
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION catalog_complete_head();
"""


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]
    # Forward-only evidence guards; no automatic removal from populated environments.
    operations = [migrations.RunSQL(GUARDS)]
