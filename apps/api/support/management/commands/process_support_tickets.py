import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from support.services import sweep


class Command(BaseCommand):
    help = (
        "Bounded idempotent sweep: record SLA warnings and breaches, close resolved "
        "tickets whose quiet period elapsed. Never deletes history."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            result = sweep(options["limit"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, sort_keys=True))
