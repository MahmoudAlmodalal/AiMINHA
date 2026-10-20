"""Support triage over an explicitly allowed context.

The context builder cannot reach attachments, other tickets, profile data, account
state or credit balances: it accepts only the current ticket's subject, category and
messages. The engine is a deterministic server-local classifier. It never calls a
provider, never persists a prompt and never performs a financial or account action.
"""

from dataclasses import dataclass
from typing import Any

CATEGORIES = [
    "ACCOUNT",
    "TECHNICAL",
    "DOCUMENTS",
    "SCHOLARSHIP",
    "ELIGIBILITY",
    "PAYMENTS",
    "OTHER",
]
HANDOFF_REASONS = [
    "STUDENT_REQUESTED_HUMAN",
    "FINANCIAL_TOPIC",
    "SECURITY_TOPIC",
    "CRITICAL_DEADLINE",
    "LOW_CONFIDENCE",
    "REPEATED_FAILURE",
    "DAILY_ALLOWANCE_EXHAUSTED",
    "GLOBAL_BUDGET_EXHAUSTED",
]
CONFIDENCE_THRESHOLD = 6000  # basis points
MAX_CONFIDENCE = 9500

_TERMS: dict[str, tuple[str, ...]] = {
    "PAYMENTS": (
        "payment",
        "pay ",
        "credits",
        "credit balance",
        "transfer",
        "refund",
        "receipt",
        "invoice",
        "money",
        "دفع",
        "مدفوع",
        "رصيد",
        "رصيدي",
        "تحويل",
        "استرجاع",
        "إيصال",
        "فاتورة",
        "مبلغ",
    ),
    "SECURITY": (
        "password",
        "otp",
        "two-factor",
        "2fa",
        "hacked",
        "stolen",
        "phishing",
        "compromised",
        "someone signed in",
        "unauthorized",
        "كلمة سر",
        "كلمة المرور",
        "رمز التحقق",
        "تم اختراق",
        "اختراق",
        "تصيد",
        "دخول غير مصرح",
    ),
    "DOCUMENTS": (
        "cv",
        "resume",
        "transcript",
        "document",
        "letter",
        "essay",
        "statement",
        "upload",
        "file",
        "سيرة ذاتية",
        "وثيقة",
        "مستند",
        "كشف",
        "رسالة",
        "مقال",
        "رفع",
        "ملف",
    ),
    "ELIGIBILITY": (
        "eligible",
        "eligibility",
        "gpa",
        "criteria",
        "requirement",
        "qualify",
        "الأهلية",
        "مؤهل",
        "معدل",
        "شروط",
        "متطلبات",
    ),
    "SCHOLARSHIP": (
        "scholarship",
        "application",
        "apply",
        "portal",
        "deadline",
        "closing date",
        "منحة",
        "طلب",
        "تقديم",
        "بوابة",
        "موعد",
        "آخر يوم",
        "استحقاق",
    ),
    "TECHNICAL": (
        "error",
        "bug",
        "upload failed",
        "not working",
        "broken",
        "cannot",
        "can't",
        "login fails",
        "خطأ",
        "عطل",
        "لا يعمل",
        "فشل",
        "رفع",
    ),
    "ACCOUNT": (
        "account",
        "sign in",
        "login",
        "email",
        "verification",
        "delete my account",
        "حساب",
        "تسجيل الدخول",
        "تأكيد",
        "حذف حسابي",
    ),
}
_DEADLINE_TERMS = (
    "deadline is today",
    "due today",
    "closes today",
    "last day",
    "closing tonight",
    "urgent",
    "asap",
    "اليوم",
    "اخر يوم",
    "آخر يوم",
    "موعد اليوم",
    "عاجل",
    "بشكل عاجل",
)


class TriageFailure(Exception):
    """The engine could not classify the case; the ticket falls back to a human."""


@dataclass(frozen=True)
class TriageContext:
    """The complete allowed context. Nothing outside this shape may be triaged."""

    subject: str
    category: str
    messages: tuple[str, ...]
    locale: str


@dataclass(frozen=True)
class TriageOutcome:
    category: str
    priority: str
    confidence: int
    handoff: bool
    reasons: tuple[str, ...]
    body: str


def build_context(ticket: Any, messages: list[Any], locale: str) -> TriageContext:
    """Assemble the allowed context. Attachment or account data is never an input."""
    bodies = tuple(str(message.body) for message in messages if message.author_kind != "ADMIN")
    return TriageContext(
        subject=str(ticket.subject),
        category=str(ticket.category),
        messages=bodies,
        locale=locale,
    )


def _haystack(context: TriageContext) -> str:
    return " ".join((context.subject, context.category, *context.messages)).lower()


def classify(context: TriageContext) -> TriageOutcome:
    """Suggest a category and priority, and decide whether a human is required."""
    if not context.messages and len(context.subject.strip()) < 12:
        raise TriageFailure("The allowed context is too small to classify")
    text = _haystack(context)
    if not text.strip():
        raise TriageFailure("The allowed context is empty")
    reasons: list[str] = []
    matches: list[tuple[str, int]] = []
    for category, terms in _TERMS.items():
        hits = sum(1 for term in terms if term in text)
        if hits:
            matches.append((category, hits))
    matches.sort(key=lambda item: (-item[1], item[0]))
    category = matches[0][0] if matches else "OTHER"
    confidence = 3500
    if matches:
        confidence = min(MAX_CONFIDENCE, 3500 + 2000 * matches[0][1])
    priority = "NORMAL"
    # A sensitive subject is decided on its own terms, never by the category ranking.
    financial = any(term in text for term in _TERMS["PAYMENTS"])
    security = any(term in text for term in _TERMS["SECURITY"])
    deadline = any(term in text for term in _DEADLINE_TERMS)
    if financial:
        reasons.append("FINANCIAL_TOPIC")
    if security:
        reasons.append("SECURITY_TOPIC")
    if deadline:
        reasons.append("CRITICAL_DEADLINE")
    if financial or security:
        priority = "HIGH"
    if deadline:
        priority = "CRITICAL"
    if category == "OTHER" or confidence < CONFIDENCE_THRESHOLD:
        reasons.append("LOW_CONFIDENCE")
    handoff = bool(reasons)
    if handoff and priority == "NORMAL" and "LOW_CONFIDENCE" in reasons:
        priority = "LOW"
    return TriageOutcome(
        category=category,
        priority=priority,
        confidence=confidence,
        handoff=handoff,
        reasons=tuple(dict.fromkeys(reasons)),
        body=_reply(context, category, priority, handoff),
    )


def _reply(context: TriageContext, category: str, priority: str, handoff: bool) -> str:
    if context.locale == "ar":
        if handoff:
            return (
                f"تم استلام طلبك وتصنيفه مبدئيًا كفئة «{category}» بأولوية «{priority}». "
                "أُحيل الطلب إلى دعم بشري لأن هذا الموضوع يحتاج مراجعة إنسان."
            )
        return (
            f"تم استلام طلبك وتصنيفه مبدئيًا كفئة «{category}» بأولوية «{priority}». "
            "أستطيع المساعدة في الخطوات العامة، وسيرد عليك دعم بشري إن احتجت."
        )
    if handoff:
        return (
            f"Your request was received and provisionally classified as {category} with "
            f"{priority} priority. It is handed to a human support agent because this "
            "topic needs one."
        )
    return (
        f"Your request was received and provisionally classified as {category} with "
        f"{priority} priority. I can help with general steps; a human support agent "
        "follows up if you need one."
    )
