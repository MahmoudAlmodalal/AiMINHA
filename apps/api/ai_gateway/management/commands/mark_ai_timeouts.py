from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_gateway.models import Attempt
from ai_gateway.services import expire_attempts


class Command(BaseCommand):
    help = (
        "Inspect expired AI dispatch intents; --apply retains uncertain capacity and credit holds."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        expired = Attempt.objects.filter(
            state="DISPATCH_INTENT", lease_until__lte=timezone.now()
        ).count()
        marked = expire_attempts() if options["apply"] else 0
        self.stdout.write(
            f"Expired AI intents: {expired}; marked uncertain: {marked}. No dispatch or refund."
        )
