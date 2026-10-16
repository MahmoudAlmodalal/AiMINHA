from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from credits.models import LedgerEntry, Wallet
from credits.services import initialize_policy
from django.db import connections
from django.utils import timezone
from identity.models import Account
from identity.security import IdentityError
from identity.services import issue, verify_email
from privacy.models import (
    DeletionRequest,
    FilePurgeTask,
    LegalEnvelope,
    PrivateAsset,
    RetentionPolicy,
)
from privacy.services import queue_expired_deletion, restore_account

pytestmark = pytest.mark.django_db(transaction=True)


def race(*actions):
    barrier = Barrier(len(actions))

    def run(action):
        try:
            barrier.wait(timeout=10)
            return action()
        except IdentityError as error:
            return error.code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(run, actions))


def test_verification_is_single_use_under_two_database_connections(settings):
    # Transaction tests flush seeded policy rows; restore the migration default.
    initialize_policy()
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    user = Account.objects.create_user(
        "race@example.invalid", "synthetic-only", birth_date=date(2000, 1, 1), locale="en"
    )
    token = issue(user, "VERIFY_EMAIL")
    outcomes = race(lambda: verify_email(token, None), lambda: verify_email(token, None))
    assert outcomes.count(None) == 1 and outcomes.count("INVALID_PROOF") == 1
    user.refresh_from_db()
    assert user.state == "ACTIVE"
    assert Wallet.objects.get(owner=user).posted_balance == 30
    assert LedgerEntry.objects.filter(owner=user, kind="SIGNUP_GRANT").count() == 1


@pytest.mark.parametrize("before_cutoff", [True, False])
def test_restore_and_purge_claim_serialize_on_the_same_account(before_cutoff):
    now = timezone.now()
    user = Account.objects.create(
        email="race@example.invalid",
        birth_date=date(2000, 1, 1),
        locale="ar",
        state="DELETION_PENDING",
        email_verified_at=now,
    )
    envelope = LegalEnvelope.objects.create(
        approved=True, min_days=1, max_days=60, evidence_ref=uuid4()
    )
    policy = RetentionPolicy.objects.create(version=20, legal_envelope=envelope)
    cutoff = now + timedelta(seconds=1) if before_cutoff else now
    deletion = DeletionRequest.objects.create(
        account=user,
        policy=policy,
        recovery_days=30,
        confirmed_at=cutoff - timedelta(days=30),
        restore_until=cutoff,
    )
    PrivateAsset.objects.create(owner=user, state="ACCEPTED", object_version="synthetic-version")
    token = issue(user, "RESTORE", deletion=deletion.pk)
    with patch("django.utils.timezone.now", return_value=now):
        outcomes = race(
            lambda: restore_account(token, None),
            lambda: queue_expired_deletion(user.pk),
            lambda: queue_expired_deletion(user.pk),
        )
    user.refresh_from_db()
    if before_cutoff:
        assert user.state == "ACTIVE" and FilePurgeTask.objects.count() == 0
        assert outcomes == [None, 0, 0]
    else:
        assert user.state == "PURGING" and FilePurgeTask.objects.count() == 1
        assert "RESTORATION_EXPIRED" in outcomes
        assert sorted(value for value in outcomes if isinstance(value, int)) == [0, 1]
