"""Owned support tickets, the measured first-response SLA and audited agent access.

Ownership rules: a student reads only their own ticket; a support administrator reads
only a ticket currently assigned to them, and only the attachments explicitly shared on
it. Nothing here grants access to the private file library.
"""

from datetime import timedelta
from typing import Any

from credits import services as credits
from credits.models import CreditPolicy, GlobalAiDay, GlobalDay, PolicyHead
from django.db import transaction
from django.db.models import F, IntegerField, OuterRef, Subquery
from django.utils import timezone
from identity.models import Account, IdentitySession
from identity.security import IdentityError, audit, require_admin, require_student
from privacy import services as privacy
from privacy.models import TicketAccess, TicketShare

from support import calendar as workcal
from support import triage
from support.models import (
    PRIORITIES,
    STATES,
    SlaCycle,
    SupportAiDay,
    SupportCalendar,
    SupportCalendarHead,
    Ticket,
    TicketEvent,
    TicketMessage,
    TicketRating,
)

MAX_BODY = 12000
MAX_SUBJECT = 256
MAX_CATEGORY = 128
# The sourced experiment allows five free AI support messages per student per day.
MAX_AI_DAILY_MESSAGES = 5
SUPPORT_SCOPE = "SUPPORT"
QUEUE_SCOPE = "SUPPORT_QUEUE"
ASSIGNMENT_SCOPE = "SUPPORT_ASSIGNMENT"
POLICY_SCOPE = "SUPPORT_POLICY"
OPEN_STATES = ("NEW", "AI_HANDLING", "AWAITING_ADMIN", "AWAITING_STUDENT")

# An administrator note that only acknowledges receipt is not the substantive human
# reply that satisfies the measured obligation. The rule is server-side so an agent
# cannot declare a one-word note substantive.
ACKNOWLEDGEMENT_PHRASES = (
    "we will look into",
    "we are looking into",
    "we will review",
    "we are reviewing",
    "we will get back to you",
    "thank you for contacting",
    "received your request",
    "we have received your",
    "سنراجع",
    "سنتابع",
    "تم استلام طلبك",
    "شكرا لتواصلك",
)
# A student reporting that the advice did not help counts as a failed answer.
NOT_HELPFUL_PHRASES = (
    "did not help",
    "didn't help",
    "does not help",
    "doesn't help",
    "not helpful",
    "did not work",
    "didn't work",
    "still not working",
    "still failing",
    "still waiting",
    "no answer yet",
    "لم تفد",
    "لم تساعد",
    "لم تعمل",
    "لا تزال",
    "لم أحصل على رد",
)


def student(user: Account, proof: IdentitySession) -> Account:
    # The account lock only matters inside a write transaction; read-only callers
    # must not open an implicit transaction boundary.
    if transaction.get_connection().in_atomic_block:
        user = Account.objects.select_for_update().get(pk=user.pk)
    else:
        user = Account.objects.get(pk=user.pk)
    require_student(user)
    proof.refresh_from_db()
    now = timezone.now()
    if (
        proof.account_id != user.pk
        or proof.epoch != user.session_epoch
        or proof.revoked_at is not None
        or now >= proof.expires_at
        or now >= proof.last_seen_at + timedelta(hours=24)
    ):
        raise IdentityError("SESSION_EXPIRED", 401, "Sign in again")
    return user


def expected_revision(request: Any) -> int:
    raw = request.headers.get("If-Match", "")
    if len(raw) < 3 or not raw.startswith('"') or not raw.endswith('"') or not raw[1:-1].isdigit():
        raise IdentityError("PRECONDITION_REQUIRED", 412, "A quoted current revision is required")
    return int(raw[1:-1])


def head_policy() -> SupportCalendar:
    """The latest published calendar policy."""
    head = SupportCalendarHead.objects.select_related("policy").filter(pk=1).first()
    if head is None:
        raise IdentityError("SUPPORT_POLICY_UNAVAILABLE", 503, "Support policy is unavailable")
    return head.policy


def policy_at(now: Any) -> SupportCalendar:
    """The calendar policy in force at an instant; a future policy waits for its date."""
    now = now or timezone.now()
    policy = (
        SupportCalendar.objects.filter(effective_at__lte=now)
        .order_by("-effective_at", "-version")
        .first()
    )
    if policy is None:
        policy = SupportCalendar.objects.order_by("version").first()
    if policy is None:
        raise IdentityError("SUPPORT_POLICY_UNAVAILABLE", 503, "Support policy is unavailable")
    return policy


def _calendar(policy: SupportCalendar) -> workcal.WorkingCalendar:
    try:
        return workcal.calendar_from_policy(policy)
    except workcal.CalendarError as exc:
        raise IdentityError("SUPPORT_POLICY_INVALID", 503, "Support policy is unusable") from exc


def _owned_ticket(user: Account, ticket_id: Any, *, lock: bool = False) -> Ticket:
    query = Ticket.objects.select_related("sla_policy").filter(pk=ticket_id, owner=user)
    if lock:
        query = query.select_for_update(of=("self",))
    ticket = query.first()
    if ticket is None:
        raise IdentityError("TICKET_NOT_FOUND", 404, "Ticket not found")
    return ticket


def _assigned_ticket(
    actor: Account, ticket_id: Any, *, lock: bool = False, audit_denial: bool = True
) -> Ticket:
    query = Ticket.objects.select_related("sla_policy").filter(pk=ticket_id)
    if lock:
        query = query.select_for_update(of=("self",))
    ticket = query.first()
    if ticket is None:
        if audit_denial:
            audit(actor, "support_ticket_read", "DENY", reason="TICKET_NOT_FOUND")
        raise IdentityError("TICKET_NOT_FOUND", 404, "Ticket not found")
    if ticket.assigned_admin_id != actor.pk:
        if audit_denial:
            # Denial audits run outside the aggregate transaction so they survive it.
            audit(actor, "support_ticket_read", "DENY", resource=ticket.pk, reason="NOT_ASSIGNED")
        raise IdentityError(
            "TICKET_ASSIGNMENT_REQUIRED", 403, "Ticket is assigned to another agent"
        )
    return ticket


def authorize_assigned(actor: Account, proof: IdentitySession, ticket_id: Any) -> None:
    """Assigned-ticket guard: current administrator role, support scope and MFA proof.

    Run before an idempotent command so a replay cannot return a cached ticket to a
    caller who is no longer allowed to receive it.
    """
    require_admin(actor, proof, SUPPORT_SCOPE)
    ticket = _assigned_ticket(actor, ticket_id)
    audit(actor, "support_ticket_access", resource=ticket.pk)


def authorize_owner(actor: Account, proof: IdentitySession, ticket_id: Any) -> None:
    """Owner guard for an idempotent student command replay.

    A ticket authorization row without a support ticket still identifies the owner,
    which keeps the Phase06 explicit-share contract intact.
    """
    owner = student(actor, proof)
    ticket = Ticket.objects.filter(pk=ticket_id, owner=owner).first()
    if ticket is None:
        access = TicketAccess.objects.filter(pk=ticket_id, owner=owner).first()
        if access is None:
            raise IdentityError("TICKET_NOT_FOUND", 404, "Ticket not found")
        audit(owner, "support_ticket_access", resource=ticket_id)
        return
    audit(owner, "support_ticket_access", resource=ticket.pk)


def _persist(ticket: Ticket) -> None:
    """Persist the aggregate changes. Callers hold the ticket row lock."""
    ticket.save()


def _event(
    ticket: Ticket,
    kind: str,
    *,
    to_state: str,
    from_state: str = "",
    actor: Account | None = None,
    reason: str = "",
    now: Any = None,
) -> TicketEvent:
    moment = now or timezone.now()
    sequence = ticket.head_sequence + 1
    ticket.head_sequence = sequence
    return TicketEvent.objects.create(
        ticket=ticket,
        sequence=sequence,
        from_state=from_state,
        to_state=to_state,
        kind=kind,
        actor=actor,
        reason=reason,
        observed_at=moment,
        recorded_at=timezone.now(),
    )


def _message(
    ticket: Ticket,
    author_kind: str,
    body: str,
    *,
    actor: Account | None = None,
    substantive: bool = False,
    now: Any = None,
) -> TicketMessage:
    moment = now or timezone.now()
    sequence = ticket.messages.count() + 1
    return TicketMessage.objects.create(
        ticket=ticket,
        sequence=sequence,
        author_kind=author_kind,
        author=actor,
        body=body,
        substantive=substantive,
        created_at=moment,
    )


def _cycle(ticket: Ticket) -> SlaCycle | None:
    if ticket.sla_cycle_no < 1:
        return None
    return SlaCycle.objects.filter(ticket=ticket, cycle_no=ticket.sla_cycle_no).first()


def _start_clock(ticket: Ticket, policy: SupportCalendar, now: Any) -> None:
    """Begin (or keep) the measured first-human-response cycle."""
    if ticket.human_requested_at is not None:
        return
    moment = now or timezone.now()
    target = int(policy.targets.get(ticket.priority, policy.targets.get("NORMAL", 1440)))
    calendar = _calendar(policy)
    ticket.human_requested_at = moment
    ticket.sla_policy = policy
    ticket.sla_target_minutes = target
    ticket.sla_due_at = workcal.add_business_seconds(calendar, moment, target * 60)
    ticket.sla_cycle_no += 1
    ticket.sla_warning_at = None
    ticket.sla_breached_at = None
    SlaCycle.objects.create(
        ticket=ticket,
        cycle_no=ticket.sla_cycle_no,
        started_at=moment,
        target_minutes=target,
        due_at=ticket.sla_due_at,
    )


def _finish_clock(ticket: Ticket, now: Any) -> None:
    """Close the measured cycle with the first substantive human reply."""
    if ticket.first_human_response_at is not None:
        return
    moment = now or timezone.now()
    ticket.first_human_response_at = moment
    cycle = _cycle(ticket)
    if cycle is not None:
        cycle.responded_at = moment
        cycle.state = "COMPLETED"
        cycle.save(update_fields=["responded_at", "state"])
    # A reply after the deadline is a breach the moment it is posted, even when the
    # bounded worker has not run since.
    if ticket.sla_due_at is not None and moment > ticket.sla_due_at:
        ticket.sla_breached_at = moment
        if cycle is not None:
            cycle.breached_at = moment
            cycle.save(update_fields=["breached_at"])
        _event(
            ticket,
            "SLA_BREACH",
            to_state=ticket.state,
            reason="FIRST_HUMAN_RESPONSE_OVERDUE",
            now=moment,
        )
        audit(None, "support_sla_breach", resource=ticket.pk, reason="LATE_FIRST_RESPONSE")


def _set_state(
    ticket: Ticket, state: str, kind: str, *, actor: Account | None, reason: str, now: Any
) -> None:
    previous = ticket.state
    ticket.state = state
    ticket.updated_at = now or timezone.now()
    _event(
        ticket,
        kind,
        to_state=state,
        from_state=previous,
        actor=actor,
        reason=reason,
        now=now,
    )


def is_acknowledgement(body: str) -> bool:
    normalized = " ".join(str(body).lower().split())
    return any(phrase in normalized for phrase in ACKNOWLEDGEMENT_PHRASES)


def reports_no_help(body: str) -> bool:
    normalized = " ".join(str(body).lower().split())
    return any(phrase in normalized for phrase in NOT_HELPFUL_PHRASES)


@transaction.atomic
def create_ticket(
    user: Account, proof: IdentitySession, data: dict[str, Any], correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    category = str(data["category"]).strip()
    subject = str(data["subject"]).strip()
    body = str(data["message"]).strip()
    urgency = str(data.get("urgency") or "NORMAL").upper()
    if not category or len(category) > MAX_CATEGORY:
        raise IdentityError("INVALID_TICKET", 400, "A ticket category is required")
    if not subject or len(subject) > MAX_SUBJECT:
        raise IdentityError("INVALID_TICKET", 400, "A ticket subject is required")
    if not body or len(body) > MAX_BODY:
        raise IdentityError("INVALID_TICKET", 400, "A ticket message is required")
    if urgency not in PRIORITIES:
        raise IdentityError("INVALID_TICKET", 400, "A known urgency is required")
    now = timezone.now()
    policy = policy_at(now)
    access = TicketAccess.objects.create(owner=owner)
    ticket = Ticket.objects.create(
        access=access,
        owner=owner,
        category=category,
        subject=subject,
        state="NEW",
        priority=urgency,
        sla_policy=policy,
        created_at=now,
        updated_at=now,
    )
    _message(ticket, "STUDENT", body, actor=owner, substantive=True, now=now)
    _event(ticket, "CREATED", to_state="NEW", actor=owner, reason="STUDENT_OPENED", now=now)
    if data.get("request_human"):
        _start_clock(ticket, policy, now)
        _event(ticket, "HUMAN_REQUESTED", to_state="NEW", actor=owner, now=now)
        _set_state(
            ticket,
            "AWAITING_ADMIN",
            "STATE_CHANGED",
            actor=owner,
            reason="HUMAN_REQUESTED",
            now=now,
        )
    audit(owner, "support_ticket_created", resource=ticket.pk, correlation=correlation)
    _persist(ticket)
    return ticket_data(ticket)


@transaction.atomic
def list_tickets(
    user: Account, proof: IdentitySession, page: int, page_size: int, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    query = Ticket.objects.filter(owner=owner).order_by("-created_at", "-pk")
    total = query.count()
    rows = query[(page - 1) * page_size : page * page_size]
    audit(owner, "support_ticket_listed", correlation=correlation)
    return {
        "items": [ticket_data(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@transaction.atomic
def read_ticket(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id)
    audit(owner, "support_ticket_read", resource=ticket.pk, correlation=correlation)
    return ticket_data(ticket)


@transaction.atomic
def read_messages(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id)
    rows = ticket.messages.order_by("sequence")
    audit(owner, "support_messages_read", resource=ticket.pk, correlation=correlation)
    return {"items": [message_data(row) for row in rows]}


@transaction.atomic
def read_history(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id)
    rows = ticket.events.order_by("sequence")
    audit(owner, "support_history_read", resource=ticket.pk, correlation=correlation)
    return {"items": [event_data(row) for row in rows]}


@transaction.atomic
def post_message(
    user: Account,
    proof: IdentitySession,
    ticket_id: Any,
    body: str,
    request_human: bool,
    correlation: Any,
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id, lock=True)
    text = str(body).strip()
    if not text or len(text) > MAX_BODY:
        raise IdentityError("INVALID_MESSAGE", 400, "A message body is required")
    if ticket.state not in OPEN_STATES:
        raise IdentityError("TICKET_CLOSED", 409, "This ticket is no longer open")
    now = timezone.now()
    policy = policy_at(now)
    _message(ticket, "STUDENT", text, actor=owner, substantive=True, now=now)
    ticket.row_version += 1
    ticket.updated_at = now
    if request_human:
        _start_clock(ticket, policy, now)
        _event(ticket, "HUMAN_REQUESTED", to_state=ticket.state, actor=owner, now=now)
        if ticket.state != "AWAITING_ADMIN":
            _set_state(
                ticket,
                "AWAITING_ADMIN",
                "STATE_CHANGED",
                actor=owner,
                reason="HUMAN_REQUESTED",
                now=now,
            )
    elif reports_no_help(text):
        # The student says the advice did not help: count it and hand off at two.
        ticket.ai_failure_streak += 1
        reasons = ["REPEATED_FAILURE"] if ticket.ai_failure_streak >= 2 else ["ADVICE_DID_NOT_HELP"]
        _event(
            ticket,
            "MESSAGE_ADDED",
            to_state=ticket.state,
            actor=owner,
            reason=",".join(reasons),
            now=now,
        )
        if ticket.ai_failure_streak >= 2:
            _start_clock(ticket, policy, now)
            _set_state(
                ticket,
                "AWAITING_ADMIN",
                "STATE_CHANGED",
                actor=owner,
                reason="REPEATED_FAILURE",
                now=now,
            )
            _event(
                ticket,
                "AI_HANDOFF",
                to_state="AWAITING_ADMIN",
                actor=owner,
                reason="REPEATED_FAILURE",
                now=now,
            )
    elif ticket.state == "AWAITING_STUDENT":
        _set_state(
            ticket,
            "AWAITING_ADMIN",
            "STATE_CHANGED",
            actor=owner,
            reason="STUDENT_REPLIED",
            now=now,
        )
    else:
        _event(
            ticket,
            "MESSAGE_ADDED",
            to_state=ticket.state,
            actor=owner,
            reason="STUDENT_REPLIED",
            now=now,
        )
    audit(owner, "support_message_posted", resource=ticket.pk, correlation=correlation)
    _persist(ticket)
    return ticket_data(ticket)


@transaction.atomic
def ai_reply(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id, lock=True)
    if ticket.state not in ("NEW", "AI_HANDLING"):
        raise IdentityError("AI_HANDLING_UNAVAILABLE", 409, "AI assistance is not available now")
    policy = policy_at(timezone.now())
    now = timezone.now()
    allowance = _ai_allowance(owner, policy, now)
    if allowance is not None:
        _start_clock(ticket, policy, now)
        _set_state(
            ticket,
            "AWAITING_ADMIN",
            "STATE_CHANGED",
            actor=owner,
            reason=allowance,
            now=now,
        )
        _event(
            ticket,
            "AI_LIMIT_REACHED",
            to_state="AWAITING_ADMIN",
            actor=owner,
            reason=allowance,
            now=now,
        )
        audit(
            owner, "support_ai_limit", resource=ticket.pk, reason=allowance, correlation=correlation
        )
        _persist(ticket)
        return {
            "ticket": ticket_data(ticket),
            "ai": {
                "available": False,
                "reason": allowance,
                "category": ticket.suggested_category,
                "priority": ticket.suggested_priority,
                "confidence": ticket.triage_confidence,
            },
        }
    context = triage.build_context(ticket, list(ticket.messages.order_by("sequence")), owner.locale)
    try:
        outcome = triage.classify(context)
    except triage.TriageFailure as error:
        ticket.ai_failure_streak += 1
        ticket.row_version += 1
        reasons = ["REPEATED_FAILURE"] if ticket.ai_failure_streak >= 2 else ["LOW_CONFIDENCE"]
        _message(
            ticket,
            "AI",
            "لم أتمكن من تصنيف طلبك بدقة. سأحوّله إلى دعم بشري."
            if owner.locale == "ar"
            else "I could not classify your request reliably. It is handed to a human agent.",
            actor=None,
            substantive=True,
            now=now,
        )
        _event(
            ticket,
            "AI_HANDOFF",
            to_state="AWAITING_ADMIN",
            actor=owner,
            reason=",".join(reasons),
            now=now,
        )
        _start_clock(ticket, policy, now)
        _set_state(
            ticket,
            "AWAITING_ADMIN",
            "STATE_CHANGED",
            actor=owner,
            reason=",".join(reasons),
            now=now,
        )
        audit(
            owner,
            "support_ai_failed",
            outcome="DENY",
            resource=ticket.pk,
            reason=str(error)[:64],
            correlation=correlation,
        )
        _persist(ticket)
        return {
            "ticket": ticket_data(ticket),
            "ai": {
                "available": False,
                "reason": reasons[0],
                "category": "",
                "priority": "",
                "confidence": None,
            },
        }
    _consume_ai_allowance(owner, now)
    reasons = list(outcome.reasons)
    if outcome.handoff and "LOW_CONFIDENCE" in reasons:
        streak = _uncertain_streak(owner, now, increment=True)
        ticket.ai_failure_streak = streak
        if streak >= 2:
            reasons.append("REPEATED_FAILURE")
    else:
        ticket.ai_failure_streak = 0
    final_reasons = tuple(dict.fromkeys(reasons))
    ticket.suggested_category = outcome.category
    ticket.suggested_priority = outcome.priority
    ticket.triage_confidence = outcome.confidence
    ticket.triage_reason = ",".join(final_reasons)
    ticket.ai_message_count += 1
    ticket.row_version += 1
    ticket.updated_at = now
    _message(ticket, "AI", outcome.body, actor=None, substantive=True, now=now)
    if ticket.state == "NEW":
        _set_state(ticket, "AI_HANDLING", "STATE_CHANGED", actor=owner, reason="AI_REPLY", now=now)
    else:
        _event(ticket, "AI_REPLIED", to_state=ticket.state, actor=owner, now=now)
    if outcome.handoff:
        _start_clock(ticket, policy, now)
        _set_state(
            ticket,
            "AWAITING_ADMIN",
            "STATE_CHANGED",
            actor=owner,
            reason=",".join(final_reasons),
            now=now,
        )
        _event(
            ticket,
            "AI_HANDOFF",
            to_state="AWAITING_ADMIN",
            actor=owner,
            reason=",".join(final_reasons),
            now=now,
        )
    audit(owner, "support_ai_replied", resource=ticket.pk, correlation=correlation)
    _persist(ticket)
    return {
        "ticket": ticket_data(ticket),
        "ai": {
            "available": True,
            "reason": ",".join(final_reasons),
            "category": outcome.category,
            "priority": outcome.priority,
            "confidence": outcome.confidence,
        },
    }


def _credit_head() -> Any:
    """The credits policy head, seeded idempotently when a fresh database lacks it."""
    head = PolicyHead.objects.select_for_update().filter(pk=1).first()
    if head is not None:
        return head.policy
    policy = CreditPolicy.objects.order_by("version").first()
    if policy is None:
        credits.initialize_policy()
        policy = CreditPolicy.objects.order_by("version").first()
    PolicyHead.objects.get_or_create(id=1, defaults={"policy": policy})
    return policy


def _ai_allowance(owner: Account, policy: SupportCalendar, now: Any) -> str | None:
    """Return the reason the AI allowance is exhausted, or None when it is available."""
    day = credits.business_day(now)
    credit_policy = _credit_head()
    global_day, _ = GlobalDay.objects.get_or_create(day=day)
    global_day = GlobalDay.objects.select_for_update().get(pk=global_day.pk)
    global_ai_day, _ = GlobalAiDay.objects.get_or_create(day=day)
    global_ai_day = GlobalAiDay.objects.select_for_update().get(pk=global_ai_day.pk)
    cap = credit_policy.global_ai_cap
    if cap == 0 or global_day.admitted_operations + global_ai_day.operations >= cap:
        return "GLOBAL_BUDGET_EXHAUSTED"
    ai_day, _ = SupportAiDay.objects.get_or_create(owner=owner, day=day)
    ai_day = SupportAiDay.objects.select_for_update().get(pk=ai_day.pk)
    if ai_day.messages >= policy.ai_daily_messages:
        return "DAILY_ALLOWANCE_EXHAUSTED"
    return None


def _consume_ai_allowance(owner: Account, now: Any) -> None:
    day = credits.business_day(now)
    global_day, _ = GlobalDay.objects.get_or_create(day=day)
    global_day = GlobalDay.objects.select_for_update().get(pk=global_day.pk)
    global_ai_day, _ = GlobalAiDay.objects.get_or_create(day=day)
    global_ai_day = GlobalAiDay.objects.select_for_update().get(pk=global_ai_day.pk)
    global_ai_day.operations += 1
    global_ai_day.save(update_fields=["operations"])
    ai_day, _ = SupportAiDay.objects.get_or_create(owner=owner, day=day)
    ai_day = SupportAiDay.objects.select_for_update().get(pk=ai_day.pk)
    ai_day.messages += 1
    ai_day.save(update_fields=["messages"])


def _uncertain_streak(owner: Account, now: Any, *, increment: bool) -> int:
    """Consecutive uncertain AI answers for this student on this business day."""
    day = credits.business_day(now)
    row, _ = SupportAiDay.objects.get_or_create(owner=owner, day=day)
    row = SupportAiDay.objects.select_for_update().get(pk=row.pk)
    row.uncertain_streak = row.uncertain_streak + 1 if increment else 0
    row.save(update_fields=["uncertain_streak"])
    return row.uncertain_streak


def _objection_deadline(ticket: Ticket, policy: SupportCalendar) -> Any:
    """The last instant the student may object to the resolution."""
    if ticket.state == "CLOSED" and ticket.reopen_until is not None:
        return ticket.reopen_until
    if ticket.resolved_at is not None:
        return ticket.resolved_at + timedelta(days=policy.closure_days)
    return None


@transaction.atomic
def student_transition(
    user: Account,
    proof: IdentitySession,
    ticket_id: Any,
    to_state: str,
    reason: str,
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id, lock=True)
    if ticket.row_version != expected:
        raise IdentityError("STALE_REVISION", 412, "Reload the current ticket")
    now = timezone.now()
    policy = policy_at(now)
    if to_state == "AWAITING_ADMIN":
        if ticket.state in ("RESOLVED", "CLOSED"):
            deadline = _objection_deadline(ticket, policy)
            if deadline is None or now > deadline:
                raise IdentityError(
                    "REOPEN_WINDOW_CLOSED", 409, "This ticket can no longer be reopened"
                )
            # A new cycle starts with clean lifecycle timestamps.
            ticket.human_requested_at = None
            ticket.first_human_response_at = None
            ticket.sla_warning_at = None
            ticket.sla_breached_at = None
            ticket.closed_at = None
            ticket.resolved_at = None
            ticket.rating_window_until = None
            ticket.ai_failure_streak = 0
            _start_clock(ticket, policy, now)
            _set_state(
                ticket,
                "AWAITING_ADMIN",
                "STATE_CHANGED",
                actor=owner,
                reason="STUDENT_REOPENED",
                now=now,
            )
            _event(ticket, "REOPENED", to_state="AWAITING_ADMIN", actor=owner, now=now)
        else:
            _start_clock(ticket, policy, now)
            _set_state(
                ticket,
                "AWAITING_ADMIN",
                "STATE_CHANGED",
                actor=owner,
                reason="HUMAN_REQUESTED",
                now=now,
            )
            _event(ticket, "HUMAN_REQUESTED", to_state="AWAITING_ADMIN", actor=owner, now=now)
    elif to_state == "RESOLVED":
        if ticket.state == "CLOSED":
            raise IdentityError("TICKET_CLOSED", 409, "This ticket is already closed")
        if ticket.state == "RESOLVED":
            # Confirming an administrator resolution does not shorten the quiet period.
            _event(
                ticket,
                "MESSAGE_ADDED",
                to_state=ticket.state,
                actor=owner,
                reason="STUDENT_CONFIRMED",
                now=now,
            )
        else:
            # A resolution stays RESOLVED until the configured quiet period expires
            # without an objection; only the bounded worker closes it.
            ticket.resolved_at = now
            ticket.rating_window_until = now + timedelta(days=policy.rating_edit_days)
            _set_state(
                ticket,
                "RESOLVED",
                "STATE_CHANGED",
                actor=owner,
                reason="STUDENT_CONFIRMED",
                now=now,
            )
    else:
        raise IdentityError("INVALID_TRANSITION", 400, "That transition is not available")
    ticket.row_version += 1
    ticket.updated_at = now
    audit(
        owner,
        "support_ticket_transition",
        resource=ticket.pk,
        reason=reason[:64],
        correlation=correlation,
    )
    _persist(ticket)
    return ticket_data(ticket)


def rating_state(ticket: Ticket) -> dict[str, Any]:
    """Rating eligibility is separate from whether an existing rating can be edited."""
    now = timezone.now()
    existing = TicketRating.objects.filter(ticket=ticket).first()
    window_open = bool(
        ticket.state in ("RESOLVED", "CLOSED")
        and ticket.rating_window_until is not None
        and now <= ticket.rating_window_until
    )
    editable = bool(existing and now <= existing.editable_until)
    return {
        "available": window_open,
        "editable": editable,
        "rating": existing,
    }


@transaction.atomic
def rate_ticket(
    user: Account,
    proof: IdentitySession,
    ticket_id: Any,
    value: int,
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id, lock=True)
    if ticket.row_version != expected:
        raise IdentityError("STALE_REVISION", 412, "Reload the current ticket")
    if type(value) is not int or not 1 <= value <= 5:
        raise IdentityError("INVALID_RATING", 400, "A rating between 1 and 5 is required")
    state = rating_state(ticket)
    now = timezone.now()
    if state["rating"] is not None:
        # An existing rating keeps its own edit deadline.
        if now > state["rating"].editable_until:
            raise IdentityError("RATING_WINDOW_CLOSED", 409, "The rating window has closed")
        rating = state["rating"]
        rating.value = value
        rating.updated_at = now
        rating.save(update_fields=["value", "updated_at"])
    else:
        if ticket.state not in ("RESOLVED", "CLOSED"):
            raise IdentityError("RATING_UNAVAILABLE", 409, "This ticket cannot be rated")
        if ticket.rating_window_until is None or now > ticket.rating_window_until:
            raise IdentityError("RATING_WINDOW_CLOSED", 409, "The rating window has closed")
        rating = TicketRating.objects.create(
            ticket=ticket,
            value=value,
            created_at=now,
            updated_at=now,
            editable_until=ticket.rating_window_until,
        )
    ticket.row_version += 1
    ticket.updated_at = now
    _event(ticket, "RATED", to_state=ticket.state, actor=owner, reason="STUDENT_RATED", now=now)
    audit(owner, "support_ticket_rated", resource=ticket.pk, correlation=correlation)
    _persist(ticket)
    return rating_data(rating)


def read_rating(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id)
    rating = TicketRating.objects.filter(ticket=ticket).first()
    audit(owner, "support_rating_read", resource=ticket.pk, correlation=correlation)
    if rating is None:
        raise IdentityError("RATING_UNAVAILABLE", 404, "No rating exists")
    return rating_data(rating)


# --- administrator surface -------------------------------------------------


def require_support_admin(actor: Account, proof: IdentitySession, *scopes: str) -> Account:
    """Administrator proof with at least one of the given support scopes."""
    for scope in scopes:
        try:
            require_admin(actor, proof, scope)
            return actor
        except IdentityError:
            continue
    raise IdentityError("ADMIN_MFA_REQUIRED", 403, "Support administration is not permitted")


@transaction.atomic
def publish_policy(
    actor: Account,
    proof: IdentitySession,
    data: dict[str, Any],
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, POLICY_SCOPE)
    head = (
        SupportCalendarHead.objects.select_for_update(of=("self",))
        .select_related("policy")
        .get(pk=1)
    )
    if head.policy.version != expected:
        raise IdentityError("STALE_POLICY", 412, "Review the current support policy")
    working = sorted({int(day) for day in data["working_weekdays"]})
    if not working or any(day < 0 or day > 6 for day in working):
        raise IdentityError("INVALID_POLICY", 400, "A working calendar is required")
    try:
        opens = workcal.parse_clock(str(data["opens_local"]))
        closes = workcal.parse_clock(str(data["closes_local"]))
    except workcal.CalendarError as exc:
        raise IdentityError(
            "INVALID_POLICY", 400, "Working hours must be valid clock times"
        ) from exc
    if closes <= opens:
        raise IdentityError("INVALID_POLICY", 400, "Working hours must close after they open")
    holidays = [str(day) for day in data["holidays"]]
    for day in holidays:
        try:
            workcal.parse_day(day)
        except workcal.CalendarError as exc:
            raise IdentityError("INVALID_POLICY", 400, "A holiday must be a real date") from exc
    targets = {str(key): int(value) for key, value in dict(data["targets"]).items()}
    if set(targets) != set(PRIORITIES) or any(value < 1 for value in targets.values()):
        raise IdentityError("INVALID_POLICY", 400, "A target for every priority is required")
    ai_daily = int(data["ai_daily_messages"])
    if not 1 <= ai_daily <= MAX_AI_DAILY_MESSAGES:
        raise IdentityError(
            "INVALID_POLICY", 400, "The AI support allowance cannot exceed five messages"
        )
    policy = SupportCalendar.objects.create(
        version=head.policy.version + 1,
        timezone=str(data["timezone"]),
        working_weekdays=working,
        opens_local=opens.strftime("%H:%M"),
        closes_local=closes.strftime("%H:%M"),
        holidays=holidays,
        targets=targets,
        ai_daily_messages=ai_daily,
        closure_days=int(data["closure_days"]),
        reopen_days=int(data["reopen_days"]),
        rating_edit_days=int(data["rating_edit_days"]),
        warning_percent=int(data["warning_percent"]),
        effective_at=data["effective_at"],
        reason=str(data["reason"]),
        actor=actor,
        session_proof=proof,
    )
    head.policy = policy
    head.save(update_fields=["policy"])
    audit(actor, "support_policy_published", resource=policy.pk, correlation=correlation)
    return policy_data(policy)


def policy_data(policy: SupportCalendar) -> dict[str, Any]:
    return {
        "id": str(policy.pk),
        "version": policy.version,
        "timezone": policy.timezone,
        "working_weekdays": list(policy.working_weekdays),
        "opens_local": policy.opens_local,
        "closes_local": policy.closes_local,
        "holidays": list(policy.holidays),
        "targets": dict(policy.targets),
        "ai_daily_messages": policy.ai_daily_messages,
        "closure_days": policy.closure_days,
        "reopen_days": policy.reopen_days,
        "rating_edit_days": policy.rating_edit_days,
        "warning_percent": policy.warning_percent,
        "effective_at": policy.effective_at.isoformat().replace("+00:00", "Z"),
    }


def read_policy(actor: Account, proof: IdentitySession, correlation: Any) -> dict[str, Any]:
    require_support_admin(actor, proof, QUEUE_SCOPE, POLICY_SCOPE)
    policy = head_policy()
    in_force = policy_at(timezone.now())
    audit(actor, "support_policy_read", resource=policy.pk, correlation=correlation)
    value = policy_data(policy)
    value["in_force_version"] = in_force.version
    value["in_force_at"] = in_force.effective_at.isoformat().replace("+00:00", "Z")
    return value


@transaction.atomic
def queue(
    actor: Account,
    proof: IdentitySession,
    page: int,
    page_size: int,
    state: str | None,
    priority: str | None,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, QUEUE_SCOPE)
    query = Ticket.objects.select_related("sla_policy").order_by("state", "-created_at", "pk")
    if state:
        if state not in STATES:
            raise IdentityError("INVALID_FILTER", 400, "Unknown ticket state")
        query = query.filter(state=state)
    if priority:
        if priority not in PRIORITIES:
            raise IdentityError("INVALID_FILTER", 400, "Unknown ticket priority")
        query = query.filter(priority=priority)
    total = query.count()
    rows = query[(page - 1) * page_size : page * page_size]
    audit(actor, "support_queue_read", correlation=correlation)
    return {
        "items": [queue_data(row, actor) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def queue_data(ticket: Ticket, actor: Account) -> dict[str, Any]:
    """Queue metadata only: no student identity, subject or message content."""
    return {
        "id": str(ticket.pk),
        "state": ticket.state,
        "category": ticket.category,
        "priority": ticket.priority,
        "assigned_to_me": ticket.assigned_admin_id == actor.pk,
        "assigned": ticket.assigned_admin_id is not None,
        "created_at": ticket.created_at.isoformat().replace("+00:00", "Z"),
        "due_at": ticket.sla_due_at.isoformat().replace("+00:00", "Z")
        if ticket.sla_due_at
        else None,
        "human_requested_at": (
            ticket.human_requested_at.isoformat().replace("+00:00", "Z")
            if ticket.human_requested_at
            else None
        ),
        "first_human_response_at": (
            ticket.first_human_response_at.isoformat().replace("+00:00", "Z")
            if ticket.first_human_response_at
            else None
        ),
        "warning": ticket.sla_warning_at is not None,
        "breached": ticket.sla_breached_at is not None,
        "row_version": ticket.row_version,
    }


@transaction.atomic
def assign_ticket(
    actor: Account,
    proof: IdentitySession,
    ticket_id: Any,
    agent_id: Any,
    reason: str,
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, ASSIGNMENT_SCOPE)
    ticket = Ticket.objects.select_for_update(of=("self",)).filter(pk=ticket_id).first()
    if ticket is None:
        raise IdentityError("TICKET_NOT_FOUND", 404, "Ticket not found")
    if ticket.row_version != expected:
        raise IdentityError("STALE_REVISION", 412, "Reload the current ticket")
    agent = Account.objects.filter(pk=agent_id, role=Account.Role.ADMIN).first()
    if agent is None or SUPPORT_SCOPE not in agent.admin_scopes:
        raise IdentityError("AGENT_NOT_ELIGIBLE", 400, "That agent cannot take support tickets")
    now = timezone.now()
    policy = policy_at(now)
    ticket.assigned_admin = agent
    ticket.row_version += 1
    ticket.updated_at = now
    TicketAccess.objects.filter(pk=ticket.pk).update(assigned_admin=agent)
    _start_clock(ticket, policy, now)
    _event(
        ticket, "HUMAN_ASSIGNED", to_state=ticket.state, actor=actor, reason=reason[:64], now=now
    )
    audit(actor, "support_ticket_assigned", resource=ticket.pk, correlation=correlation)
    _persist(ticket)
    return queue_data(ticket, actor)


def admin_messages(
    actor: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    require_admin(actor, proof, SUPPORT_SCOPE)
    _assigned_ticket(actor, ticket_id)
    with transaction.atomic():
        ticket = _assigned_ticket(actor, ticket_id, audit_denial=False)
        rows = list(ticket.messages.order_by("sequence"))
    audit(actor, "support_messages_read", resource=ticket.pk, correlation=correlation)
    return {"items": [message_data(row) for row in rows]}


def admin_post_message(
    actor: Account,
    proof: IdentitySession,
    ticket_id: Any,
    body: str,
    request_human: bool,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, SUPPORT_SCOPE)
    _assigned_ticket(actor, ticket_id)
    with transaction.atomic():
        ticket = _assigned_ticket(actor, ticket_id, lock=True, audit_denial=False)
        text = str(body).strip()
        if not text or len(text) > MAX_BODY:
            raise IdentityError("INVALID_MESSAGE", 400, "A message body is required")
        if ticket.state in ("RESOLVED", "CLOSED"):
            raise IdentityError("TICKET_CLOSED", 409, "This ticket is no longer open")
        now = timezone.now()
        policy = policy_at(now)
        # An acknowledgement is not the substantive human reply that satisfies the
        # measured obligation. The classification is server-side.
        substantive = not is_acknowledgement(text)
        _message(ticket, "ADMIN", text, actor=actor, substantive=substantive, now=now)
        ticket.row_version += 1
        ticket.updated_at = now
        _start_clock(ticket, policy, now)
        if substantive:
            _finish_clock(ticket, now)
            _event(
                ticket,
                "FIRST_HUMAN_RESPONSE",
                to_state=ticket.state,
                actor=actor,
                reason="SUBSTANTIVE_REPLY",
                now=now,
            )
        else:
            _event(
                ticket,
                "MESSAGE_ADDED",
                to_state=ticket.state,
                actor=actor,
                reason="AGENT_ACKNOWLEDGED",
                now=now,
            )
        if ticket.state == "AWAITING_STUDENT":
            _set_state(
                ticket,
                "AWAITING_ADMIN",
                "STATE_CHANGED",
                actor=actor,
                reason="AGENT_REPLIED",
                now=now,
            )
        else:
            _event(
                ticket,
                "STATE_CHANGED",
                to_state=ticket.state,
                actor=actor,
                reason="AGENT_REPLIED",
                now=now,
            )
        audit(actor, "support_message_posted", resource=ticket.pk, correlation=correlation)
        _persist(ticket)
        return ticket_data(ticket)


def admin_transition(
    actor: Account,
    proof: IdentitySession,
    ticket_id: Any,
    to_state: str,
    reason: str,
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, SUPPORT_SCOPE)
    _assigned_ticket(actor, ticket_id)
    with transaction.atomic():
        ticket = _assigned_ticket(actor, ticket_id, lock=True, audit_denial=False)
        if ticket.row_version != expected:
            raise IdentityError("STALE_REVISION", 412, "Reload the current ticket")
        now = timezone.now()
        policy = policy_at(now)
        allowed = {
            "AWAITING_STUDENT": ("AWAITING_ADMIN",),
            "AWAITING_ADMIN": ("AWAITING_STUDENT", "RESOLVED"),
            "AI_HANDLING": ("AWAITING_ADMIN",),
            "NEW": ("AWAITING_ADMIN",),
            "RESOLVED": ("CLOSED",),
        }
        if to_state not in allowed.get(ticket.state, ()):
            raise IdentityError("INVALID_TRANSITION", 409, "That transition is not available")
        if to_state == "RESOLVED":
            ticket.resolved_at = now
            ticket.rating_window_until = now + timedelta(days=policy.rating_edit_days)
        if to_state == "CLOSED":
            ticket.closed_at = now
            ticket.reopen_until = now + timedelta(days=policy.reopen_days)
        _set_state(ticket, to_state, "STATE_CHANGED", actor=actor, reason=reason[:64], now=now)
        ticket.row_version += 1
        ticket.updated_at = now
        audit(
            actor,
            "support_ticket_transition",
            resource=ticket.pk,
            reason=reason[:64],
            correlation=correlation,
        )
        _persist(ticket)
        return ticket_data(ticket)


def classify_ticket(
    actor: Account,
    proof: IdentitySession,
    ticket_id: Any,
    category: str,
    priority: str,
    reason: str,
    expected: int,
    correlation: Any,
) -> dict[str, Any]:
    require_admin(actor, proof, SUPPORT_SCOPE)
    _assigned_ticket(actor, ticket_id)
    with transaction.atomic():
        ticket = _assigned_ticket(actor, ticket_id, lock=True, audit_denial=False)
        if ticket.row_version != expected:
            raise IdentityError("STALE_REVISION", 412, "Reload the current ticket")
        if priority not in PRIORITIES:
            raise IdentityError("INVALID_CLASSIFICATION", 400, "Unknown priority")
        name = str(category).strip()
        if not name or len(name) > MAX_CATEGORY:
            raise IdentityError("INVALID_CLASSIFICATION", 400, "A category is required")
        now = timezone.now()
        ticket.category = name
        ticket.priority = priority
        ticket.row_version += 1
        ticket.updated_at = now
        _event(
            ticket,
            "CLASSIFIED",
            to_state=ticket.state,
            actor=actor,
            reason=reason[:64],
            now=now,
        )
        audit(actor, "support_ticket_classified", resource=ticket.pk, correlation=correlation)
        _persist(ticket)
        return ticket_data(ticket)


def sla_view(
    actor: Account, proof: IdentitySession, ticket_id: Any, *, admin: bool, correlation: Any
) -> dict[str, Any]:
    if admin:
        require_admin(actor, proof, SUPPORT_SCOPE)
        _assigned_ticket(actor, ticket_id)
        ticket = _assigned_ticket(actor, ticket_id, audit_denial=False)
    else:
        owner = student(actor, proof)
        ticket = _owned_ticket(owner, ticket_id)
    audit(actor, "support_sla_read", resource=ticket.pk, correlation=correlation)
    return sla_data(ticket)


@transaction.atomic
def attachments(
    user: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    owner = student(user, proof)
    ticket = _owned_ticket(owner, ticket_id)
    rows = TicketShare.objects.filter(ticket_id=ticket.pk, owner=owner).order_by("created_at")
    audit(owner, "support_attachments_read", resource=ticket.pk, correlation=correlation)
    return {
        "items": [
            {
                "id": str(row.pk),
                "asset_id": str(row.asset_id),
                "state": "REVOKED" if row.revoked_at else "SHARED",
                "version": row.version,
                "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
            }
            for row in rows
        ]
    }


def admin_attachments(
    actor: Account, proof: IdentitySession, ticket_id: Any, correlation: Any
) -> dict[str, Any]:
    """The explicit attachments of an assigned ticket. Never the wider library."""
    require_admin(actor, proof, SUPPORT_SCOPE)
    _assigned_ticket(actor, ticket_id)
    rows = TicketShare.objects.filter(ticket_id=ticket_id).order_by("created_at")
    audit(actor, "support_attachments_read", resource=ticket_id, correlation=correlation)
    return {
        "items": [
            {
                "id": str(row.pk),
                "asset_id": str(row.asset_id),
                "state": "REVOKED" if row.revoked_at else "SHARED",
                "version": row.version,
                "created_at": row.created_at.isoformat().replace("+00:00", "Z"),
            }
            for row in rows
        ]
    }


def attachment_metadata(
    actor: Account, proof: IdentitySession, ticket_id: Any, share_id: Any
) -> dict[str, Any]:
    """Assigned-agent metadata read of one explicit share. The privacy layer audits it."""
    require_admin(actor, proof, SUPPORT_SCOPE)
    privacy.ticket_asset(actor, proof, ticket_id, share_id)
    share = TicketShare.objects.filter(pk=share_id, ticket_id=ticket_id).first()
    if share is None:
        raise IdentityError("ATTACHMENT_NOT_FOUND", 404, "Attachment not found")
    return {
        "id": str(share.pk),
        "asset_id": str(share.asset_id),
        "state": "REVOKED" if share.revoked_at else "SHARED",
        "version": share.version,
        "created_at": share.created_at.isoformat().replace("+00:00", "Z"),
    }


def metrics(actor: Account, proof: IdentitySession, correlation: Any) -> dict[str, Any]:
    require_admin(actor, proof, QUEUE_SCOPE)
    rows = Ticket.objects.all()
    by_state: dict[str, int] = {state: 0 for state in STATES}
    for state in rows.values_list("state", flat=True):
        by_state[state] = by_state.get(state, 0) + 1
    rated = list(TicketRating.objects.values_list("value", flat=True))
    cycles = list(SlaCycle.objects.select_related("ticket").all())
    elapsed: list[int] = []
    breaches = 0
    for cycle in cycles:
        if cycle.breached_at is not None:
            breaches += 1
        if cycle.responded_at is not None:
            try:
                calendar = _calendar(cycle.ticket.sla_policy)
            except (IdentityError, AttributeError):
                continue
            elapsed.append(workcal.business_minutes(calendar, cycle.started_at, cycle.responded_at))
    audit(actor, "support_metrics_read", correlation=correlation)
    return {
        "tickets": {
            "total": rows.count(),
            "by_state": by_state,
            "first_human_responses": sum(1 for cycle in cycles if cycle.responded_at is not None),
            "measured_cycles": len(cycles),
            "sla_breaches": breaches,
            "sla_warnings": rows.filter(sla_warning_at__isnull=False).count(),
            "resolved": rows.filter(resolved_at__isnull=False).count(),
            "ratings": len(rated),
            "average_rating": round(sum(rated) / len(rated), 2) if rated else None,
            "average_first_response_business_minutes": (
                round(sum(elapsed) / len(elapsed), 2) if elapsed else None
            ),
        }
    }


def _sweep_candidates() -> tuple[list[Any], list[Any], list[Any]]:
    measuring = Ticket.objects.filter(
        sla_due_at__isnull=False,
        first_human_response_at__isnull=True,
        state__in=("NEW", "AI_HANDLING", "AWAITING_ADMIN", "AWAITING_STUDENT"),
    )
    warnings = list(measuring.filter(sla_warning_at__isnull=True).order_by("sla_due_at")[:200])
    breaches = list(measuring.filter(sla_breached_at__isnull=True).order_by("sla_due_at")[:200])
    # Only tickets whose own quiet period has elapsed are due, so a long closure
    # policy on an old ticket cannot starve a newer ticket that is due.
    closure = SupportCalendar.objects.filter(pk=OuterRef("sla_policy_id")).values("closure_days")[
        :1
    ]
    closing = list(
        Ticket.objects.filter(state="RESOLVED", closed_at__isnull=True, resolved_at__isnull=False)
        .annotate(closure_days=Subquery(closure, output_field=IntegerField()))
        .filter(resolved_at__lte=timezone.now() - F("closure_days") * timedelta(days=1))
        .order_by("resolved_at")[:200]
    )
    return warnings, breaches, closing


@transaction.atomic
def _mark_warning(ticket_id: Any, now: Any) -> bool:
    ticket = Ticket.objects.select_for_update(of=("self",)).filter(pk=ticket_id).first()
    if ticket is None or ticket.sla_warning_at is not None or ticket.first_human_response_at:
        return False
    if (
        ticket.sla_policy is None
        or ticket.human_requested_at is None
        or ticket.sla_target_minutes is None
    ):
        return False
    calendar = _calendar(ticket.sla_policy)
    elapsed = workcal.business_minutes(calendar, ticket.human_requested_at, now)
    threshold = ticket.sla_target_minutes * ticket.sla_policy.warning_percent // 100
    if elapsed < threshold:
        return False
    ticket.sla_warning_at = now
    ticket.updated_at = now
    _event(
        ticket,
        "SLA_WARNING",
        to_state=ticket.state,
        reason=f"ELAPSED_{elapsed}_MINUTES",
        now=now,
    )
    cycle = _cycle(ticket)
    if cycle is not None and cycle.warning_at is None:
        cycle.warning_at = now
        cycle.save(update_fields=["warning_at"])
    _persist(ticket)
    audit(None, "support_sla_warning", resource=ticket.pk, reason="APPROACHING_TARGET")
    return True


@transaction.atomic
def _mark_breach(ticket_id: Any, now: Any) -> bool:
    ticket = Ticket.objects.select_for_update(of=("self",)).filter(pk=ticket_id).first()
    if ticket is None or ticket.sla_breached_at is not None or ticket.first_human_response_at:
        return False
    if ticket.sla_due_at is None or now <= ticket.sla_due_at:
        return False
    ticket.sla_breached_at = now
    ticket.updated_at = now
    _event(
        ticket,
        "SLA_BREACH",
        to_state=ticket.state,
        reason="FIRST_HUMAN_RESPONSE_OVERDUE",
        now=now,
    )
    cycle = _cycle(ticket)
    if cycle is not None and cycle.breached_at is None:
        cycle.breached_at = now
        cycle.save(update_fields=["breached_at"])
    _persist(ticket)
    audit(None, "support_sla_breach", resource=ticket.pk, reason="OVERDUE")
    return True


@transaction.atomic
def _auto_close(ticket_id: Any, now: Any) -> bool:
    ticket = Ticket.objects.select_for_update(of=("self",)).filter(pk=ticket_id).first()
    if ticket is None or ticket.closed_at is not None or ticket.state != "RESOLVED":
        return False
    policy = ticket.sla_policy or policy_at(now)
    if ticket.resolved_at is None or now < ticket.resolved_at + timedelta(days=policy.closure_days):
        return False
    ticket.closed_at = now
    ticket.reopen_until = now + timedelta(days=policy.reopen_days)
    ticket.updated_at = now
    _set_state(ticket, "CLOSED", "AUTO_CLOSED", actor=None, reason="QUIET_PERIOD_ELAPSED", now=now)
    _persist(ticket)
    audit(None, "support_ticket_auto_closed", resource=ticket.pk, reason="QUIET_PERIOD_ELAPSED")
    return True


def sweep(limit: int = 200) -> dict[str, int]:
    """Bounded idempotent sweep. A crash never double-applies or skips a ticket."""
    now = timezone.now()
    warnings, breaches, closing = _sweep_candidates()
    counted = {"warnings": 0, "breaches": 0, "closed": 0}
    for ticket in warnings[:limit]:
        counted["warnings"] += int(_mark_warning(ticket.pk, now))
    for ticket in breaches[:limit]:
        counted["breaches"] += int(_mark_breach(ticket.pk, now))
    for ticket in closing[:limit]:
        counted["closed"] += int(_auto_close(ticket.pk, now))
    return counted


# --- projections ------------------------------------------------------------


def message_data(message: TicketMessage) -> dict[str, Any]:
    return {
        "sequence": message.sequence,
        "author_kind": message.author_kind,
        "body": message.body,
        "substantive": message.substantive,
        "created_at": message.created_at.isoformat().replace("+00:00", "Z"),
    }


def event_data(event: TicketEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "kind": event.kind,
        "from_state": event.from_state,
        "to_state": event.to_state,
        "reason": event.reason,
        "observed_at": event.observed_at.isoformat().replace("+00:00", "Z"),
    }


def rating_data(rating: TicketRating) -> dict[str, Any]:
    return {
        "ticket_id": str(rating.ticket_id),
        "value": rating.value,
        "created_at": rating.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": rating.updated_at.isoformat().replace("+00:00", "Z"),
        "editable_until": rating.editable_until.isoformat().replace("+00:00", "Z"),
    }


def cycle_data(cycle: SlaCycle) -> dict[str, Any]:
    return {
        "cycle_no": cycle.cycle_no,
        "started_at": cycle.started_at.isoformat().replace("+00:00", "Z"),
        "responded_at": (
            cycle.responded_at.isoformat().replace("+00:00", "Z") if cycle.responded_at else None
        ),
        "target_business_minutes": cycle.target_minutes,
        "computed_due_at": cycle.due_at.isoformat().replace("+00:00", "Z"),
        "warning": cycle.warning_at is not None,
        "breached": cycle.breached_at is not None,
        "state": cycle.state,
    }


def sla_data(ticket: Ticket) -> dict[str, Any]:
    elapsed = None
    if ticket.human_requested_at is not None and ticket.sla_policy is not None:
        try:
            calendar = _calendar(ticket.sla_policy)
        except IdentityError:
            calendar = None
        if calendar is not None:
            end = ticket.first_human_response_at or timezone.now()
            elapsed = workcal.business_minutes(calendar, ticket.human_requested_at, end)
    return {
        "cycle_no": ticket.sla_cycle_no,
        "human_requested_at": (
            ticket.human_requested_at.isoformat().replace("+00:00", "Z")
            if ticket.human_requested_at
            else None
        ),
        "computed_due_at": (
            ticket.sla_due_at.isoformat().replace("+00:00", "Z") if ticket.sla_due_at else None
        ),
        "calendar_policy_id": str(ticket.sla_policy_id) if ticket.sla_policy_id else None,
        "target_business_minutes": ticket.sla_target_minutes,
        "first_human_response_at": (
            ticket.first_human_response_at.isoformat().replace("+00:00", "Z")
            if ticket.first_human_response_at
            else None
        ),
        "elapsed_business_minutes": elapsed,
        "warning": ticket.sla_warning_at is not None,
        "breached": ticket.sla_breached_at is not None,
        "met": ticket.first_human_response_at is not None,
        "cycles": [cycle_data(cycle) for cycle in ticket.sla_cycles.order_by("cycle_no")],
    }


def ticket_data(ticket: Ticket) -> dict[str, Any]:
    state = rating_state(ticket)
    return {
        "id": str(ticket.pk),
        "state": ticket.state,
        "category": ticket.category,
        "subject": ticket.subject,
        "priority": ticket.priority,
        "head_sequence": ticket.head_sequence,
        "row_version": ticket.row_version,
        "created_at": ticket.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": ticket.updated_at.isoformat().replace("+00:00", "Z"),
        "assigned": ticket.assigned_admin is not None,
        "suggested_category": ticket.suggested_category,
        "suggested_priority": ticket.suggested_priority,
        "triage_confidence": ticket.triage_confidence,
        "triage_reason": ticket.triage_reason,
        "resolved_at": (
            ticket.resolved_at.isoformat().replace("+00:00", "Z") if ticket.resolved_at else None
        ),
        "closed_at": ticket.closed_at.isoformat().replace("+00:00", "Z")
        if ticket.closed_at
        else None,
        "reopen_until": (
            ticket.reopen_until.isoformat().replace("+00:00", "Z") if ticket.reopen_until else None
        ),
        "rating_window_until": (
            ticket.rating_window_until.isoformat().replace("+00:00", "Z")
            if ticket.rating_window_until
            else None
        ),
        "rating": state["rating"].value if state["rating"] else None,
        "rating_available": state["available"],
        "rating_editable": state["editable"],
        "sla": sla_data(ticket),
    }
