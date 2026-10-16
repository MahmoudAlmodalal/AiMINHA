"""Deferred journal conservation, captured prices and immutable local fixture proofs."""

from django.db import migrations

GUARDS = r"""
CREATE FUNCTION credits_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable credit evidence' USING ERRCODE='23514'; END $$;
CREATE FUNCTION credits_adult(dob date) RETURNS boolean LANGUAGE sql STABLE AS $$
SELECT CASE WHEN dob IS NULL OR dob > timezone('UTC', statement_timestamp())::date
 OR extract(year from dob)+18 > extract(year from timezone('UTC', statement_timestamp()))
 THEN false ELSE timezone('UTC', statement_timestamp())::date >=
 CASE WHEN extract(month from dob)=2 AND extract(day from dob)=29
 THEN make_date(extract(year from dob)::int+18,3,1)
 ELSE make_date(extract(year from dob)::int+18,extract(month from dob)::int,extract(day from
  dob)::int)
 END END $$;

CREATE FUNCTION credits_policy_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.version=1 AND NEW.actor_id IS NULL AND NEW.session_proof_id IS NULL
    AND NEW.reason='DEFAULT_BETA' AND (NEW.signup_grant,NEW.daily_spend_cap,NEW.global_ai_cap,
      NEW.matching_price,NEW.cv_price,NEW.document_price)=(30,6,100,1,4,6)
    AND NOT EXISTS (SELECT 1 FROM credits_creditpolicy)
    AND NOT EXISTS (SELECT 1 FROM credits_policyhead)
    AND NOT EXISTS (SELECT 1 FROM credits_wallet)
    AND NOT EXISTS (SELECT 1 FROM credits_operation)
  THEN RETURN NEW; END IF;
  IF NEW.version < 2 OR NOT catalog_admin_proof(NEW.actor_id,NEW.session_proof_id,'COST_POLICY')
    OR length(btrim(NEW.reason))=0 OR NOT EXISTS (
      SELECT 1 FROM credits_policyhead h JOIN credits_creditpolicy p ON p.id=h.policy_id
      WHERE h.id=1 AND NEW.version=p.version+1
    ) THEN RAISE EXCEPTION 'current cost-policy MFA proof required' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE FUNCTION credits_policy_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='INSERT' THEN
    IF NEW.id<>1 OR NOT EXISTS (SELECT 1 FROM credits_creditpolicy WHERE id=NEW.policy_id AND
  version=1)
    THEN RAISE EXCEPTION 'initial credit policy head required' USING ERRCODE='23514'; END IF;
    RETURN NEW;
  END IF;
  IF TG_OP='DELETE' OR NEW.id<>1 OR NOT EXISTS (
    SELECT 1 FROM credits_creditpolicy n JOIN credits_creditpolicy o ON o.id=OLD.policy_id
    WHERE n.id=NEW.policy_id AND n.version=o.version+1
  ) THEN RAISE EXCEPTION 'credit policy head must advance once' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION credits_operation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p credits_creditpolicy;
DECLARE f credits_syntheticinput;
BEGIN
  IF TG_OP='DELETE' THEN RAISE EXCEPTION 'credit operation cannot be removed' USING
  ERRCODE='23514'; END IF;
  IF TG_OP='INSERT' THEN
    PERFORM 1 FROM identity_account WHERE id=NEW.owner_id FOR UPDATE;
    PERFORM 1 FROM credits_policyhead WHERE id=1 FOR UPDATE;
    SELECT * INTO p FROM credits_creditpolicy WHERE id=NEW.policy_id;
    SELECT * INTO f FROM credits_syntheticinput WHERE id=NEW.fixture_id;
    IF NEW.state<>'RESERVED' OR NEW.attempt<>0 OR NEW.fence_digest<>''
      OR NEW.reconciliation_started_at IS NOT NULL OR NEW.resolution_due_at IS NOT NULL
      OR NEW.reserve_until<>NEW.created_at+interval '15 minutes'
      OR NEW.captured_day<>(NEW.created_at AT TIME ZONE 'Asia/Hebron')::date
      OR length(NEW.key_digest)<>64 OR length(NEW.request_digest)<>64
      OR f.owner_id IS DISTINCT FROM NEW.owner_id
      OR NEW.price IS DISTINCT FROM (CASE NEW.service WHEN 'MATCHING_AI' THEN p.matching_price
        WHEN 'CV_EXTRACTION' THEN p.cv_price WHEN 'DOCUMENT_NEW' THEN p.document_price ELSE NULL
  END)
      OR NOT EXISTS (SELECT 1 FROM credits_policyhead WHERE id=1 AND policy_id=NEW.policy_id)
      OR NOT EXISTS (SELECT 1 FROM identity_account a WHERE a.id=NEW.owner_id AND a.role='STUDENT'
        AND a.state='ACTIVE' AND a.email_verified_at IS NOT NULL AND credits_adult(a.birth_date))
    THEN RAISE EXCEPTION 'invalid captured credit admission' USING ERRCODE='23514'; END IF;
    IF NOT EXISTS (SELECT 1 FROM credits_wallet w WHERE w.owner_id=NEW.owner_id
      AND w.posted_balance-w.reserved_balance>=NEW.price)
      OR coalesce((SELECT d.spent+d.reserved FROM credits_studentday d
        WHERE d.owner_id=NEW.owner_id AND d.day=NEW.captured_day),0)+NEW.price>p.daily_spend_cap
      OR coalesce((SELECT d.admitted_operations FROM credits_globalday d WHERE
  d.day=NEW.captured_day),0)>=p.global_ai_cap
    THEN RAISE EXCEPTION 'credit admission budget exceeded' USING ERRCODE='23514'; END IF;
  ELSE
    IF (NEW.id,NEW.owner_id,NEW.service,NEW.price,NEW.policy_id,NEW.captured_day,
      NEW.key_digest,NEW.request_digest,NEW.fixture_id,NEW.created_at,NEW.reserve_until)
      IS DISTINCT FROM
      (OLD.id,OLD.owner_id,OLD.service,OLD.price,OLD.policy_id,OLD.captured_day,
      OLD.key_digest,OLD.request_digest,OLD.fixture_id,OLD.created_at,OLD.reserve_until)
      OR OLD.state IN ('SETTLED','RELEASED') OR NOT (
      (NEW.state=OLD.state AND NEW.attempt=OLD.attempt AND NEW.fence_digest=OLD.fence_digest)
      OR (OLD.state='RESERVED' AND NEW.state='RUNNING' AND NEW.attempt=OLD.attempt+1
          AND length(NEW.fence_digest)=64)
      OR (OLD.state IN ('RESERVED','RUNNING') AND NEW.state='RECONCILING'
          AND NEW.attempt=OLD.attempt AND NEW.fence_digest=OLD.fence_digest)
      OR (OLD.state='RUNNING' AND NEW.state IN ('SETTLED','RELEASED') AND NEW.attempt=OLD.attempt
          AND NEW.fence_digest=OLD.fence_digest)
    ) THEN RAISE EXCEPTION 'invalid or immutable credit transition' USING ERRCODE='23514'; END IF;
    IF OLD.reconciliation_started_at IS NOT NULL AND (
      NEW.reconciliation_started_at IS DISTINCT FROM OLD.reconciliation_started_at
      OR NEW.resolution_due_at IS DISTINCT FROM OLD.resolution_due_at)
    THEN RAISE EXCEPTION 'reconciliation target is immutable' USING ERRCODE='23514'; END IF;
  END IF;
  IF NEW.state IN ('RUNNING','SETTLED') AND NOT EXISTS (
    SELECT 1 FROM identity_account a WHERE a.id=NEW.owner_id AND a.role='STUDENT'
      AND a.state='ACTIVE' AND a.email_verified_at IS NOT NULL AND credits_adult(a.birth_date)
  ) THEN RAISE EXCEPTION 'verified active adult required' USING ERRCODE='23514'; END IF;
  IF (NEW.state='RECONCILING' AND (NEW.reconciliation_started_at IS NULL OR
    NEW.resolution_due_at IS DISTINCT FROM NEW.reconciliation_started_at+interval '24 hours'))
    OR (NEW.state<>'RECONCILING' AND (NEW.reconciliation_started_at IS NOT NULL OR
  NEW.resolution_due_at IS NOT NULL))
  THEN RAISE EXCEPTION 'explicit reconciliation marker required' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION credits_hold_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR (TG_OP='INSERT' AND NEW.state<>'ACTIVE')
   OR (TG_OP='UPDATE' AND ((NEW.operation_id,NEW.amount) IS DISTINCT FROM
  (OLD.operation_id,OLD.amount)
     OR OLD.state<>'ACTIVE' OR NEW.state NOT IN ('SETTLED','RELEASED')))
 THEN RAISE EXCEPTION 'invalid immutable credit hold' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION credits_entry_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p credits_creditpolicy;
BEGIN
 PERFORM 1 FROM identity_account WHERE id=NEW.owner_id FOR UPDATE;
 SELECT * INTO p FROM credits_creditpolicy WHERE id=NEW.policy_id;
 IF length(btrim(NEW.reason_code))=0 OR (NEW.kind='SIGNUP_GRANT' AND (
   NEW.amount IS DISTINCT FROM p.signup_grant OR NOT EXISTS (
     SELECT 1 FROM identity_account a WHERE a.id=NEW.owner_id AND a.role='STUDENT'
       AND a.state='ACTIVE' AND a.email_verified_at IS NOT NULL AND credits_adult(a.birth_date)
   ) OR NOT EXISTS (SELECT 1 FROM credits_policyhead h WHERE h.policy_id=NEW.policy_id)
 )) OR (NEW.kind='DEBIT' AND NOT EXISTS (
   SELECT 1 FROM credits_operation o WHERE o.id=NEW.operation_id AND o.owner_id=NEW.owner_id
     AND o.policy_id=NEW.policy_id AND NEW.amount=-o.price
 )) THEN RAISE EXCEPTION 'invalid captured journal evidence' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION credits_output_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o credits_operation;
DECLARE canonical text;
BEGIN
 SELECT * INTO o FROM credits_operation WHERE id=NEW.operation_id;
 canonical:='{"fixture_id":"'||o.fixture_id::text||'","result":"SYNTHETIC_OK"}';
 IF o.state<>'RUNNING' OR NOT EXISTS (
     SELECT 1 FROM identity_account a WHERE a.id=o.owner_id AND a.role='STUDENT'
       AND a.state='ACTIVE' AND a.email_verified_at IS NOT NULL AND credits_adult(a.birth_date)
   ) OR NEW.owner_id IS DISTINCT FROM o.owner_id OR NEW.validator_version<>'synthetic-v1'
   OR NEW.payload IS DISTINCT FROM
  jsonb_build_object('fixture_id',o.fixture_id::text,'result','SYNTHETIC_OK')
   OR NEW.content_hash<>encode(sha256(convert_to(canonical,'UTF8')),'hex')
 THEN RAISE EXCEPTION 'exact validated synthetic output required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION credits_conservation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM credits_wallet w WHERE w.posted_balance<>(
     SELECT coalesce(sum(e.amount),0) FROM credits_ledgerentry e WHERE e.owner_id=w.owner_id
   ) OR w.reserved_balance<>(
     SELECT coalesce(sum(h.amount),0) FROM credits_hold h JOIN credits_operation o ON
  o.id=h.operation_id
       WHERE o.owner_id=w.owner_id AND h.state='ACTIVE'
   )
 ) OR EXISTS (
   SELECT 1 FROM credits_ledgerentry e LEFT JOIN credits_wallet w ON w.owner_id=e.owner_id
     WHERE w.owner_id IS NULL
 ) OR EXISTS (
   SELECT 1 FROM credits_operation o LEFT JOIN credits_wallet w ON w.owner_id=o.owner_id
     WHERE w.owner_id IS NULL
 ) THEN RAISE EXCEPTION 'credit wallet journal conservation failed' USING ERRCODE='23514'; END IF;
 IF EXISTS (
   SELECT 1 FROM credits_studentday d WHERE d.spent<>(
     SELECT coalesce(sum(o.price),0) FROM credits_operation o
       WHERE o.owner_id=d.owner_id AND o.captured_day=d.day AND o.state='SETTLED'
   ) OR d.reserved<>(
     SELECT coalesce(sum(h.amount),0) FROM credits_hold h JOIN credits_operation o ON
  o.id=h.operation_id
       WHERE o.owner_id=d.owner_id AND o.captured_day=d.day AND h.state='ACTIVE'
   )
 ) OR EXISTS (
   SELECT 1 FROM credits_operation o LEFT JOIN credits_studentday d ON d.owner_id=o.owner_id AND
  d.day=o.captured_day
     WHERE d.id IS NULL
 ) OR EXISTS (
   SELECT 1 FROM credits_globalday d WHERE d.admitted_operations<>(
     SELECT count(*) FROM credits_operation o WHERE o.captured_day=d.day
   )
 ) OR EXISTS (
   SELECT 1 FROM credits_operation o LEFT JOIN credits_globalday d ON d.day=o.captured_day WHERE
  d.day IS NULL
 ) THEN RAISE EXCEPTION 'credit captured-day conservation failed' USING ERRCODE='23514'; END IF;
 IF EXISTS (
   SELECT 1 FROM credits_operation o
   LEFT JOIN credits_hold h ON h.operation_id=o.id
   LEFT JOIN credits_finalization f ON f.operation_id=o.id
   LEFT JOIN credits_savedoutput r ON r.operation_id=o.id
   LEFT JOIN credits_ledgerentry e ON e.operation_id=o.id
   WHERE h.operation_id IS NULL OR h.amount<>o.price OR CASE
    WHEN o.state IN ('RESERVED','RUNNING','RECONCILING') THEN
      h.state<>'ACTIVE' OR f.operation_id IS NOT NULL OR r.id IS NOT NULL OR e.id IS NOT NULL
    WHEN o.state='SETTLED' THEN
      h.state<>'SETTLED' OR f.operation_id IS NULL OR f.outcome<>'SETTLED'
      OR f.reason_code<>'VALIDATED_SAVED_SYNTHETIC_OUTPUT'
      OR r.id IS NULL OR r.owner_id<>o.owner_id OR f.output_id IS DISTINCT FROM r.id
      OR e.id IS NULL OR e.kind<>'DEBIT' OR e.amount<>-o.price OR e.owner_id<>o.owner_id
      OR e.policy_id<>o.policy_id OR f.entry_id IS DISTINCT FROM e.id
    WHEN o.state='RELEASED' THEN
      h.state<>'RELEASED' OR f.operation_id IS NULL OR f.outcome<>'RELEASED'
      OR r.id IS NOT NULL OR e.id IS NOT NULL OR f.output_id IS NOT NULL OR f.entry_id IS NOT NULL
      OR f.reason_code NOT IN ('KNOWN_SYNTHETIC_FAILURE')
    ELSE true END
 ) THEN RAISE EXCEPTION 'credit operation finalization conservation failed' USING
  ERRCODE='23514'; END IF;
 IF EXISTS (SELECT 1 FROM credits_creditpolicy p WHERE NOT EXISTS (
   SELECT 1 FROM credits_policyhead h JOIN credits_creditpolicy c ON c.id=h.policy_id WHERE
  c.version>=p.version
 )) THEN RAISE EXCEPTION 'policy version must become current atomically' USING ERRCODE='23514';
  END IF;
 RETURN NULL;
END $$;

CREATE TRIGGER credits_policy_immutable BEFORE UPDATE OR DELETE ON credits_creditpolicy FOR EACH
  ROW EXECUTE FUNCTION credits_immutable();
CREATE TRIGGER credits_policy_proof BEFORE INSERT ON credits_creditpolicy FOR EACH ROW EXECUTE
  FUNCTION credits_policy_insert();
CREATE TRIGGER credits_policy_head_guard BEFORE INSERT OR UPDATE OR DELETE ON credits_policyhead
  FOR EACH ROW EXECUTE FUNCTION credits_policy_head();
CREATE TRIGGER credits_fixture_immutable BEFORE UPDATE OR DELETE ON credits_syntheticinput FOR
  EACH ROW EXECUTE FUNCTION credits_immutable();
CREATE TRIGGER credits_operation_transition BEFORE INSERT OR UPDATE OR DELETE ON
  credits_operation FOR EACH ROW EXECUTE FUNCTION credits_operation_guard();
CREATE TRIGGER credits_hold_transition BEFORE INSERT OR UPDATE OR DELETE ON credits_hold FOR EACH
  ROW EXECUTE FUNCTION credits_hold_guard();
CREATE TRIGGER credits_entry_insert BEFORE INSERT ON credits_ledgerentry FOR EACH ROW EXECUTE
  FUNCTION credits_entry_guard();
CREATE TRIGGER credits_entry_immutable BEFORE UPDATE OR DELETE ON credits_ledgerentry FOR EACH
  ROW EXECUTE FUNCTION credits_immutable();
CREATE TRIGGER credits_output_insert BEFORE INSERT ON credits_savedoutput FOR EACH ROW EXECUTE
  FUNCTION credits_output_guard();
CREATE TRIGGER credits_output_immutable BEFORE UPDATE OR DELETE ON credits_savedoutput FOR EACH
  ROW EXECUTE FUNCTION credits_immutable();
CREATE TRIGGER credits_finalization_immutable BEFORE UPDATE OR DELETE ON credits_finalization FOR
  EACH ROW EXECUTE FUNCTION credits_immutable();
"""

TABLES = [
    "wallet",
    "studentday",
    "globalday",
    "operation",
    "hold",
    "ledgerentry",
    "savedoutput",
    "finalization",
    "creditpolicy",
    "policyhead",
    "syntheticinput",
]
for table in TABLES:
    GUARDS += f"""
CREATE CONSTRAINT TRIGGER credits_{table}_conserved AFTER INSERT OR UPDATE OR DELETE ON
  credits_{table}
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION credits_conservation();
"""

SEED = r"""
INSERT INTO credits_creditpolicy
  (id,version,signup_grant,daily_spend_cap,global_ai_cap,matching_price,cv_price,
   document_price,reason,created_at)
VALUES (gen_random_uuid(),1,30,6,100,1,4,6,'DEFAULT_BETA',statement_timestamp());
INSERT INTO credits_policyhead (id,policy_id) SELECT 1,id FROM credits_creditpolicy WHERE
  version=1;
"""

BACKFILL = r"""
INSERT INTO credits_wallet (owner_id,posted_balance,reserved_balance)
SELECT a.id,p.signup_grant,0 FROM identity_account a CROSS JOIN credits_creditpolicy p
WHERE p.version=1 AND a.state='ACTIVE' AND a.role='STUDENT' AND a.email_verified_at IS NOT NULL
AND credits_adult(a.birth_date);
INSERT INTO credits_ledgerentry (id,owner_id,kind,amount,policy_id,reason_code,created_at)
SELECT
  gen_random_uuid(),w.owner_id,'SIGNUP_GRANT',p.signup_grant,p.id,'ACTIVATION_BACKFILL',statement_timestamp()
FROM credits_wallet w CROSS JOIN credits_creditpolicy p WHERE p.version=1;
INSERT INTO privacy_privacyaudit (id,actor_id,resource_id,action,outcome,reason,recorded_at)
SELECT
  gen_random_uuid(),e.owner_id,e.id,'CREDIT_SIGNUP_GRANT','ALLOW','ACTIVATION_BACKFILL',statement_timestamp()
FROM credits_ledgerentry e WHERE e.kind='SIGNUP_GRANT';
"""

REVERSE = (
    "\n".join(  # noqa: S608 -- fixed migration table identifiers, no external input.
        [
            f"DROP TRIGGER IF EXISTS credits_{table}_conserved ON credits_{table};"
            for table in TABLES
        ]
    )
    + r"""
DROP FUNCTION credits_conservation();
DROP FUNCTION credits_output_guard() CASCADE;
DROP FUNCTION credits_entry_guard() CASCADE;
DROP FUNCTION credits_hold_guard() CASCADE;
DROP FUNCTION credits_operation_guard() CASCADE;
DROP FUNCTION credits_policy_head() CASCADE;
DROP FUNCTION credits_policy_insert() CASCADE;
DROP FUNCTION credits_immutable() CASCADE;
DROP FUNCTION credits_adult(date);
DELETE FROM credits_policyhead;
DELETE FROM credits_creditpolicy;
"""
)


class Migration(migrations.Migration):
    dependencies = [
        ("credits", "0001_initial"),
        ("catalog", "0002_publication_guards"),
        ("privacy", "0003_purge_identity_guard"),
    ]
    operations = [migrations.RunSQL(SEED + GUARDS + BACKFILL, reverse_sql=REVERSE)]
