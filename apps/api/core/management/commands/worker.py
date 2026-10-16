from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection


class Command(BaseCommand):
    help = "Bootstrap worker preflight only; durable jobs are not implemented."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check", action="store_true", help="Check database connectivity and exit."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["check"]:
            raise CommandError(
                "Worker execution disabled: durable job workflows await later phases."
            )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            raise CommandError("Worker database preflight failed.") from None
        self.stdout.write("Worker database preflight passed; job execution remains disabled.")
