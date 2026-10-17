from django.db import migrations

SQL = r"""
CREATE FUNCTION documents_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'document history is immutable';
END $$;

CREATE TRIGGER documents_version_immutable BEFORE UPDATE OR DELETE ON documents_documentversion
FOR EACH ROW EXECUTE FUNCTION documents_immutable();
CREATE TRIGGER documents_approval_immutable BEFORE UPDATE OR DELETE ON documents_documentapproval
FOR EACH ROW EXECUTE FUNCTION documents_immutable();
CREATE TRIGGER documents_export_immutable BEFORE UPDATE OR DELETE ON documents_documentexport
FOR EACH ROW EXECUTE FUNCTION documents_immutable();
CREATE TRIGGER documents_snapshot_immutable BEFORE UPDATE OR DELETE ON documents_submissionsnapshot
FOR EACH ROW EXECUTE FUNCTION documents_immutable();

CREATE FUNCTION documents_check_version() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d documents_document; source documents_documentversion; actual text;
BEGIN
    SELECT * INTO STRICT d FROM documents_document WHERE id=NEW.document_id FOR UPDATE;
    IF NEW.owner_id <> d.owner_id OR NEW.number <> d.revision+1 THEN
        RAISE EXCEPTION 'document version owner or sequence mismatch';
    END IF;
    IF length(NEW.title) NOT BETWEEN 1 AND 200 OR length(btrim(NEW.title))=0
       OR length(NEW.content) NOT BETWEEN 1 AND 40000 OR length(btrim(NEW.content))=0 THEN
        RAISE EXCEPTION 'invalid document content';
    END IF;
    actual := encode(sha256(convert_to(
        jsonb_build_array(d.kind,NEW.title,NEW.language,NEW.content)::text,'UTF8')),'hex');
    IF NEW.content_hash <> actual THEN RAISE EXCEPTION 'document hash mismatch'; END IF;
    IF NEW.restored_from_id IS NOT NULL THEN
        SELECT * INTO STRICT source FROM documents_documentversion WHERE id=NEW.restored_from_id;
        IF source.document_id<>NEW.document_id OR source.owner_id<>NEW.owner_id
           OR source.number>=NEW.number OR source.title<>NEW.title OR source.language<>NEW.language
           OR source.content<>NEW.content OR source.content_hash<>NEW.content_hash THEN
            RAISE EXCEPTION 'restore must preserve exact source content';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER documents_version_check BEFORE INSERT ON documents_documentversion
FOR EACH ROW EXECUTE FUNCTION documents_check_version();

CREATE FUNCTION documents_check_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v documents_documentversion;
BEGIN
    IF TG_OP='DELETE' THEN RAISE EXCEPTION 'document erasure requires approved lifecycle'; END IF;
    IF TG_OP='INSERT' THEN
        IF NEW.revision<>0 OR NEW.current_id IS NOT NULL THEN
            RAISE EXCEPTION 'document begins with an empty locked head';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.owner_id<>OLD.owner_id OR NEW.kind<>OLD.kind OR NEW.created_at<>OLD.created_at
       OR NEW.revision<>OLD.revision+1 OR NEW.current_id IS NULL THEN
        RAISE EXCEPTION 'document head must advance exactly once';
    END IF;
    SELECT * INTO STRICT v FROM documents_documentversion WHERE id=NEW.current_id;
    IF v.document_id<>NEW.id OR v.owner_id<>NEW.owner_id OR v.number<>NEW.revision THEN
        RAISE EXCEPTION 'document head points outside owned version sequence';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER documents_head_check BEFORE INSERT OR UPDATE OR DELETE ON documents_document
FOR EACH ROW EXECUTE FUNCTION documents_check_head();

CREATE FUNCTION documents_complete_head() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE d documents_document; target uuid; v documents_documentversion;
BEGIN
    IF TG_TABLE_NAME='documents_documentversion' THEN target:=NEW.document_id;
    ELSE target:=NEW.id; END IF;
    SELECT * INTO STRICT d FROM documents_document WHERE id=target;
    IF d.current_id IS NULL OR d.revision=0 THEN
        RAISE EXCEPTION 'document lacks saved content';
    END IF;
    SELECT * INTO STRICT v FROM documents_documentversion WHERE id=d.current_id;
    IF v.document_id<>d.id OR v.owner_id<>d.owner_id OR v.number<>d.revision
       OR d.revision<>(SELECT max(number) FROM documents_documentversion
                      WHERE document_id=d.id) THEN
        RAISE EXCEPTION 'incomplete document head';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER documents_head_complete AFTER INSERT OR UPDATE ON documents_document
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION documents_complete_head();
CREATE CONSTRAINT TRIGGER documents_version_complete AFTER INSERT ON documents_documentversion
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION documents_complete_head();

CREATE FUNCTION documents_check_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v documents_documentversion; a privacy_privateasset;
BEGIN
    SELECT * INTO STRICT v FROM documents_documentversion WHERE id=NEW.version_id;
    IF NEW.owner_id<>v.owner_id OR NEW.content_hash<>v.content_hash THEN
        RAISE EXCEPTION 'document evidence owner/hash mismatch';
    END IF;
    IF TG_TABLE_NAME<>'documents_documentapproval' AND NOT EXISTS(
        SELECT 1 FROM documents_documentapproval
        WHERE version_id=v.id AND owner_id=v.owner_id AND content_hash=v.content_hash
    ) THEN RAISE EXCEPTION 'exact owner approval required'; END IF;
    IF TG_TABLE_NAME='documents_documentexport' THEN
        SELECT * INTO STRICT a FROM privacy_privateasset WHERE id=NEW.asset_id;
        IF a.owner_id<>NEW.owner_id OR a.state<>'ACCEPTED' OR NOT EXISTS(
            SELECT 1 FROM private_files_storedfile f
            JOIN private_files_scanreceipt scan ON scan.file_id=f.asset_id
            WHERE f.asset_id=a.id AND f.capacity_state='RETAINED'
            AND scan.sha256=f.sha256 AND scan.size=f.size AND scan.verdict='CLEAN'
        ) THEN
            RAISE EXCEPTION 'private export asset unavailable or unowned';
        END IF;
    END IF;
    IF TG_TABLE_NAME='documents_submissionsnapshot' THEN
        PERFORM pg_advisory_xact_lock(hashtextextended(NEW.application_ref::text, 0));
        IF EXISTS(SELECT 1 FROM documents_submissionsnapshot
                  WHERE application_ref=NEW.application_ref AND owner_id<>NEW.owner_id) THEN
            RAISE EXCEPTION 'application snapshot owner mismatch';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER documents_approval_check BEFORE INSERT ON documents_documentapproval
FOR EACH ROW EXECUTE FUNCTION documents_check_evidence();
CREATE TRIGGER documents_export_check BEFORE INSERT ON documents_documentexport
FOR EACH ROW EXECUTE FUNCTION documents_check_evidence();
CREATE TRIGGER documents_snapshot_check BEFORE INSERT ON documents_submissionsnapshot
FOR EACH ROW EXECUTE FUNCTION documents_check_evidence();
"""

REVERSE = """
DROP TRIGGER IF EXISTS documents_snapshot_check ON documents_submissionsnapshot;
DROP TRIGGER IF EXISTS documents_export_check ON documents_documentexport;
DROP TRIGGER IF EXISTS documents_approval_check ON documents_documentapproval;
DROP FUNCTION IF EXISTS documents_check_evidence();
DROP TRIGGER IF EXISTS documents_version_complete ON documents_documentversion;
DROP TRIGGER IF EXISTS documents_head_complete ON documents_document;
DROP FUNCTION IF EXISTS documents_complete_head();
DROP TRIGGER IF EXISTS documents_head_check ON documents_document;
DROP FUNCTION IF EXISTS documents_check_head();
DROP TRIGGER IF EXISTS documents_version_check ON documents_documentversion;
DROP FUNCTION IF EXISTS documents_check_version();
DROP TRIGGER IF EXISTS documents_snapshot_immutable ON documents_submissionsnapshot;
DROP TRIGGER IF EXISTS documents_export_immutable ON documents_documentexport;
DROP TRIGGER IF EXISTS documents_approval_immutable ON documents_documentapproval;
DROP TRIGGER IF EXISTS documents_version_immutable ON documents_documentversion;
DROP FUNCTION IF EXISTS documents_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
        ("private_files", "0002_storage_guards"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
