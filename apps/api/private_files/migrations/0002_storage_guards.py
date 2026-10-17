from typing import Any

from django.db import migrations


def seed(apps: Any, schema_editor: Any) -> None:
    apps.get_model("private_files", "StorageLock").objects.get_or_create(id=1)


GUARDS = """
CREATE FUNCTION files_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable storage evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER files_scan_immutable BEFORE UPDATE OR DELETE ON private_files_scanreceipt
FOR EACH ROW EXECUTE FUNCTION files_immutable();
CREATE TRIGGER files_grant_immutable BEFORE UPDATE OR DELETE ON private_files_accessgrant
FOR EACH ROW EXECUTE FUNCTION files_immutable();
CREATE TRIGGER files_record_no_delete BEFORE DELETE ON private_files_storedfile
FOR EACH ROW EXECUTE FUNCTION files_immutable();
CREATE FUNCTION files_guard_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF ROW(NEW.asset_id,NEW.operation_digest,NEW.sha256,NEW.size,NEW.mime,NEW.name,
      NEW.storage_token,NEW.created_at) IS DISTINCT FROM
     ROW(OLD.asset_id,OLD.operation_digest,OLD.sha256,OLD.size,OLD.mime,OLD.name,
      OLD.storage_token,OLD.created_at) THEN
    RAISE EXCEPTION 'immutable stored byte identity' USING ERRCODE='23514';
  END IF;
  IF NEW.capacity_state <> OLD.capacity_state AND NOT
     ((OLD.capacity_state='RESERVED' AND NEW.capacity_state IN ('RETAINED','RELEASED')) OR
      (OLD.capacity_state='RETAINED' AND NEW.capacity_state='RELEASED')) THEN
    RAISE EXCEPTION 'invalid capacity transition' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER files_record_guard BEFORE UPDATE ON private_files_storedfile
FOR EACH ROW EXECUTE FUNCTION files_guard_record();
CREATE FUNCTION files_verify_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE asset_uuid uuid; a privacy_privateasset;
 f private_files_storedfile; s private_files_scanreceipt;
BEGIN
  IF TG_TABLE_NAME='privacy_privateasset' THEN asset_uuid:=NEW.id;
  ELSIF TG_TABLE_NAME='private_files_storedfile' THEN asset_uuid:=NEW.asset_id;
  ELSE asset_uuid:=NEW.file_id; END IF;
  SELECT * INTO f FROM private_files_storedfile WHERE asset_id=asset_uuid;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT * INTO a FROM privacy_privateasset WHERE id=asset_uuid;
  IF f.sha256 !~ '^[0-9a-f]{64}$' OR a.object_version<>f.sha256 OR a.declared_size<>f.size THEN
    RAISE EXCEPTION 'invalid exact byte binding' USING ERRCODE='23514';
  END IF;
  IF a.state='ACCEPTED' THEN
    SELECT * INTO s FROM private_files_scanreceipt WHERE file_id=f.asset_id;
    IF NOT FOUND OR s.verdict<>'CLEAN' OR s.sha256<>f.sha256 OR s.size<>f.size
      OR s.engine NOT LIKE 'ClamAV %%' OR s.signature_version !~ '^[0-9]+$'
      OR s.signature_at>s.scanned_at+interval '5 minutes'
      OR s.signature_at<s.scanned_at-interval '7 days'
      OR f.capacity_state<>'RETAINED' THEN
      RAISE EXCEPTION 'accepted file requires exact clean scanner proof' USING ERRCODE='23514';
    END IF;
  END IF;
  IF a.state='PURGED' AND (f.capacity_state<>'RELEASED' OR f.capacity_bytes<>0) THEN
    RAISE EXCEPTION 'purged file retains capacity' USING ERRCODE='23514';
  END IF;
  IF f.capacity_state='RELEASED' AND a.state<>'PURGED' THEN
    RAISE EXCEPTION 'released capacity requires confirmed purge' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER files_asset_exact AFTER INSERT OR UPDATE ON privacy_privateasset
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION files_verify_binding();
CREATE CONSTRAINT TRIGGER files_record_exact AFTER INSERT OR UPDATE ON private_files_storedfile
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION files_verify_binding();
CREATE CONSTRAINT TRIGGER files_scan_exact AFTER INSERT ON private_files_scanreceipt
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION files_verify_binding();
"""


class Migration(migrations.Migration):
    dependencies = [("private_files", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop), migrations.RunSQL(GUARDS)]
