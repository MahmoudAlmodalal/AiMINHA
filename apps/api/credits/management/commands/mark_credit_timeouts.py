"""Idempotent reconciliation marker; does not dispatch, retry, debit or refund."""

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from credits.models import Operation
from credits.services import mark_expired


class Command(BaseCommand):
    help = "Inspect expired reservations; --apply marks uncertainty without releasing funds."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--limit", type=int, choices=range(1, 1001), default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        now = timezone.now()
        ids = list(
            Operation.objects.filter(
                state__in=["RESERVED", "RUNNING"],
                reserve_until__lte=now,
            )
            .order_by("reserve_until", "pk")
            .values_list("pk", flat=True)[: options["limit"]]
        )
        if options["apply"]:
            for operation_id in ids:
                mark_expired(operation_id, now)
        overdue = Operation.objects.filter(state="RECONCILING", resolution_due_at__lte=now).count()
        self.stdout.write(
            f"Expired inspected: {len(ids)}; apply: {bool(options['apply'])}; "
            f"reconciliation target overdue: {overdue}. No balance released."
        )
