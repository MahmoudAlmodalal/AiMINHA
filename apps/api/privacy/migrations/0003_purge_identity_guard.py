from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("privacy", "0002_privacy_guards")]
    operations = [
        migrations.RunSQL("""
CREATE FUNCTION privacy_guard_purge_task() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE asset_owner uuid; account_owner uuid; exact_key uuid; exact_version varchar;
BEGIN
  IF TG_OP='UPDATE' AND ROW(NEW.deletion_id, NEW.asset_id, NEW.object_key, NEW.object_version)
     IS DISTINCT FROM ROW(OLD.deletion_id, OLD.asset_id, OLD.object_key, OLD.object_version) THEN
    RAISE EXCEPTION 'immutable purge target' USING ERRCODE='23514';
  END IF;
  SELECT owner_id, object_key, object_version INTO asset_owner, exact_key, exact_version
    FROM privacy_privateasset WHERE id=NEW.asset_id;
  SELECT account_id INTO account_owner FROM privacy_deletionrequest WHERE id=NEW.deletion_id;
  IF asset_owner IS DISTINCT FROM account_owner OR NEW.object_key IS DISTINCT FROM exact_key
     OR NEW.object_version IS DISTINCT FROM exact_version THEN
    RAISE EXCEPTION 'purge target ownership/version mismatch' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER privacy_purge_guard BEFORE INSERT OR UPDATE ON privacy_filepurgetask
FOR EACH ROW EXECUTE FUNCTION privacy_guard_purge_task();
CREATE TRIGGER privacy_deletion_no_delete BEFORE DELETE ON privacy_deletionrequest
FOR EACH ROW EXECUTE FUNCTION privacy_forbid_mutation();
""")
    ]
