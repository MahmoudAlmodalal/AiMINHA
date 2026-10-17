"""A local accounting receipt cannot replace its validated persisted artifact."""

from django.db import migrations

SQL = r"""
CREATE FUNCTION documents_synthetic_job_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE operation credits_operation;
DECLARE version documents_documentversion;
DECLARE body text;
DECLARE qualification text;
DECLARE expected_hash text;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'immutable synthetic document job' USING ERRCODE='23514';
 END IF;
 SELECT * INTO operation FROM credits_operation WHERE id=NEW.operation_id;
 IF NEW.kind NOT IN ('CV','MOTIVATION_LETTER','PERSONAL_STATEMENT','ESSAY','CV_EXTRACTION')
   OR NEW.language NOT IN ('ar','en') OR operation.owner_id IS DISTINCT FROM NEW.owner_id
   OR operation.service IS DISTINCT FROM (CASE WHEN NEW.kind='CV_EXTRACTION'
     THEN 'CV_EXTRACTION' ELSE 'DOCUMENT_NEW' END)
 THEN RAISE EXCEPTION 'invalid document operation binding' USING ERRCODE='23514'; END IF;
 expected_hash:=encode(sha256(convert_to('{"kind":"'||NEW.kind||'","language":"'||
   NEW.language||'"}','UTF8')),'hex');
 IF NEW.request_hash<>expected_hash THEN
  RAISE EXCEPTION 'invalid synthetic request hash' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN
  IF operation.state<>'RESERVED' OR NEW.version_id IS NOT NULL OR NEW.proposal IS NOT NULL THEN
   RAISE EXCEPTION 'pending document admission required' USING ERRCODE='23514'; END IF;
  RETURN NEW;
 END IF;
 IF (NEW.id,NEW.operation_id,NEW.owner_id,NEW.kind,NEW.language,NEW.request_hash,NEW.created_at)
   IS DISTINCT FROM
   (OLD.id,OLD.operation_id,OLD.owner_id,OLD.kind,OLD.language,OLD.request_hash,OLD.created_at)
   OR OLD.version_id IS NOT NULL OR OLD.proposal IS NOT NULL OR operation.state<>'RUNNING'
 THEN RAISE EXCEPTION 'immutable document job evidence' USING ERRCODE='23514'; END IF;
 qualification:=CASE WHEN NEW.language='ar' THEN 'دورة تدريبية اصطناعية'
   ELSE 'Synthetic training course' END;
 IF NEW.kind='CV_EXTRACTION' THEN
  IF NEW.version_id IS NOT NULL OR NEW.proposal IS DISTINCT FROM jsonb_build_object(
     'language',NEW.language,'trusted',false,'facts',jsonb_build_array(jsonb_build_object(
       'field','qualification','value',qualification,'source','SYNTHETIC_FIXTURE',
       'review_required',true)))
  THEN RAISE EXCEPTION 'exact untrusted synthetic proposal required' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT * INTO version FROM documents_documentversion WHERE id=NEW.version_id;
  body:=CASE WHEN NEW.language='ar' THEN 'طالب اصطناعي' ELSE 'Synthetic Student' END
    ||chr(10)||qualification;
  IF NEW.proposal IS NOT NULL OR NEW.version_id IS NULL
    OR version.owner_id IS DISTINCT FROM NEW.owner_id
    OR version.language IS DISTINCT FROM NEW.language OR version.provenance<>'SYNTHETIC_LOCAL'
    OR version.content IS DISTINCT FROM body
    OR version.title NOT IN ('Synthetic document','Synthetic CV','مستند اصطناعي')
    OR NOT EXISTS (SELECT 1 FROM documents_document d
      WHERE d.id=version.document_id AND d.kind=NEW.kind AND d.owner_id=NEW.owner_id)
  THEN RAISE EXCEPTION 'exact saved synthetic document required' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION documents_synthetic_saved_before_charge() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM documents_syntheticdocumentjob j WHERE j.operation_id=NEW.operation_id
   AND ((j.kind='CV_EXTRACTION' AND (j.proposal IS NULL OR j.version_id IS NOT NULL))
     OR (j.kind<>'CV_EXTRACTION' AND (j.version_id IS NULL OR j.proposal IS NOT NULL))))
 THEN RAISE EXCEPTION 'document artifact must be saved before debit' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION documents_synthetic_conservation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM documents_syntheticdocumentjob j
   JOIN credits_operation o ON o.id=j.operation_id
   WHERE (o.state='SETTLED') IS DISTINCT FROM
     (j.version_id IS NOT NULL OR j.proposal IS NOT NULL))
 THEN RAISE EXCEPTION 'document accounting witness conservation failed' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;

CREATE TRIGGER documents_synthetic_job_proof BEFORE INSERT OR UPDATE OR DELETE
 ON documents_syntheticdocumentjob FOR EACH ROW EXECUTE FUNCTION documents_synthetic_job_guard();
CREATE TRIGGER documents_synthetic_saved_proof BEFORE INSERT ON credits_savedoutput
 FOR EACH ROW EXECUTE FUNCTION documents_synthetic_saved_before_charge();
CREATE CONSTRAINT TRIGGER documents_synthetic_job_conserved AFTER INSERT OR UPDATE OR DELETE
 ON documents_syntheticdocumentjob DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
 EXECUTE FUNCTION documents_synthetic_conservation();
CREATE CONSTRAINT TRIGGER documents_synthetic_operation_conserved AFTER INSERT OR UPDATE
 ON credits_operation DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
 EXECUTE FUNCTION documents_synthetic_conservation();
"""

REVERSE = r"""
DROP TRIGGER documents_synthetic_operation_conserved ON credits_operation;
DROP TRIGGER documents_synthetic_job_conserved ON documents_syntheticdocumentjob;
DROP TRIGGER documents_synthetic_saved_proof ON credits_savedoutput;
DROP TRIGGER documents_synthetic_job_proof ON documents_syntheticdocumentjob;
DROP FUNCTION documents_synthetic_conservation();
DROP FUNCTION documents_synthetic_saved_before_charge();
DROP FUNCTION documents_synthetic_job_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_document_guards")]
    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSE)]
