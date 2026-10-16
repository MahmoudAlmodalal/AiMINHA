from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from privacy.models import DeletionRequest
from privacy.services import queue_expired_deletion


class Command(BaseCommand):
    help = "Plan due account file erasure; no storage deletion is implemented or implied."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--enqueue", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        if not 1 <= options["limit"] <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        accounts = list(
            DeletionRequest.objects.filter(state="PENDING", restore_until__lte=timezone.now())
            .order_by("restore_until")
            .values_list("account_id", flat=True)[: options["limit"]]
        )
        count = (
            sum(queue_expired_deletion(account) for account in accounts)
            if options["enqueue"]
            else 0
        )
        self.stdout.write(
            f"Due accounts: {len(accounts)}; queued tasks: {count}; no objects erased."
        )
