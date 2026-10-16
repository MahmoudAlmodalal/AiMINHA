from django.db import migrations

GUARDS = r"""
CREATE FUNCTION eligibility_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable eligibility evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER eligibility_profile_immutable BEFORE UPDATE OR DELETE ON eligibility_profileversion
FOR EACH ROW EXECUTE FUNCTION eligibility_immutable();
CREATE TRIGGER eligibility_rules_immutable BEFORE UPDATE OR DELETE ON eligibility_ruleset
FOR EACH ROW EXECUTE FUNCTION eligibility_immutable();
CREATE TRIGGER eligibility_evaluation_immutable BEFORE UPDATE OR DELETE ON eligibility_evaluation
FOR EACH ROW EXECUTE FUNCTION eligibility_immutable();
ALTER TABLE eligibility_profilehead ADD CONSTRAINT eligibility_head_same_owner
FOREIGN KEY(current_id,owner_id) REFERENCES eligibility_profileversion(id,owner_id);
ALTER TABLE eligibility_evaluation ADD CONSTRAINT eligibility_evaluation_same_owner
FOREIGN KEY(profile_version_id,owner_id) REFERENCES eligibility_profileversion(id,owner_id);

CREATE FUNCTION eligibility_profile_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.version<1 OR jsonb_typeof(NEW.facts)<>'object'
    OR NOT NEW.facts ?& ARRAY['nationalities','residency_country','degree_level','major',
                              'qualification','gpa','languages','preferred_countries']
    OR (SELECT count(*) FROM jsonb_object_keys(NEW.facts))<>8
    OR jsonb_typeof(NEW.confirmed_fields)<>'array' THEN
    RAISE EXCEPTION 'typed profile facts required' USING ERRCODE='23514';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements_text(NEW.confirmed_fields) f
             WHERE NOT NEW.facts ? f OR NEW.facts->f='null'::jsonb) THEN
    RAISE EXCEPTION 'null is not confirmed evidence' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER eligibility_profile_evidence_guard BEFORE INSERT ON eligibility_profileversion
FOR EACH ROW EXECUTE FUNCTION eligibility_profile_evidence();

CREATE FUNCTION eligibility_profile_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.owner_id<>OLD.owner_id OR NEW.revision<>OLD.revision+1 OR NOT EXISTS (
    SELECT 1 FROM eligibility_profileversion v WHERE v.id=NEW.current_id
    AND v.owner_id=NEW.owner_id AND v.version=NEW.revision
  ) THEN RAISE EXCEPTION 'invalid profile head' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER eligibility_profile_head_guard BEFORE UPDATE ON eligibility_profilehead
FOR EACH ROW EXECUTE FUNCTION eligibility_profile_head();

CREATE FUNCTION eligibility_rule_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE criteria_count integer;
BEGIN
  IF NOT catalog_admin_proof(NEW.actor_id,NEW.session_proof_id,'MODERATION') OR
     jsonb_typeof(NEW.rules)<>'array' OR jsonb_array_length(NEW.rules) NOT BETWEEN 1 AND 50 OR
     length(btrim(NEW.reason))=0 OR NOT EXISTS (
       SELECT 1 FROM catalog_scholarshipversion v
       JOIN catalog_scholarship s ON s.id=v.scholarship_id
       JOIN eligibility_rulehead h ON h.scholarship_id=s.id
       JOIN catalog_sourcerevision p ON p.id=v.source_revision_id
       JOIN catalog_source src ON src.current_id=p.id
       WHERE h.id=NEW.head_id AND v.id=NEW.scholarship_version_id
       AND v.content_hash=NEW.scholarship_hash AND s.visibility='PUBLISHED'
       AND s.published_version_id=v.id AND s.latest_id=v.id
       AND p.permission_status='APPROVED' AND p.date_checked IS NOT NULL
       AND (p.valid_until IS NULL OR p.valid_until>statement_timestamp())
       AND p.freshness_days IS NOT NULL AND v.source_checked_at IS NOT NULL
       AND v.source_checked_at + make_interval(days=>p.freshness_days)>statement_timestamp()
     ) THEN RAISE EXCEPTION 'current reviewed rule evidence required' USING ERRCODE='23514'; END IF;
  SELECT jsonb_array_length(criteria) INTO criteria_count
    FROM catalog_scholarshipversion WHERE id=NEW.scholarship_version_id;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(NEW.rules) r
             WHERE (r->>'criterion_index')::integer NOT BETWEEN 0 AND criteria_count-1) OR
    (NEW.complete AND (criteria_count=0 OR
      (SELECT count(DISTINCT r->>'criterion_index') FROM jsonb_array_elements(NEW.rules) r)
       <> criteria_count)) THEN
    RAISE EXCEPTION 'all exact criteria must be represented' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER eligibility_rule_evidence_guard BEFORE INSERT ON eligibility_ruleset
FOR EACH ROW EXECUTE FUNCTION eligibility_rule_evidence();

CREATE FUNCTION eligibility_rule_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.scholarship_id<>OLD.scholarship_id OR NEW.revision<>OLD.revision+1 OR NOT EXISTS (
    SELECT 1 FROM eligibility_ruleset r WHERE r.id=NEW.current_id
    AND r.head_id=NEW.id AND r.version=NEW.revision
  ) THEN RAISE EXCEPTION 'invalid rule head' USING ERRCODE='23514'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER eligibility_rule_head_guard BEFORE UPDATE ON eligibility_rulehead
FOR EACH ROW EXECUTE FUNCTION eligibility_rule_head();

CREATE FUNCTION eligibility_complete_head() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_TABLE_NAME='eligibility_profilehead' THEN
    IF NOT EXISTS (SELECT 1 FROM eligibility_profilehead h JOIN eligibility_profileversion v
      ON h.current_id=v.id WHERE h.id=NEW.id AND v.owner_id=h.owner_id AND v.version=h.revision)
    THEN RAISE EXCEPTION 'profile must commit complete' USING ERRCODE='23514'; END IF;
  ELSE
    IF NOT EXISTS (SELECT 1 FROM eligibility_rulehead h JOIN eligibility_ruleset r
      ON h.current_id=r.id WHERE h.id=NEW.id AND r.head_id=h.id AND r.version=h.revision)
    THEN RAISE EXCEPTION 'rules must commit complete' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER eligibility_profile_complete
AFTER INSERT OR UPDATE ON eligibility_profilehead
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION eligibility_complete_head();
CREATE CONSTRAINT TRIGGER eligibility_rule_complete AFTER INSERT OR UPDATE ON eligibility_rulehead
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION eligibility_complete_head();

CREATE FUNCTION eligibility_result_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE basis eligibility_ruleset;
DECLARE expected_status text;
DECLARE complete_basis boolean := false;
DECLARE checks jsonb;
BEGIN
  IF jsonb_typeof(NEW.result) IS DISTINCT FROM 'object' OR NOT NEW.result ?& ARRAY[
    'status','confidence','coverage_bps','fit_score_bps','fit_status','domains','rules',
    'missing_fields','limitations'] OR
    jsonb_typeof(NEW.result->'rules') IS DISTINCT FROM 'array' OR
    jsonb_typeof(NEW.result->'domains') IS DISTINCT FROM 'array' OR
    jsonb_typeof(NEW.result->'coverage_bps') IS DISTINCT FROM 'number' OR
    jsonb_typeof(NEW.result->'fit_score_bps') NOT IN ('null','number') OR
    NEW.result->>'confidence' IS DISTINCT FROM 'UNCALIBRATED' OR
    (NEW.result->>'coverage_bps')::integer NOT BETWEEN 0 AND 10000 THEN
    RAISE EXCEPTION 'typed complete evaluation result required' USING ERRCODE='23514';
  END IF;
  checks := NEW.result->'rules';
  IF NEW.rule_set_id IS NOT NULL THEN
    SELECT * INTO basis FROM eligibility_ruleset WHERE id=NEW.rule_set_id;
    IF basis.id IS NULL OR basis.scholarship_version_id<>NEW.scholarship_version_id OR
      jsonb_array_length(checks)<>jsonb_array_length(basis.rules) OR
      (SELECT count(DISTINCT r->>'key') FROM jsonb_array_elements(checks) r)
       <>jsonb_array_length(checks) OR EXISTS (
      SELECT 1 FROM jsonb_array_elements(checks) r WHERE
       jsonb_typeof(r) IS DISTINCT FROM 'object' OR NOT r ?& ARRAY[
         'key','criterion_index','field','domain','mandatory','result','reason_code',
         'expected_display','actual_display','evidence'] OR
       (r->>'result' IN ('PASS','FAIL','UNKNOWN')) IS NOT TRUE OR NOT EXISTS (
         SELECT 1 FROM jsonb_array_elements(basis.rules) original
         WHERE original->>'key'=r->>'key'
         AND original->'criterion_index'=r->'criterion_index'
         AND original->'mandatory'=r->'mandatory' AND original->'field'=r->'field'
         AND original->'domain'=r->'domain'
         AND original->>'evidence_text'=r->'evidence'->>'source_text'
         AND (original->>'verified'='true' OR r->>'result'='UNKNOWN')
       )
    ) THEN RAISE EXCEPTION 'every pinned rule requires its exact check'
      USING ERRCODE='23514'; END IF;
    complete_basis := basis.complete;
  ELSIF jsonb_array_length(checks)<>0 THEN
    RAISE EXCEPTION 'no invented comparison without a rule basis' USING ERRCODE='23514';
  END IF;
  IF EXISTS (SELECT 1 FROM jsonb_array_elements(checks) r
             WHERE r->>'mandatory'='true' AND r->>'result'='FAIL') THEN
    expected_status := 'INELIGIBLE';
  ELSIF NOT complete_basis OR jsonb_array_length(checks)=0 OR NOT EXISTS (
    SELECT 1 FROM jsonb_array_elements(checks) r WHERE r->>'result' IN ('PASS','FAIL')
  ) OR EXISTS (SELECT 1 FROM jsonb_array_elements(checks) r
               WHERE r->>'mandatory'='true' AND r->>'result'='UNKNOWN') THEN
    expected_status := 'INSUFFICIENT_INFORMATION';
  ELSE expected_status := 'ELIGIBLE'; END IF;
  IF NEW.result->>'status' IS DISTINCT FROM expected_status THEN
    RAISE EXCEPTION 'rule-first aggregate decision required' USING ERRCODE='23514';
  END IF;
  IF (NEW.result->'fit_score_bps'<>'null'::jsonb AND (
      (NEW.result->>'coverage_bps')::integer<7000 OR
      (NEW.result->>'fit_score_bps')::integer NOT BETWEEN 0 AND 10000)) OR
    ((NEW.result->>'coverage_bps')::integer<7000 AND
      NEW.result->>'fit_status' IS DISTINCT FROM 'INSUFFICIENT_COVERAGE') OR
    ((NEW.result->>'coverage_bps')::integer>=7000 AND
      (NEW.result->>'fit_status' IS DISTINCT FROM 'AVAILABLE' OR
       NEW.result->'fit_score_bps'='null'::jsonb)) THEN
    RAISE EXCEPTION 'coverage floor cannot be bypassed' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER eligibility_result_evidence_guard BEFORE INSERT ON eligibility_evaluation
FOR EACH ROW EXECUTE FUNCTION eligibility_result_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("eligibility", "0001_initial")]
    # Evidence guards are forward-only; do not remove them automatically from saved data.
    operations = [migrations.RunSQL(GUARDS)]
