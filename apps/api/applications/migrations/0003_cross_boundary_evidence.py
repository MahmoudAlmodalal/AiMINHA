"""Bind real application freezes and protect uploads without blocking legal purge planning."""

from django.db import migrations

SQL = r"""
CREATE FUNCTION applications_frozen_document_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; tracked applications_application;
BEGIN
 IF TG_TABLE_NAME='documents_submissionsnapshot' THEN target:=NEW.application_ref;
 ELSIF TG_TABLE_NAME='applications_application' THEN target:=NEW.id;
 ELSE target:=NEW.application_id; END IF;
 SELECT * INTO tracked FROM applications_application WHERE id=target;
 -- Phase11's standalone LOCAL freeze proof has no application aggregate. A real
 -- tracker reference is stricter and cannot impersonate that older fixture port.
 IF NOT FOUND THEN RETURN NULL; END IF;
 IF EXISTS (
  SELECT 1 FROM documents_submissionsnapshot d WHERE d.application_ref=target AND (
   d.owner_id<>tracked.owner_id OR NOT EXISTS (
    SELECT 1 FROM applications_submissionartifact s
    JOIN applications_applicationevent e ON e.id=s.event_id
    WHERE s.application_id=target AND s.version_id=d.version_id
      AND s.content_hash=d.content_hash AND e.application_id=target
      AND e.sequence=tracked.submitted_sequence AND e.to_state='SUBMITTED'
      AND e.student_submission_confirmation
   )
  )
 ) OR EXISTS (
  SELECT 1 FROM applications_submissionartifact s WHERE s.application_id=target
   AND s.version_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM documents_submissionsnapshot d
    WHERE d.application_ref=target AND d.owner_id=tracked.owner_id
      AND d.version_id=s.version_id AND d.content_hash=s.content_hash
   )
 ) THEN RAISE EXCEPTION 'application requires exact submitted document freeze'
  USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER applications_document_freeze_bound
 AFTER INSERT ON documents_submissionsnapshot DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION applications_frozen_document_binding();
CREATE CONSTRAINT TRIGGER applications_submission_freeze_bound
 AFTER INSERT ON applications_submissionartifact DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION applications_frozen_document_binding();
CREATE CONSTRAINT TRIGGER applications_tracker_freeze_bound
 AFTER INSERT OR UPDATE ON applications_application DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION applications_frozen_document_binding();

CREATE FUNCTION applications_protect_submitted_upload() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM applications_submissionartifact s WHERE s.asset_id=OLD.id)
 THEN IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END IF;
 IF TG_OP='UPDATE' AND NEW.state=OLD.state THEN RETURN NEW; END IF;
 -- Normal mutation cannot thaw evidence. The canonical account purge planner
 -- may mark an exact object only after its approved, expired legal snapshot.
 -- This is not an erasure receipt or an implementation of physical/body purge.
 IF NOT EXISTS (
  SELECT 1 FROM privacy_deletionrequest d
  JOIN privacy_retentionpolicy p ON p.id=d.policy_id
  JOIN privacy_legalenvelope legal ON legal.id=p.legal_envelope_id
  JOIN identity_account a ON a.id=d.account_id
  WHERE d.account_id=OLD.owner_id AND d.state='PURGING' AND a.state='PURGING'
    AND d.restore_until<=statement_timestamp() AND legal.approved
    AND p.recovery_days BETWEEN legal.min_days AND legal.max_days
 ) THEN RAISE EXCEPTION 'submitted upload requires separate approved erasure workflow'
  USING ERRCODE='23514'; END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER applications_submitted_upload_protected
 BEFORE UPDATE OR DELETE ON privacy_privateasset
 FOR EACH ROW EXECUTE FUNCTION applications_protect_submitted_upload();
"""

REVERSE = r"""
DROP TRIGGER applications_submitted_upload_protected ON privacy_privateasset;
DROP FUNCTION applications_protect_submitted_upload();
DROP TRIGGER applications_tracker_freeze_bound ON applications_application;
DROP TRIGGER applications_submission_freeze_bound ON applications_submissionartifact;
DROP TRIGGER applications_document_freeze_bound ON documents_submissionsnapshot;
DROP FUNCTION applications_frozen_document_binding();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0002_application_guards"),
        ("private_files", "0004_exact_object_key"),
    ]
    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSE)]
