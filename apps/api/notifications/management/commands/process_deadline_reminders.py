import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from notifications.services import process


class Command(BaseCommand):
    help = "Bounded recoverable sweep: recheck deadline evidence, schedule and deliver in-app only."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--max-batches", type=int, default=10)

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            result = process(options["batch_size"], options["max_batches"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, sort_keys=True))
