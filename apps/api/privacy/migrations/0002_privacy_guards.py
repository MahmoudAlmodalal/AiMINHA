from typing import Any

from django.db import migrations


def initial_policy(apps: Any, schema_editor: Any) -> None:
    policy = apps.get_model("privacy", "RetentionPolicy").objects.create(
        version=1, recovery_days=30
    )
    apps.get_model("privacy", "RetentionHead").objects.create(id=1, policy=policy)


IMMUTABLE = """
CREATE FUNCTION privacy_forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable privacy evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER privacy_audit_immutable BEFORE UPDATE OR DELETE ON privacy_privacyaudit
FOR EACH ROW EXECUTE FUNCTION privacy_forbid_mutation();
CREATE TRIGGER privacy_consent_immutable BEFORE UPDATE OR DELETE ON privacy_consentrecord
FOR EACH ROW EXECUTE FUNCTION privacy_forbid_mutation();
CREATE TRIGGER privacy_disclosure_immutable BEFORE UPDATE OR DELETE ON privacy_disclosure
FOR EACH ROW EXECUTE FUNCTION privacy_forbid_mutation();
CREATE TRIGGER privacy_retention_immutable BEFORE UPDATE OR DELETE ON privacy_retentionpolicy
FOR EACH ROW EXECUTE FUNCTION privacy_forbid_mutation();
ALTER TABLE privacy_ticketshare ADD CONSTRAINT privacy_share_asset_owner
FOREIGN KEY(asset_id, owner_id) REFERENCES privacy_privateasset(id, owner_id);
ALTER TABLE privacy_ticketshare ADD CONSTRAINT privacy_share_ticket_owner
FOREIGN KEY(ticket_id, owner_id) REFERENCES privacy_ticketaccess(id, owner_id);
CREATE FUNCTION privacy_guard_deletion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF ROW(NEW.account_id, NEW.policy_id, NEW.confirmed_at, NEW.restore_until,
         NEW.recovery_days, NEW.recovery_timezone, NEW.cutoff_algorithm)
     IS DISTINCT FROM
     ROW(OLD.account_id, OLD.policy_id, OLD.confirmed_at, OLD.restore_until,
         OLD.recovery_days, OLD.recovery_timezone, OLD.cutoff_algorithm) THEN
    RAISE EXCEPTION 'immutable deletion snapshot' USING ERRCODE='23514';
  END IF;
  IF NEW.state <> OLD.state AND NOT
     ((OLD.state='PENDING' AND NEW.state IN ('RESTORED','PURGING')) OR
       (OLD.state='PURGING' AND NEW.state='PURGED')) THEN
    RAISE EXCEPTION 'invalid deletion transition' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER privacy_deletion_guard BEFORE UPDATE ON privacy_deletionrequest
FOR EACH ROW EXECUTE FUNCTION privacy_guard_deletion();
CREATE FUNCTION privacy_guard_asset() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF ROW(NEW.owner_id, NEW.object_key, NEW.object_version) IS DISTINCT FROM
     ROW(OLD.owner_id, OLD.object_key, OLD.object_version) THEN
    RAISE EXCEPTION 'immutable object identity' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER privacy_asset_guard BEFORE UPDATE ON privacy_privateasset
FOR EACH ROW EXECUTE FUNCTION privacy_guard_asset();
"""


class Migration(migrations.Migration):
    dependencies = [("privacy", "0001_initial")]
    operations = [
        migrations.RunPython(initial_policy, migrations.RunPython.noop),
        # Forward-only: never automatically remove evidence guards from populated data.
        migrations.RunSQL(IMMUTABLE),
    ]
