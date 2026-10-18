from django.db import migrations

SQL = r"""
CREATE FUNCTION applications_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION
'application evidence is immutable; legal erasure requires approved scoped lifecycle' ; END $$;
CREATE TRIGGER applications_event_immutable BEFORE UPDATE OR DELETE ON applications_applicationevent
FOR EACH ROW EXECUTE FUNCTION applications_immutable();
CREATE TRIGGER applications_requirement_immutable BEFORE UPDATE OR DELETE ON
applications_applicationrequirement
FOR EACH ROW EXECUTE FUNCTION applications_immutable();
CREATE TRIGGER applications_submission_immutable BEFORE UPDATE OR DELETE ON
applications_submissionartifact
FOR EACH ROW EXECUTE FUNCTION applications_immutable();
CREATE TRIGGER applications_official_immutable BEFORE UPDATE OR DELETE ON
applications_officialstatusreport
FOR EACH ROW EXECUTE FUNCTION applications_immutable();
CREATE TRIGGER applications_deletion_immutable BEFORE UPDATE OR DELETE ON
applications_submittedartifactdeletionrequest
FOR EACH ROW EXECUTE FUNCTION applications_immutable();

CREATE FUNCTION applications_current_catalog(target uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT EXISTS(SELECT 1 FROM catalog_scholarshipversion v
 JOIN catalog_scholarship s ON s.id=v.scholarship_id
 JOIN catalog_sourcerevision r ON r.id=v.source_revision_id
 JOIN catalog_source src ON src.id=r.source_id
 WHERE v.id=target AND s.visibility='PUBLISHED' AND s.published_version_id=v.id
 AND s.latest_id=v.id AND src.current_id=r.id AND r.permission_status='APPROVED'
 AND r.date_checked<=statement_timestamp()
 AND (r.valid_until IS NULL OR r.valid_until>statement_timestamp())
 AND ((v.origin='MANUAL' AND r.allow_manual) OR (v.origin='IMPORT' AND r.allow_import))
 AND EXISTS(SELECT 1 FROM catalog_moderationevent e WHERE e.scholarship_id=s.id
 AND e.version_id=v.id AND e.action='APPROVE' AND e.content_hash=v.content_hash));
$$;

CREATE FUNCTION applications_artifact_valid(own uuid, ver uuid, ast uuid, hash text)
RETURNS boolean LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN ver IS NOT NULL AND ast IS NULL THEN EXISTS(
 SELECT 1 FROM documents_documentversion v JOIN documents_documentapproval a ON a.version_id=v.id
 WHERE v.id=ver AND v.owner_id=own AND a.owner_id=own
 AND v.content_hash=hash AND a.content_hash=hash)
 WHEN ast IS NOT NULL AND ver IS NULL THEN EXISTS(
 SELECT 1 FROM privacy_privateasset a
 JOIN private_files_storedfile f ON f.asset_id=a.id
 JOIN private_files_scanreceipt scan ON scan.file_id=f.asset_id
 WHERE a.id=ast AND a.owner_id=own AND a.state='ACCEPTED'
 AND f.capacity_state='RETAINED' AND f.sha256=hash
 AND scan.sha256=f.sha256 AND scan.size=f.size AND scan.verdict='CLEAN') ELSE false END;
$$;

CREATE FUNCTION applications_check_requirement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a applications_application; v catalog_scholarshipversion;
BEGIN
 SELECT * INTO STRICT a FROM applications_application WHERE id=NEW.application_id FOR UPDATE;
 SELECT * INTO STRICT v FROM catalog_scholarshipversion WHERE id=NEW.scholarship_version_id;
 IF a.state<>'PREPARING' OR a.submitted_sequence IS NOT NULL OR v.scholarship_id<>a.scholarship_id
 OR v.required_documents->>NEW.position IS DISTINCT FROM NEW.label
 OR NEW.key<>encode(sha256(convert_to(NEW.position::text||':'||NEW.label,'UTF8')),'hex')
 THEN RAISE EXCEPTION 'requirement must preserve exact reviewed document label'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_requirement_check BEFORE INSERT ON applications_applicationrequirement
FOR EACH ROW EXECUTE FUNCTION applications_check_requirement();

CREATE FUNCTION applications_check_selection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a applications_application; r applications_applicationrequirement; target uuid;
BEGIN
 IF TG_OP='DELETE' THEN target:=OLD.requirement_id; ELSE target:=NEW.requirement_id; END IF;
 SELECT * INTO STRICT r FROM applications_applicationrequirement WHERE id=target;
 SELECT * INTO STRICT a FROM applications_application WHERE id=r.application_id FOR UPDATE;
 IF a.state<>'PREPARING' OR a.submitted_sequence IS NOT NULL THEN
 RAISE EXCEPTION 'manifest is frozen outside Preparing'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 IF TG_OP='UPDATE' AND NEW.requirement_id<>OLD.requirement_id THEN
 RAISE EXCEPTION 'selection requirement cannot move'; END IF;
 IF r.scholarship_version_id<>a.scholarship_version_id OR NOT applications_artifact_valid(
 a.owner_id,NEW.version_id,NEW.asset_id,NEW.content_hash) THEN
 RAISE EXCEPTION 'selection needs owned exact approved/scanned artifact'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_selection_check BEFORE INSERT OR UPDATE OR DELETE ON
applications_selectedartifact
FOR EACH ROW EXECUTE FUNCTION applications_check_selection();

CREATE FUNCTION applications_manifest(app uuid, ver uuid) RETURNS jsonb LANGUAGE sql STABLE AS $$
 SELECT coalesce(jsonb_agg(jsonb_build_object('key',r.key,'version_id',s.version_id,
 'asset_id',s.asset_id,'content_hash',s.content_hash) ORDER BY r.position),'[]'::jsonb)
FROM applications_applicationrequirement r JOIN applications_selectedartifact s ON
s.requirement_id=r.id
 WHERE r.application_id=app AND r.scholarship_version_id=ver;
$$;

CREATE FUNCTION applications_check_event() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a applications_application; prior applications_applicationevent;
 actor identity_account; proof identity_identitysession; v catalog_scholarshipversion;
 known_count int; attached_count int;
BEGIN
 SELECT * INTO STRICT a FROM applications_application WHERE id=NEW.application_id FOR UPDATE;
 SELECT * INTO STRICT actor FROM identity_account WHERE id=NEW.actor_id;
 SELECT * INTO STRICT proof FROM identity_identitysession WHERE id=NEW.session_proof_id;
 SELECT * INTO STRICT v FROM catalog_scholarshipversion WHERE id=NEW.scholarship_version_id;
 NEW.recorded_at:=clock_timestamp();
 IF NEW.actor_id<>a.owner_id OR actor.role<>'STUDENT' OR actor.state<>'ACTIVE'
 OR actor.email_verified_at IS NULL OR actor.birth_date>(current_date-interval '18 years')::date
 OR proof.account_id<>a.owner_id OR proof.epoch<>actor.session_epoch OR proof.revoked_at IS NOT NULL
OR proof.expires_at<=statement_timestamp() OR proof.last_seen_at+interval '24 hours'
<=statement_timestamp()
 OR NEW.source<>'STUDENT_REPORTED' OR NEW.sequence<>a.revision+1
 OR NEW.observed_at>NEW.recorded_at OR length(NEW.notes_snapshot)>5000
 OR v.scholarship_id<>a.scholarship_id OR (NEW.profile_version_id IS NOT NULL AND NOT EXISTS(
SELECT 1 FROM eligibility_profileversion p WHERE p.id=NEW.profile_version_id AND
p.owner_id=a.owner_id))
 THEN RAISE EXCEPTION 'invalid student application event binding'; END IF;
 IF NEW.manifest_snapshot IS DISTINCT FROM applications_manifest(a.id,v.id) THEN
 RAISE EXCEPTION 'event must snapshot exact current manifest'; END IF;
 IF a.revision=0 THEN
 IF NEW.kind<>'CREATED' OR NEW.from_state<>'' OR NEW.to_state<>'PREPARING'
 OR NEW.scholarship_version_id<>a.scholarship_version_id
 OR NEW.profile_version_id IS DISTINCT FROM a.profile_version_id THEN
 RAISE EXCEPTION 'initial application event must be Preparing'; END IF;
 ELSE
 SELECT * INTO STRICT prior FROM applications_applicationevent WHERE id=a.head_id;
 IF NEW.from_state<>a.state OR (NEW.kind<>'REBASE' AND (
 NEW.scholarship_version_id<>a.scholarship_version_id
 OR NEW.profile_version_id IS DISTINCT FROM a.profile_version_id)) THEN
 RAISE EXCEPTION 'event must continue pinned history'; END IF;
 IF NEW.kind='TRANSITION' THEN
 IF NOT ((a.state='PREPARING' AND NEW.to_state IN ('READY','WITHDRAWN'))
 OR (a.state='READY' AND NEW.to_state IN ('PREPARING','SUBMITTED','WITHDRAWN'))
 OR (a.state='SUBMITTED' AND NEW.to_state IN ('UNDER_REVIEW','ACCEPTED','REJECTED','WITHDRAWN'))
 OR (a.state='UNDER_REVIEW' AND NEW.to_state IN ('ACCEPTED','REJECTED','WITHDRAWN')))
 OR length(btrim(NEW.evidence))=0 THEN RAISE EXCEPTION 'illegal application transition'; END IF;
 ELSIF NEW.kind IN ('NOTES','ARTIFACT','CORRECTION','REBASE') THEN
 IF NEW.to_state<>a.state THEN RAISE EXCEPTION 'activity cannot change state'; END IF;
 IF NEW.kind='ARTIFACT' AND a.state<>'PREPARING' THEN
 RAISE EXCEPTION 'artifact activity outside Preparing'; END IF;
 IF NEW.kind='REBASE' AND (a.state<>'PREPARING' OR a.submitted_sequence IS NOT NULL
 OR NEW.scholarship_version_id=a.scholarship_version_id
 OR NOT applications_current_catalog(NEW.scholarship_version_id)
OR NEW.manifest_snapshot<>'[]'::jsonb) THEN RAISE EXCEPTION 'invalid explicit source rebase' ; END
IF;
 IF NEW.kind IN ('NOTES','CORRECTION') AND NEW.manifest_snapshot<>prior.manifest_snapshot THEN
 RAISE EXCEPTION 'activity cannot alter manifest'; END IF;
 ELSE RAISE EXCEPTION 'unknown application event kind'; END IF;
 IF NEW.kind<>'NOTES' AND NEW.notes_snapshot<>prior.notes_snapshot THEN
 RAISE EXCEPTION 'notes must have explicit notes activity'; END IF;
 END IF;
 IF (NEW.kind='CORRECTION')<>(NEW.correction_of_sequence IS NOT NULL) OR
 (NEW.kind='CORRECTION' AND (length(btrim(NEW.evidence))=0 OR length(btrim(NEW.reason))=0
 OR NOT EXISTS(SELECT 1 FROM applications_applicationevent correction_event
 WHERE correction_event.application_id=a.id
 AND correction_event.sequence=NEW.correction_of_sequence
 AND correction_event.sequence<NEW.sequence))) THEN
 RAISE EXCEPTION 'correction must preserve an earlier evidenced event'; END IF;
 IF NEW.student_submission_confirmation IS DISTINCT FROM
 (NEW.kind='TRANSITION' AND NEW.to_state='SUBMITTED') THEN
 RAISE EXCEPTION 'external submission requires explicit student confirmation'; END IF;
 IF NEW.kind='TRANSITION' AND NEW.to_state IN ('READY','SUBMITTED') THEN
 SELECT count(*) INTO known_count FROM applications_applicationrequirement
 WHERE application_id=a.id AND scholarship_version_id=v.id;
 SELECT count(*) INTO attached_count FROM applications_selectedartifact s
 JOIN applications_applicationrequirement r ON r.id=s.requirement_id
 WHERE r.application_id=a.id AND r.scholarship_version_id=v.id
 AND applications_artifact_valid(a.owner_id,s.version_id,s.asset_id,s.content_hash);
IF NOT a.requirements_known OR known_count=0 OR
known_count<>jsonb_array_length(v.required_documents)
 OR attached_count<>known_count OR NOT applications_current_catalog(v.id) THEN
RAISE EXCEPTION
'Ready/Submitted needs complete current reviewed requirements and exact owned artifacts' ; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_event_check BEFORE INSERT ON applications_applicationevent
FOR EACH ROW EXECUTE FUNCTION applications_check_event();

CREATE FUNCTION applications_check_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e applications_applicationevent; v catalog_scholarshipversion;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'application history cannot be reset'; END IF;
 SELECT * INTO STRICT v FROM catalog_scholarshipversion WHERE id=NEW.scholarship_version_id;
 IF v.scholarship_id<>NEW.scholarship_id OR NEW.round_key!~'^[0-9a-f]{64}$'
 OR NEW.round_snapshot->>'round_key' IS DISTINCT FROM NEW.round_key
 OR NEW.requirements_known IS DISTINCT FROM (jsonb_array_length(v.required_documents)>0)
 OR (NEW.profile_version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM eligibility_profileversion p
 WHERE p.id=NEW.profile_version_id AND p.owner_id=NEW.owner_id)) THEN
 RAISE EXCEPTION 'application source/profile binding invalid'; END IF;
 IF TG_OP='INSERT' THEN
 IF NEW.revision<>0 OR NEW.head_id IS NOT NULL OR NEW.state<>'PREPARING'
 OR NEW.submitted_sequence IS NOT NULL OR NOT applications_current_catalog(v.id) THEN
 RAISE EXCEPTION 'new application starts Preparing with approved source'; END IF;
 RETURN NEW;
 END IF;
 SELECT * INTO STRICT e FROM applications_applicationevent WHERE id=NEW.head_id;
 IF NEW.owner_id<>OLD.owner_id OR NEW.scholarship_id<>OLD.scholarship_id
 OR NEW.round_key<>OLD.round_key OR NEW.created_at<>OLD.created_at
 OR NEW.revision<>OLD.revision+1 OR e.application_id<>NEW.id OR e.sequence<>NEW.revision
 OR e.to_state<>NEW.state OR e.scholarship_version_id<>NEW.scholarship_version_id
 OR e.profile_version_id IS DISTINCT FROM NEW.profile_version_id
 OR (e.kind<>'REBASE' AND (NEW.scholarship_version_id<>OLD.scholarship_version_id
 OR NEW.profile_version_id IS DISTINCT FROM OLD.profile_version_id
 OR NEW.round_snapshot<>OLD.round_snapshot OR NEW.requirements_known<>OLD.requirements_known))
OR (OLD.submitted_sequence IS NOT NULL AND NEW.submitted_sequence IS DISTINCT FROM
OLD.submitted_sequence)
 OR (OLD.submitted_sequence IS NULL AND NEW.submitted_sequence IS DISTINCT FROM
 CASE WHEN e.kind='TRANSITION' AND e.to_state='SUBMITTED' THEN e.sequence ELSE NULL END) THEN
 RAISE EXCEPTION 'application head must CAS-advance one exact owned event'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_head_check BEFORE INSERT OR UPDATE OR DELETE ON applications_application
FOR EACH ROW EXECUTE FUNCTION applications_check_head();

CREATE FUNCTION applications_check_submission() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a applications_application; e applications_applicationevent;
 r applications_applicationrequirement; s applications_selectedartifact;
BEGIN
 SELECT * INTO STRICT a FROM applications_application WHERE id=NEW.application_id FOR UPDATE;
 SELECT * INTO STRICT e FROM applications_applicationevent WHERE id=NEW.event_id;
 SELECT * INTO STRICT r FROM applications_applicationrequirement WHERE id=NEW.requirement_id;
 SELECT * INTO STRICT s FROM applications_selectedartifact WHERE requirement_id=r.id;
 IF a.submitted_sequence IS NULL OR e.sequence<>a.submitted_sequence OR e.application_id<>a.id
 OR e.to_state<>'SUBMITTED' OR NOT e.student_submission_confirmation
 OR r.application_id<>a.id OR r.scholarship_version_id<>e.scholarship_version_id
 OR NEW.version_id IS DISTINCT FROM s.version_id OR NEW.asset_id IS DISTINCT FROM s.asset_id
 OR NEW.content_hash<>s.content_hash OR NEW.label_snapshot<>r.label
 OR NOT applications_artifact_valid(a.owner_id,NEW.version_id,NEW.asset_id,NEW.content_hash) THEN
 RAISE EXCEPTION 'submission must freeze exact owned manifest'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_submission_check BEFORE INSERT ON applications_submissionartifact
FOR EACH ROW EXECUTE FUNCTION applications_check_submission();

CREATE FUNCTION applications_complete() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a applications_application; e applications_applicationevent; target uuid;
BEGIN
 IF TG_TABLE_NAME='applications_application' THEN target:=NEW.id;
 ELSIF TG_TABLE_NAME='applications_selectedartifact' THEN
 SELECT application_id INTO target FROM applications_applicationrequirement
 WHERE id=CASE WHEN TG_OP='DELETE' THEN OLD.requirement_id ELSE NEW.requirement_id END;
 ELSE target:=NEW.application_id; END IF;
 SELECT * INTO STRICT a FROM applications_application WHERE id=target;
 SELECT * INTO STRICT e FROM applications_applicationevent WHERE id=a.head_id;
 IF a.revision=0 OR e.application_id<>a.id OR e.sequence<>a.revision OR e.to_state<>a.state
 OR (SELECT count(*) FROM applications_applicationevent WHERE application_id=a.id)<>a.revision
 OR (SELECT max(sequence) FROM applications_applicationevent WHERE application_id=a.id)<>a.revision
 OR e.manifest_snapshot<>applications_manifest(a.id,a.scholarship_version_id)
 OR (SELECT count(*) FROM applications_applicationrequirement
 WHERE application_id=a.id AND scholarship_version_id=a.scholarship_version_id)<>
(SELECT jsonb_array_length(required_documents) FROM catalog_scholarshipversion WHERE
id=a.scholarship_version_id)
 THEN RAISE EXCEPTION 'incomplete or noncontiguous application history'; END IF;
 IF a.submitted_sequence IS NOT NULL AND (
 (SELECT count(*) FROM applications_submissionartifact WHERE application_id=a.id)<>
 (SELECT count(*) FROM applications_applicationrequirement WHERE application_id=a.id
 AND scholarship_version_id=a.scholarship_version_id)
 OR EXISTS(SELECT 1 FROM applications_submissionartifact s WHERE s.application_id=a.id
 AND s.version_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM documents_submissionsnapshot d
 WHERE d.application_ref=a.id AND d.version_id=s.version_id AND d.owner_id=a.owner_id
 AND d.content_hash=s.content_hash))) THEN
 RAISE EXCEPTION 'submission evidence must be complete and frozen'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER applications_complete_head AFTER INSERT OR UPDATE ON
applications_application
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION applications_complete();
CREATE CONSTRAINT TRIGGER applications_complete_event AFTER INSERT ON applications_applicationevent
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION applications_complete();
CREATE CONSTRAINT TRIGGER applications_complete_selection AFTER INSERT OR UPDATE OR DELETE ON
applications_selectedartifact
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION applications_complete();
CREATE CONSTRAINT TRIGGER applications_complete_requirement AFTER INSERT ON
applications_applicationrequirement
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION applications_complete();
CREATE CONSTRAINT TRIGGER applications_complete_submission AFTER INSERT ON
applications_submissionartifact
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION applications_complete();

CREATE FUNCTION applications_check_official() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.recorded_at:=clock_timestamp();
 IF NEW.origin<>'SYNTHETIC_LOCAL' OR NEW.status<>'UNDER_REVIEW'
 OR NEW.source_url<>'https://synthetic.example.invalid/application-status'
 OR NEW.evidence_ref<>'LOCAL_FIXED_SYNTHETIC_PROOF' OR NEW.observed_at>NEW.recorded_at THEN
 RAISE EXCEPTION 'lawful verified-official integration is unavailable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_official_check BEFORE INSERT ON applications_officialstatusreport
FOR EACH ROW EXECUTE FUNCTION applications_check_official();

CREATE FUNCTION applications_check_deletion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.state<>'PENDING_LEGAL_REVIEW' OR length(btrim(NEW.reason))=0 OR NOT EXISTS(
SELECT 1 FROM applications_submissionartifact s JOIN applications_application a ON
a.id=s.application_id
 WHERE s.id=NEW.artifact_id AND a.id=NEW.application_id AND a.owner_id=NEW.owner_id) THEN
 RAISE EXCEPTION 'deletion request must belong to submitted owned evidence'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_deletion_check BEFORE INSERT ON
applications_submittedartifactdeletionrequest
FOR EACH ROW EXECUTE FUNCTION applications_check_deletion();

CREATE FUNCTION applications_check_saved() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'unsave through audited active flag'; END IF;
 IF TG_OP='INSERT' THEN
 IF NEW.revision<>1 OR NOT NEW.active THEN RAISE EXCEPTION 'save starts active revision 1'; END IF;
 ELSE
 IF NEW.owner_id<>OLD.owner_id OR NEW.scholarship_id<>OLD.scholarship_id
 OR NEW.created_at<>OLD.created_at OR NEW.revision<>OLD.revision+1 OR NEW.active=OLD.active THEN
 RAISE EXCEPTION 'save relation must CAS-advance'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_saved_check BEFORE INSERT OR UPDATE OR DELETE ON
applications_savedscholarship
FOR EACH ROW EXECUTE FUNCTION applications_check_saved();
"""

REVERSE = r"""
DROP TRIGGER IF EXISTS applications_saved_check ON applications_savedscholarship;
DROP FUNCTION IF EXISTS applications_check_saved();
DROP TRIGGER IF EXISTS applications_deletion_check ON applications_submittedartifactdeletionrequest;
DROP FUNCTION IF EXISTS applications_check_deletion();
DROP TRIGGER IF EXISTS applications_official_check ON applications_officialstatusreport;
DROP FUNCTION IF EXISTS applications_check_official();
DROP TRIGGER IF EXISTS applications_complete_submission ON applications_submissionartifact;
DROP TRIGGER IF EXISTS applications_complete_requirement ON applications_applicationrequirement;
DROP TRIGGER IF EXISTS applications_complete_selection ON applications_selectedartifact;
DROP TRIGGER IF EXISTS applications_complete_event ON applications_applicationevent;
DROP TRIGGER IF EXISTS applications_complete_head ON applications_application;
DROP FUNCTION IF EXISTS applications_complete();
DROP TRIGGER IF EXISTS applications_submission_check ON applications_submissionartifact;
DROP FUNCTION IF EXISTS applications_check_submission();
DROP TRIGGER IF EXISTS applications_head_check ON applications_application;
DROP FUNCTION IF EXISTS applications_check_head();
DROP TRIGGER IF EXISTS applications_event_check ON applications_applicationevent;
DROP FUNCTION IF EXISTS applications_check_event();
DROP FUNCTION IF EXISTS applications_manifest(uuid,uuid);
DROP TRIGGER IF EXISTS applications_selection_check ON applications_selectedartifact;
DROP FUNCTION IF EXISTS applications_check_selection();
DROP TRIGGER IF EXISTS applications_requirement_check ON applications_applicationrequirement;
DROP FUNCTION IF EXISTS applications_check_requirement();
DROP FUNCTION IF EXISTS applications_artifact_valid(uuid,uuid,uuid,text);
DROP FUNCTION IF EXISTS applications_current_catalog(uuid);
DROP TRIGGER IF EXISTS applications_deletion_immutable ON
applications_submittedartifactdeletionrequest;
DROP TRIGGER IF EXISTS applications_official_immutable ON applications_officialstatusreport;
DROP TRIGGER IF EXISTS applications_submission_immutable ON applications_submissionartifact;
DROP TRIGGER IF EXISTS applications_requirement_immutable ON applications_applicationrequirement;
DROP TRIGGER IF EXISTS applications_event_immutable ON applications_applicationevent;
DROP FUNCTION IF EXISTS applications_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [("applications", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
