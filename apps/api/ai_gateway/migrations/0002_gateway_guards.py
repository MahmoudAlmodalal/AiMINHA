"""Immutable route evidence, nonresettable capacity and deferred credit/result binding.

The service remains responsible for authentication, consent, clocks and fencing.
These guards do not turn arbitrary database writers into trusted AI workers.
"""

from django.db import migrations

GUARDS = r"""
CREATE FUNCTION gateway_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable gateway evidence' USING ERRCODE='23514'; END $$;

CREATE FUNCTION gateway_approval_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND (
    (to_jsonb(NEW)-'revoked_at') IS DISTINCT FROM (to_jsonb(OLD)-'revoked_at')
    OR OLD.revoked_at IS NOT NULL OR NEW.revoked_at IS NULL
 )) THEN RAISE EXCEPTION 'approval identity is immutable' USING ERRCODE='23514'; END IF;
 IF length(btrim(NEW.model))=0 OR length(btrim(NEW.data_type))=0
    OR length(btrim(NEW.purpose))=0 OR length(btrim(NEW.region))=0
 THEN RAISE EXCEPTION 'scoped approval evidence required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_quota_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'quota evidence cannot be removed' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (to_jsonb(NEW)-ARRAY['reserved','consumed','blocked_reason']) IS DISTINCT FROM
      (to_jsonb(OLD)-ARRAY['reserved','consumed','blocked_reason'])
      OR NEW.consumed<OLD.consumed
      OR (OLD.blocked_reason<>'' AND NEW.blocked_reason='')
   THEN RAISE EXCEPTION 'quota baseline cannot be reset' USING ERRCODE='23514'; END IF;
 ELSE
   PERFORM pg_advisory_xact_lock(hashtextextended(
     NEW.provider||':'||NEW.account_ref::text||':'||NEW.unit,0));
   IF EXISTS (SELECT 1 FROM ai_gateway_quotawindow q
       WHERE q.provider=NEW.provider AND q.account_ref=NEW.account_ref AND q.unit=NEW.unit
         AND q.starts_at<NEW.ends_at AND NEW.starts_at<q.ends_at)
   THEN RAISE EXCEPTION 'quota windows cannot overlap' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_config_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a ai_gateway_providerapproval;
DECLARE q ai_gateway_quotawindow;
BEGIN
 IF length(btrim(NEW.model))=0 OR length(btrim(NEW.data_type))=0
    OR length(btrim(NEW.purpose))=0 OR length(btrim(NEW.region))=0
 THEN RAISE EXCEPTION 'scoped route required' USING ERRCODE='23514'; END IF;
 SELECT * INTO q FROM ai_gateway_quotawindow WHERE id=NEW.quota_id;
 IF q.provider IS DISTINCT FROM NEW.provider
 THEN RAISE EXCEPTION 'route quota scope mismatch' USING ERRCODE='23514'; END IF;
 IF NEW.approval_id IS NOT NULL THEN
   SELECT * INTO a FROM ai_gateway_providerapproval WHERE id=NEW.approval_id;
   IF (a.provider,a.model,a.classification,a.data_type,a.purpose,a.region) IS DISTINCT FROM
      (NEW.provider,NEW.model,NEW.classification,NEW.data_type,NEW.purpose,NEW.region)
   THEN RAISE EXCEPTION 'route approval scope mismatch' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_request_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE o credits_operation;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'gateway request cannot be removed' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (to_jsonb(NEW)-'state') IS DISTINCT FROM (to_jsonb(OLD)-'state')
      OR (NEW.state<>OLD.state AND (OLD.state IN ('SETTLED','RELEASED','RECONCILING') OR NOT (
        (OLD.state='PENDING' AND NEW.state IN ('RUNNING','RECONCILING'))
        OR (OLD.state='RUNNING' AND NEW.state IN ('SETTLED','RELEASED','RECONCILING'))
      )))
   THEN RAISE EXCEPTION 'invalid gateway state transition' USING ERRCODE='23514'; END IF;
 ELSE
   SELECT * INTO o FROM credits_operation WHERE id=NEW.operation_id;
   IF NEW.state<>'PENDING' OR o.owner_id IS DISTINCT FROM NEW.owner_id
      OR NEW.classification<>'PUBLIC/SYNTHETIC'
      OR o.state<>'RESERVED' OR NOT EXISTS (
        SELECT 1 FROM credits_syntheticinput f WHERE f.id=o.fixture_id AND f.owner_id=NEW.owner_id
      )
      OR jsonb_typeof(NEW.route_ids)<>'array' OR jsonb_array_length(NEW.route_ids)>3
      OR EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.route_ids) e
        WHERE jsonb_typeof(e)<>'string' OR (e#>>'{}')!~
        '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
      OR (SELECT count(*) FROM jsonb_array_elements(NEW.route_ids))<>
         (SELECT count(DISTINCT e) FROM jsonb_array_elements(NEW.route_ids) e)
   THEN RAISE EXCEPTION 'synthetic owner-bound gateway admission required' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_attempt_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r ai_gateway_gatewayrequest;
DECLARE c ai_gateway_providerconfig;
DECLARE a ai_gateway_providerapproval;
DECLARE q ai_gateway_quotawindow;
DECLARE o credits_operation;
DECLARE prior bigint;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'gateway attempt cannot be removed' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (to_jsonb(NEW)-ARRAY['state','used']) IS DISTINCT FROM
      (to_jsonb(OLD)-ARRAY['state','used']) OR OLD.state<>'DISPATCH_INTENT'
      OR NEW.state NOT IN ('SUCCEEDED','NOT_EXECUTED','REJECTED','UNKNOWN')
   THEN RAISE EXCEPTION 'attempt identity or terminal outcome is immutable' USING ERRCODE='23514';
   END IF;
 ELSE
   SELECT * INTO r FROM ai_gateway_gatewayrequest WHERE id=NEW.request_id;
   SELECT * INTO o FROM credits_operation WHERE id=r.operation_id;
   SELECT * INTO c FROM ai_gateway_providerconfig WHERE id=NEW.config_id;
   SELECT * INTO q FROM ai_gateway_quotawindow WHERE id=NEW.quota_id FOR UPDATE;
   SELECT * INTO a FROM ai_gateway_providerapproval WHERE id=NEW.approval_id FOR UPDATE;
   SELECT count(*) INTO prior FROM ai_gateway_attempt WHERE request_id=NEW.request_id;
   IF NEW.state<>'DISPATCH_INTENT' OR r.state<>'RUNNING' OR o.state<>'RUNNING'
      OR NEW.number<>prior+1 OR NEW.number>3
      OR EXISTS (SELECT 1 FROM ai_gateway_attempt p WHERE p.request_id=NEW.request_id
                  AND p.state<>'NOT_EXECUTED')
      OR (SELECT count(*) FROM ai_gateway_attempt p WHERE p.request_id=NEW.request_id
                  AND p.config_id=NEW.config_id)>=c.attempt_limit
      OR NOT c.enabled OR c.classification IS DISTINCT FROM r.classification
      OR c.quota_id IS DISTINCT FROM NEW.quota_id
      OR c.approval_id IS DISTINCT FROM NEW.approval_id OR NEW.approval_id IS NULL
      OR a.revoked_at IS NOT NULL OR a.approved_at>statement_timestamp()
      OR a.expires_at<=statement_timestamp()
      OR (a.provider,a.model,a.classification,a.data_type,a.purpose,a.region) IS DISTINCT FROM
         (c.provider,c.model,c.classification,c.data_type,c.purpose,c.region)
      OR NOT (r.route_ids ? NEW.config_id::text)
      OR NEW.consent_version<>r.consent_version OR length(NEW.fence_digest)<>64
      OR NEW.fence_digest IS DISTINCT FROM o.fence_digest
      OR NEW.lease_until<=NEW.created_at OR NEW.lease_until>o.reserve_until
      OR NEW.lease_until>NEW.created_at+make_interval(secs=>c.timeout_seconds)
      OR NEW.lease_until>q.ends_at OR NEW.lease_until>q.valid_until
      OR NEW.estimate<>c.max_units_per_attempt OR q.provider IS DISTINCT FROM c.provider
      OR q.measurement_ref IS NULL OR NOT q.free_only_confirmed OR q.blocked_reason<>''
      OR q.starts_at>statement_timestamp() OR q.ends_at<=statement_timestamp()
      OR q.observed_at>statement_timestamp() OR q.valid_until<=statement_timestamp()
      OR EXISTS (SELECT 1 FROM ai_gateway_attempt p JOIN ai_gateway_quotawindow prior_quota
          ON prior_quota.id=p.quota_id WHERE prior_quota.provider=q.provider
          AND prior_quota.account_ref=q.account_ref AND prior_quota.unit=q.unit AND (
            p.state='UNKNOWN' OR (p.state='DISPATCH_INTENT' AND
              (p.lease_until<=statement_timestamp() OR prior_quota.id<>q.id))))
      OR q.observed_used+NEW.estimate+coalesce((SELECT sum(CASE
            WHEN p.state IN ('DISPATCH_INTENT','UNKNOWN') THEN p.estimate
            ELSE coalesce(p.used,0) END)
            FROM ai_gateway_attempt p WHERE p.quota_id=q.id),0)>q.hard_limit
   THEN RAISE EXCEPTION 'approved measured free capacity required' USING ERRCODE='23514'; END IF;
 END IF;
 IF (NEW.state IN ('DISPATCH_INTENT','UNKNOWN') AND NEW.used IS NOT NULL)
    OR (NEW.state='NOT_EXECUTED' AND NEW.used IS DISTINCT FROM NEW.estimate)
    OR (NEW.state IN ('SUCCEEDED','REJECTED') AND
       (NEW.used IS NULL OR NEW.used>NEW.estimate))
 THEN RAISE EXCEPTION 'explicit measured attempt outcome required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_result_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r ai_gateway_gatewayrequest;
DECLARE expected jsonb;
BEGIN
 SELECT * INTO r FROM ai_gateway_gatewayrequest WHERE id=NEW.request_id;
 expected:=jsonb_build_object('language',r.language,'claims',jsonb_build_array(
   jsonb_build_object('text',CASE r.language WHEN 'ar' THEN 'معلومة منحة اصطناعية.'
   ELSE 'Synthetic scholarship information.' END,'citations',jsonb_build_array('fixture'))));
 IF NEW.owner_id IS DISTINCT FROM r.owner_id OR NEW.payload IS DISTINCT FROM expected
 THEN RAISE EXCEPTION 'exact validated synthetic evidence required' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION gateway_credit_timeout() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r ai_gateway_gatewayrequest;
BEGIN
 IF NEW.state='RECONCILING' AND OLD.state IS DISTINCT FROM NEW.state THEN
   SELECT * INTO r FROM ai_gateway_gatewayrequest WHERE operation_id=NEW.id FOR UPDATE;
   IF r.id IS NOT NULL AND r.state IN ('PENDING','RUNNING') THEN
     -- The existing credit timeout marker remains conservative for gateway work.
     -- Unknown usage keeps its full capacity hold and disables this quota window.
     PERFORM 1 FROM ai_gateway_quotawindow q WHERE q.id IN (
       SELECT a.quota_id FROM ai_gateway_attempt a WHERE a.request_id=r.id
         AND a.state='DISPATCH_INTENT') ORDER BY q.id FOR UPDATE;
     UPDATE ai_gateway_quotawindow q SET blocked_reason=CASE WHEN q.blocked_reason=''
       THEN 'USAGE_UNKNOWN' ELSE q.blocked_reason END
       WHERE q.id IN (SELECT a.quota_id FROM ai_gateway_attempt a WHERE a.request_id=r.id
         AND a.state='DISPATCH_INTENT');
     UPDATE ai_gateway_attempt SET state='UNKNOWN' WHERE request_id=r.id
       AND state='DISPATCH_INTENT';
     UPDATE ai_gateway_gatewayrequest SET state='RECONCILING' WHERE id=r.id;
   END IF;
 END IF;
 RETURN NULL;
END $$;

CREATE FUNCTION gateway_conservation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (SELECT 1 FROM ai_gateway_quotawindow q WHERE q.reserved IS DISTINCT FROM (
    SELECT coalesce(sum(a.estimate),0) FROM ai_gateway_attempt a
      WHERE a.quota_id=q.id AND a.state IN ('DISPATCH_INTENT','UNKNOWN'))
    OR q.consumed IS DISTINCT FROM (SELECT coalesce(sum(a.used),0) FROM ai_gateway_attempt a
      WHERE a.quota_id=q.id AND a.state NOT IN ('DISPATCH_INTENT','UNKNOWN'))
    OR ((EXISTS (SELECT 1 FROM ai_gateway_attempt a WHERE a.quota_id=q.id AND a.state='UNKNOWN')
       OR q.observed_used+q.reserved+q.consumed>q.hard_limit) AND q.blocked_reason='')
 ) THEN RAISE EXCEPTION 'gateway capacity conservation failed' USING ERRCODE='23514'; END IF;
 IF EXISTS (SELECT 1 FROM ai_gateway_gatewayrequest r
    JOIN credits_operation o ON o.id=r.operation_id
    LEFT JOIN ai_gateway_gatewayresult z ON z.request_id=r.id
    LEFT JOIN LATERAL (SELECT a.state FROM ai_gateway_attempt a WHERE a.request_id=r.id
                      ORDER BY a.number DESC LIMIT 1) last_attempt ON true
    WHERE o.owner_id<>r.owner_id OR o.state<>CASE r.state WHEN 'PENDING' THEN 'RESERVED'
      ELSE r.state END
      OR CASE WHEN r.state='SETTLED' THEN z.id IS NULL OR z.owner_id<>r.owner_id
           OR last_attempt.state IS DISTINCT FROM 'SUCCEEDED'
         ELSE z.id IS NOT NULL END
      OR CASE
        WHEN r.state='PENDING' THEN EXISTS (
          SELECT 1 FROM ai_gateway_attempt a WHERE a.request_id=r.id)
        WHEN r.state='RUNNING' THEN EXISTS (
          SELECT 1 FROM ai_gateway_attempt a WHERE a.request_id=r.id
            AND a.state NOT IN ('DISPATCH_INTENT','NOT_EXECUTED'))
        WHEN r.state='RECONCILING' THEN EXISTS (
          SELECT 1 FROM ai_gateway_attempt a WHERE a.request_id=r.id
            AND a.state IN ('SUCCEEDED','REJECTED'))
        WHEN r.state='SETTLED' THEN (
          SELECT count(*) FROM ai_gateway_attempt a WHERE a.request_id=r.id
            AND a.state='SUCCEEDED')<>1 OR EXISTS (
          SELECT 1 FROM ai_gateway_attempt a WHERE a.request_id=r.id
            AND a.state IN ('DISPATCH_INTENT','UNKNOWN','REJECTED'))
        WHEN r.state='RELEASED' THEN EXISTS (
          SELECT 1 FROM ai_gateway_attempt a WHERE a.request_id=r.id
            AND a.state IN ('DISPATCH_INTENT','UNKNOWN','SUCCEEDED'))
        ELSE true END
 ) THEN RAISE EXCEPTION 'gateway credit/result conservation failed' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;

CREATE TRIGGER gateway_credit_timeout_mirror AFTER UPDATE OF state ON credits_operation
 FOR EACH ROW EXECUTE FUNCTION gateway_credit_timeout();
CREATE TRIGGER gateway_approval_evidence BEFORE INSERT OR UPDATE OR DELETE ON
 ai_gateway_providerapproval FOR EACH ROW EXECUTE FUNCTION gateway_approval_guard();
CREATE TRIGGER gateway_quota_evidence BEFORE INSERT OR UPDATE OR DELETE ON ai_gateway_quotawindow
 FOR EACH ROW EXECUTE FUNCTION gateway_quota_guard();
CREATE TRIGGER gateway_config_evidence BEFORE INSERT ON ai_gateway_providerconfig
 FOR EACH ROW EXECUTE FUNCTION gateway_config_guard();
CREATE TRIGGER gateway_config_immutable BEFORE UPDATE OR DELETE ON ai_gateway_providerconfig
 FOR EACH ROW EXECUTE FUNCTION gateway_immutable();
CREATE TRIGGER gateway_request_transition BEFORE INSERT OR UPDATE OR DELETE ON
 ai_gateway_gatewayrequest FOR EACH ROW EXECUTE FUNCTION gateway_request_guard();
CREATE TRIGGER gateway_attempt_transition BEFORE INSERT OR UPDATE OR DELETE ON ai_gateway_attempt
 FOR EACH ROW EXECUTE FUNCTION gateway_attempt_guard();
CREATE TRIGGER gateway_result_evidence BEFORE INSERT ON ai_gateway_gatewayresult
 FOR EACH ROW EXECUTE FUNCTION gateway_result_guard();
CREATE TRIGGER gateway_result_immutable BEFORE UPDATE OR DELETE ON ai_gateway_gatewayresult
 FOR EACH ROW EXECUTE FUNCTION gateway_immutable();
CREATE TRIGGER gateway_routing_immutable BEFORE UPDATE OR DELETE ON ai_gateway_routingevent
 FOR EACH ROW EXECUTE FUNCTION gateway_immutable();
"""

TABLES = [
    "ai_gateway_quotawindow",
    "ai_gateway_attempt",
    "ai_gateway_gatewayrequest",
    "ai_gateway_gatewayresult",
    "credits_operation",
]
for table in TABLES:
    GUARDS += f"""
CREATE CONSTRAINT TRIGGER gateway_{table}_conserved AFTER INSERT OR UPDATE OR DELETE ON {table}
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION gateway_conservation();
"""

REVERSE = (
    "\n".join(  # noqa: S608 -- migration identifiers are fixed, no external input.
        f"DROP TRIGGER IF EXISTS gateway_{table}_conserved ON {table};" for table in TABLES
    )
    + r"""
DROP FUNCTION gateway_conservation();
DROP FUNCTION gateway_credit_timeout() CASCADE;
DROP FUNCTION gateway_result_guard() CASCADE;
DROP FUNCTION gateway_attempt_guard() CASCADE;
DROP FUNCTION gateway_request_guard() CASCADE;
DROP FUNCTION gateway_config_guard() CASCADE;
DROP FUNCTION gateway_quota_guard() CASCADE;
DROP FUNCTION gateway_approval_guard() CASCADE;
DROP FUNCTION gateway_immutable() CASCADE;
"""
)


class Migration(migrations.Migration):
    dependencies = [("ai_gateway", "0001_initial")]
    operations = [migrations.RunSQL(GUARDS, reverse_sql=REVERSE)]
