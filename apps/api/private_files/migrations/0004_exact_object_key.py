from django.db import migrations

GUARDS = """
-- No existing byte key is moved or silently rewritten. A mismatch needs an
-- explicit, verified storage reconciliation before this boundary can be enabled.
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM private_files_storedfile f
   JOIN privacy_privateasset a ON a.id=f.asset_id WHERE f.storage_token<>a.object_key) THEN
  RAISE EXCEPTION 'private file object key mismatch; storage reconciliation required'
    USING ERRCODE='23514';
 END IF;
END $$;
CREATE FUNCTION files_guard_object_key() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE asset_uuid uuid;
BEGIN
 IF TG_TABLE_NAME='privacy_privateasset' THEN asset_uuid:=NEW.id;
 ELSE asset_uuid:=NEW.asset_id; END IF;
 IF EXISTS(SELECT 1 FROM private_files_storedfile f
   JOIN privacy_privateasset a ON a.id=f.asset_id
   WHERE f.asset_id=asset_uuid AND f.storage_token<>a.object_key) THEN
  RAISE EXCEPTION 'stored object key differs from private asset key' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER files_object_key_asset AFTER INSERT OR UPDATE ON privacy_privateasset
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION files_guard_object_key();
CREATE CONSTRAINT TRIGGER files_object_key_record AFTER INSERT OR UPDATE ON private_files_storedfile
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION files_guard_object_key();
"""


class Migration(migrations.Migration):
    dependencies = [("private_files", "0003_storedfile_lease_expires_at")]
    operations = [migrations.RunSQL(GUARDS)]
