"""Atomic credit kernel. Synthetic local adapters only; no provider calls.

Lock order: account -> policy head -> global day -> student day -> operation ->
wallet/hold -> saved output/finalization. No network work occurs inside locks.
"""

import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, digest, require_admin, require_student

from credits.models import (
    SERVICES,
    CreditPolicy,
    Finalization,
    GlobalDay,
    Hold,
    LedgerEntry,
    Operation,
    PolicyHead,
    SavedOutput,
    StudentDay,
    SyntheticInput,
    Wallet,
)

BUSINESS_TZ = "Asia/Hebron"
FREE_SERVICES = [
    "BROWSING",
    "RULES_ELIGIBILITY",
    "MANUAL_EDITS",
    "SAME_VERSION_REEXPORT",
    "EXTENSION",
]
POLICY_FIELDS = (
    "signup_grant",
    "daily_spend_cap",
    "global_ai_cap",
    "matching_price",
    "cv_price",
    "document_price",
)


def business_day(now: datetime) -> date:
    if timezone.is_naive(now):
        raise ValueError("Credit clocks require an aware timestamp")
    return now.astimezone(ZoneInfo(BUSINESS_TZ)).date()


def payload_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@transaction.atomic
def initialize_policy() -> CreditPolicy:
    """Idempotent seed, also usable after an isolated test database flush."""
    policy, _ = CreditPolicy.objects.get_or_create(version=1, defaults={"reason": "DEFAULT_BETA"})
    head, _ = PolicyHead.objects.get_or_create(pk=1, defaults={"policy": policy})
    return CreditPolicy.objects.get(pk=head.policy_id)


def head_lock() -> PolicyHead:
    # Fetch the FK only after acquiring the head row. A joined FOR UPDATE can
    # lose a concurrently advanced head during PostgreSQL's row recheck.
    return PolicyHead.objects.select_for_update().get(pk=1)


def owner_lock(owner_id: Any, *, active: bool = True) -> Account:
    user = Account.objects.select_for_update().filter(pk=owner_id).first()
    if user is None:
        raise IdentityError("VERIFIED_ADULT_REQUIRED")
    if active:
        require_student(user)
    return user


def session_check(user: Account, proof: IdentitySession | None) -> None:
    if proof is not None:
        proof.refresh_from_db()
    now = timezone.now()
    if (
        proof is None
        or proof.account_id != user.pk
        or proof.epoch != user.session_epoch
        or proof.revoked_at is not None
        or now >= proof.expires_at
        or now >= proof.last_seen_at + timedelta(hours=24)
    ):
        raise IdentityError("SESSION_EXPIRED", 401, "Sign in again")


def policy_admin(user: Account, proof: IdentitySession | None) -> None:
    require_admin(user, proof, "COST_POLICY")
    session_check(user, proof)
    if proof is None or proof.mfa_verified_at is None or proof.mfa_verified_at > timezone.now():
        raise IdentityError("ADMIN_MFA_REQUIRED")


@transaction.atomic
def grant_signup(owner_id: Any) -> LedgerEntry:
    user = owner_lock(owner_id)
    policy = head_lock().policy
    existing = LedgerEntry.objects.filter(owner=user, kind="SIGNUP_GRANT").first()
    if existing is not None:
        return existing
    wallet, _ = Wallet.objects.get_or_create(owner=user)
    wallet = Wallet.objects.select_for_update().get(pk=user.pk)
    entry = LedgerEntry.objects.create(
        owner=user,
        kind="SIGNUP_GRANT",
        amount=policy.signup_grant,
        policy=policy,
        reason_code="VERIFIED_ADULT_ACTIVATION",
    )
    wallet.posted_balance += policy.signup_grant
    wallet.save(update_fields=["posted_balance"])
    audit(user, "credit_signup_grant", resource=entry.pk, reason="ONCE_ONLY")
    return entry


def local_synthetic_only() -> None:
    if not settings.LOCAL:
        raise IdentityError("AI_EXECUTION_UNAVAILABLE", 503, "AI execution is unavailable")


@transaction.atomic
def create_synthetic_input(owner_id: Any) -> UUID:
    local_synthetic_only()
    user = owner_lock(owner_id)
    return SyntheticInput.objects.create(owner=user).pk


def day_locks(user: Account, day: date) -> tuple[GlobalDay, StudentDay]:
    global_day, _ = GlobalDay.objects.get_or_create(day=day)
    global_day = GlobalDay.objects.select_for_update().get(pk=global_day.pk)
    student_day, _ = StudentDay.objects.get_or_create(owner=user, day=day)
    student_day = StudentDay.objects.select_for_update().get(pk=student_day.pk)
    return global_day, student_day


def operation_lock(user: Account, operation_id: Any) -> tuple[Operation, Wallet, StudentDay]:
    # Owner filter precedes all private state reads; missing and foreign IDs are indistinguishable.
    existing = Operation.objects.filter(pk=operation_id, owner=user).first()
    if existing is None:
        raise IdentityError("OPERATION_ACCESS_DENIED")
    _, day = day_locks(user, existing.captured_day)
    op = Operation.objects.select_for_update().get(pk=existing.pk, owner=user)
    wallet = Wallet.objects.select_for_update().get(pk=user.pk)
    return op, wallet, day


@transaction.atomic
def reserve(owner_id: Any, service: str, key: str, input_id: Any) -> Operation:
    local_synthetic_only()
    user = owner_lock(owner_id)
    policy = head_lock().policy
    if service not in SERVICES or re.fullmatch(r"[A-Za-z0-9._~-]{16,128}", key) is None:
        raise IdentityError("INVALID_CREDIT_REQUEST", 400, "Invalid operation request")
    fixture = SyntheticInput.objects.filter(pk=input_id, owner=user).first()
    if fixture is None:
        raise IdentityError("INPUT_ACCESS_DENIED")
    body = digest(service + ":" + str(fixture.pk))
    existing = Operation.objects.filter(owner=user, key_digest=digest(key)).first()
    if existing is not None:
        if existing.request_digest != body:
            raise IdentityError("IDEMPOTENCY_CONFLICT", 409, "Idempotency key already used")
        return existing
    now = timezone.now()
    day = business_day(now)
    global_day, student_day = day_locks(user, day)
    wallet = Wallet.objects.select_for_update().filter(pk=user.pk).first()
    price = {
        "MATCHING_AI": policy.matching_price,
        "CV_EXTRACTION": policy.cv_price,
        "DOCUMENT_NEW": policy.document_price,
    }[service]
    if wallet is None or wallet.posted_balance - wallet.reserved_balance < price:
        raise IdentityError("INSUFFICIENT_CREDITS", 409, "Insufficient available credits")
    if student_day.spent + student_day.reserved + price > policy.daily_spend_cap:
        raise IdentityError("DAILY_SPEND_CAP", 429, "Daily spending cap reached")
    if global_day.admitted_operations >= policy.global_ai_cap:
        raise IdentityError("GLOBAL_AI_CAP", 429, "Daily AI operation limit reached")
    op = Operation.objects.create(
        owner=user,
        service=service,
        price=price,
        policy=policy,
        fixture=fixture,
        captured_day=day,
        key_digest=digest(key),
        request_digest=body,
        created_at=now,
        reserve_until=now + timedelta(minutes=15),
    )
    Hold.objects.create(operation=op, amount=price)
    wallet.reserved_balance += price
    wallet.save(update_fields=["reserved_balance"])
    student_day.reserved += price
    student_day.save(update_fields=["reserved"])
    global_day.admitted_operations += 1
    global_day.save(update_fields=["admitted_operations"])
    audit(user, "credit_reserved", resource=op.pk, reason="SYNTHETIC_LOCAL")
    return op


def fence(op: Operation, token: str, *, allow_terminal: bool = False) -> None:
    if not token or not secrets.compare_digest(op.fence_digest, digest(token)):
        raise IdentityError("STALE_WORKER_FENCE", 409, "Operation claim is no longer current")
    if not allow_terminal and (op.state != "RUNNING" or timezone.now() >= op.reserve_until):
        raise IdentityError("OPERATION_NOT_RUNNING", 409, "Operation is awaiting reconciliation")


@transaction.atomic
def claim(owner_id: Any, operation_id: Any) -> str:
    local_synthetic_only()
    user = owner_lock(owner_id)
    head_lock()
    op, _, _ = operation_lock(user, operation_id)
    if op.state != "RESERVED" or timezone.now() >= op.reserve_until:
        raise IdentityError("OPERATION_NOT_CLAIMABLE", 409, "Operation cannot be dispatched")
    token = secrets.token_urlsafe(48)
    op.state, op.attempt, op.fence_digest = "RUNNING", op.attempt + 1, digest(token)
    op.save(update_fields=["state", "attempt", "fence_digest"])
    audit(user, "credit_claimed", resource=op.pk, reason="SYNTHETIC_LOCAL")
    return token


@transaction.atomic
def settle(owner_id: Any, operation_id: Any, token: str, payload: dict[str, Any]) -> Operation:
    local_synthetic_only()
    user = owner_lock(owner_id)
    head_lock()
    op, wallet, day = operation_lock(user, operation_id)
    fence(op, token, allow_terminal=op.state == "SETTLED")
    expected = {"fixture_id": str(op.fixture_id), "result": "SYNTHETIC_OK"}
    if payload != expected:
        raise IdentityError("OUTPUT_VALIDATION_FAILED", 409, "Output could not be validated")
    if op.state == "SETTLED":
        output = SavedOutput.objects.get(operation=op)
        if output.content_hash != payload_hash(payload):
            raise IdentityError("OUTPUT_CONFLICT", 409, "Output differs from the saved result")
        return op
    hold = Hold.objects.select_for_update().get(operation=op, state="ACTIVE")
    # Validation, persisted output, debit and terminal receipt share one transaction.
    output = SavedOutput.objects.create(
        operation=op,
        owner=user,
        payload=payload,
        content_hash=payload_hash(payload),
    )
    entry = LedgerEntry.objects.create(
        owner=user,
        kind="DEBIT",
        amount=-op.price,
        operation=op,
        policy=op.policy,
        reason_code="VALIDATED_SAVED_SYNTHETIC_OUTPUT",
    )
    Finalization.objects.create(
        operation=op,
        outcome="SETTLED",
        output=output,
        entry=entry,
        reason_code="VALIDATED_SAVED_SYNTHETIC_OUTPUT",
    )
    wallet.posted_balance -= op.price
    wallet.reserved_balance -= op.price
    wallet.save(update_fields=["posted_balance", "reserved_balance"])
    day.reserved -= op.price
    day.spent += op.price
    day.save(update_fields=["reserved", "spent"])
    hold.state, op.state = "SETTLED", "SETTLED"
    hold.save(update_fields=["state"])
    op.save(update_fields=["state"])
    audit(user, "credit_settled", resource=op.pk, reason="SYNTHETIC_LOCAL")
    return op


@transaction.atomic
def fail(owner_id: Any, operation_id: Any, token: str) -> Operation:
    """Trusted synchronous local failure, never a timeout/provider uncertainty claim."""
    local_synthetic_only()
    user = owner_lock(owner_id)
    head_lock()
    op, wallet, day = operation_lock(user, operation_id)
    fence(op, token, allow_terminal=op.state == "RELEASED")
    if op.state == "RELEASED":
        return op
    hold = Hold.objects.select_for_update().get(operation=op, state="ACTIVE")
    Finalization.objects.create(
        operation=op, outcome="RELEASED", reason_code="KNOWN_SYNTHETIC_FAILURE"
    )
    wallet.reserved_balance -= op.price
    wallet.save(update_fields=["reserved_balance"])
    day.reserved -= op.price
    day.save(update_fields=["reserved"])
    hold.state, op.state = "RELEASED", "RELEASED"
    hold.save(update_fields=["state"])
    op.save(update_fields=["state"])
    audit(user, "credit_released", resource=op.pk, reason="KNOWN_SYNTHETIC_FAILURE")
    return op


def _reconcile(op: Operation, now: datetime, actor: Account | None = None) -> Operation:
    if op.state in {"RESERVED", "RUNNING"}:
        op.state = "RECONCILING"
        op.reconciliation_started_at = now
        op.resolution_due_at = now + timedelta(hours=24)
        op.save(update_fields=["state", "reconciliation_started_at", "resolution_due_at"])
        audit(actor, "credit_reconciling", resource=op.pk, reason="OUTCOME_UNCERTAIN")
    return op


@transaction.atomic
def mark_uncertain(owner_id: Any, operation_id: Any, token: str) -> Operation:
    local_synthetic_only()
    user = owner_lock(owner_id)
    head_lock()
    op, _, _ = operation_lock(user, operation_id)
    fence(op, token, allow_terminal=op.state == "RECONCILING")
    return _reconcile(op, timezone.now(), user)


@transaction.atomic
def mark_expired(operation_id: Any, now: datetime | None = None) -> Operation:
    """Recoverable DB scan marker; account suspension must not discard holds."""
    now = now or timezone.now()
    owner_id = Operation.objects.filter(pk=operation_id).values_list("owner_id", flat=True).first()
    user = owner_lock(owner_id, active=False)
    head_lock()
    op, _, _ = operation_lock(user, operation_id)
    if now >= op.reserve_until:
        _reconcile(op, now)
    return op


@transaction.atomic
def publish_policy(
    actor: Account,
    proof: IdentitySession | None,
    data: dict[str, Any],
    expected_version: int,
    correlation: Any = None,
) -> CreditPolicy:
    user = Account.objects.select_for_update().get(pk=actor.pk)
    policy_admin(user, proof)
    head = head_lock()
    if head.policy.version != expected_version:
        raise IdentityError("STALE_REVISION", 412, "Review the current credit policy")
    if set(data) != {*POLICY_FIELDS, "reason"}:
        raise IdentityError("INVALID_POLICY", 400, "Invalid credit policy")
    for name in POLICY_FIELDS:
        minimum = 1 if name.endswith("price") else 0
        if type(data[name]) is not int or not minimum <= data[name] <= 1_000_000:
            raise IdentityError("INVALID_POLICY", 400, "Invalid credit policy")
    if not isinstance(data["reason"], str) or not 1 <= len(data["reason"].strip()) <= 1000:
        raise IdentityError("INVALID_POLICY", 400, "A policy change reason is required")
    policy = CreditPolicy.objects.create(
        version=head.policy.version + 1, actor=user, session_proof=proof, **data
    )
    head.policy = policy
    head.save(update_fields=["policy"])
    audit(user, "credit_policy_published", resource=policy.pk, correlation=correlation)
    return policy


def policy_data(policy: CreditPolicy) -> dict[str, Any]:
    return {
        "id": policy.pk,
        "version": policy.version,
        "signup_grant": policy.signup_grant,
        "daily_spend_cap": policy.daily_spend_cap,
        "global_ai_cap": policy.global_ai_cap,
        "timezone": BUSINESS_TZ,
        "reserve_minutes": 15,
        "reconciliation_target_hours": 24,
        "prices": {
            "MATCHING_AI": policy.matching_price,
            "CV_EXTRACTION": policy.cv_price,
            "DOCUMENT_NEW": policy.document_price,
        },
        "free_services": FREE_SERVICES,
        "ai_execution_available": False,
    }


@transaction.atomic
def read_wallet(actor: Account, proof: IdentitySession, correlation: Any = None) -> dict[str, Any]:
    user = owner_lock(actor.pk)
    session_check(user, proof)
    policy = head_lock().policy
    day = business_day(timezone.now())
    wallet = Wallet.objects.filter(owner=user).first()
    grant = LedgerEntry.objects.filter(owner=user, kind="SIGNUP_GRANT").first()
    student = StudentDay.objects.filter(owner=user, day=day).first()
    global_day = GlobalDay.objects.filter(day=day).first()
    posted, reserved = (wallet.posted_balance, wallet.reserved_balance) if wallet else (0, 0)
    spent, day_reserved = (student.spent, student.reserved) if student else (0, 0)
    admitted = global_day.admitted_operations if global_day else 0
    audit(user, "credit_wallet_read", correlation=correlation)
    return {
        "posted_balance": posted,
        "reserved_balance": reserved,
        "available_balance": posted - reserved,
        "signup_grant": {
            "awarded": grant is not None,
            "amount": grant.amount if grant else None,
            "policy_version": grant.policy.version if grant else None,
            "awarded_at": grant.created_at if grant else None,
        },
        "daily": {
            "day": day,
            "timezone": BUSINESS_TZ,
            "spent": spent,
            "reserved": day_reserved,
            "cap": policy.daily_spend_cap,
            "remaining": max(0, policy.daily_spend_cap - spent - day_reserved),
        },
        "global_daily": {
            "day": day,
            "timezone": BUSINESS_TZ,
            "admitted_operations": admitted,
            "cap": policy.global_ai_cap,
            "remaining": max(0, policy.global_ai_cap - admitted),
        },
        "policy": policy_data(policy),
    }


def operation_data(op: Operation) -> dict[str, Any]:
    return {
        "id": op.pk,
        "service": op.service,
        "state": op.state,
        "price": op.price,
        "policy_version": op.policy.version,
        "captured_day": op.captured_day,
        "created_at": op.created_at,
        "reserve_until": op.reserve_until,
        "reconciliation_started_at": op.reconciliation_started_at,
        "resolution_due_at": op.resolution_due_at,
        "resolution_overdue": op.state == "RECONCILING"
        and op.resolution_due_at is not None
        and timezone.now() >= op.resolution_due_at,
        "output_id": SavedOutput.objects.filter(operation=op).values_list("pk", flat=True).first(),
    }


@transaction.atomic
def read_history(
    actor: Account,
    proof: IdentitySession,
    page: int,
    page_size: int,
    *,
    entries: bool = False,
    correlation: Any = None,
) -> dict[str, Any]:
    user = owner_lock(actor.pk)
    session_check(user, proof)
    query = (
        (LedgerEntry.objects if entries else Operation.objects)
        .filter(owner=user)
        .select_related("policy")
        .order_by("-created_at", "-pk")
    )
    total = query.count()
    rows = query[(page - 1) * page_size : page * page_size]
    items = [
        (
            {
                "id": x.pk,
                "kind": x.kind,
                "amount": x.amount,
                "operation_id": x.operation_id,
                "policy_version": x.policy.version,
                "created_at": x.created_at,
                "reason_code": x.reason_code,
            }
            if entries
            else operation_data(x)
        )
        for x in rows
    ]
    audit(
        user,
        "credit_entries_read" if entries else "credit_operations_read",
        correlation=correlation,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@transaction.atomic
def read_operation(
    actor: Account, proof: IdentitySession, operation_id: Any, correlation: Any = None
) -> dict[str, Any]:
    user = owner_lock(actor.pk)
    session_check(user, proof)
    op = Operation.objects.select_related("policy").filter(pk=operation_id, owner=user).first()
    if op is None:
        raise IdentityError("OPERATION_ACCESS_DENIED")
    audit(user, "credit_operation_read", resource=op.pk, correlation=correlation)
    return operation_data(op)
