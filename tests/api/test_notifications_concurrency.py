"""Concurrent worker retries use the same PostgreSQL reminder and one inbox effect."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import connections, transaction
from notifications import services
from notifications.models import DeadlineReminder, Notification
from test_catalog import catalog_settings as catalog_settings
from test_notifications import setup

pytestmark = pytest.mark.django_db(transaction=True)


def race(*actions):
    barrier = Barrier(len(actions))

    def run(action):
        connections.close_all()
        try:
            barrier.wait(timeout=15)
            return action()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(run, actions))


def test_concurrent_schedulers_and_deliveries_have_one_reminder_and_one_inbox():
    _, _, _, _, owner = setup()
    outcomes = race(
        lambda: services.schedule_owner(owner.pk), lambda: services.schedule_owner(owner.pk)
    )
    assert sorted(outcomes) == [0, 1]
    initial = DeadlineReminder.objects.get()
    with transaction.atomic():
        services.cancel(initial, "SYNTHETIC_OPTIONAL_DISABLE")
    outcomes = race(
        lambda: services.schedule_owner(owner.pk), lambda: services.schedule_owner(owner.pk)
    )
    assert sorted(outcomes) == [0, 1]
    reminder = DeadlineReminder.objects.get(status="SCHEDULED")
    assert reminder.pk != initial.pk
    with patch(
        "notifications.services.timezone.now", return_value=reminder.due_at + timedelta(seconds=1)
    ):
        results = race(lambda: services.deliver(reminder.pk), lambda: services.deliver(reminder.pk))
    assert sorted(results) == [False, True]
    assert Notification.objects.count() == 1
    assert DeadlineReminder.objects.filter(status="DELIVERED").count() == 1
    assert DeadlineReminder.objects.filter(status="CANCELLED").count() == 1
