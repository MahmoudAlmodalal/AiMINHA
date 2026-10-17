import json
from typing import Any

from django.core.management.base import BaseCommand

from private_files.services import recover_abandoned


class Command(BaseCommand):
    help = "Purge expired local file attempts with physical fencing and confirmed quota release."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(json.dumps(recover_abandoned()))
