import uuid
from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class AccountManager(BaseUserManager):
    def create_user(self, email: str, password: str, **fields: Any) -> "Account":
        user = self.model(email=email.strip().lower(), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser):
    class State(models.TextChoices):
        PENDING = "PENDING"
        ACTIVE = "ACTIVE"
        DELETION_PENDING = "DELETION_PENDING"
        PURGING = "PURGING"
        DELETED = "DELETED"
        SUSPENDED = "SUSPENDED"

    class Role(models.TextChoices):
        STUDENT = "STUDENT"
        ADMIN = "ADMIN"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    birth_date = models.DateField()
    locale = models.CharField(max_length=2, choices=[("ar", "ar"), ("en", "en")])
    state = models.CharField(max_length=20, choices=State, default=State.PENDING)
    role = models.CharField(max_length=8, choices=Role, default=Role.STUDENT)
    admin_scopes = models.JSONField(default=list)
    email_verified_at = models.DateTimeField(null=True)
    session_epoch = models.PositiveIntegerField(default=1)
    consent_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    objects = AccountManager()
    USERNAME_FIELD = "email"

    @property
    def is_active(self) -> bool:
        return self.state == self.State.ACTIVE

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="identity_email_casefold_unique"),
            models.CheckConstraint(
                condition=models.Q(
                    state__in=[
                        "PENDING",
                        "ACTIVE",
                        "DELETION_PENDING",
                        "PURGING",
                        "DELETED",
                        "SUSPENDED",
                    ]
                ),
                name="identity_valid_state",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["STUDENT", "ADMIN"]), name="identity_valid_role"
            ),
        ]


class IdentitySession(models.Model):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    epoch = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True)
    # No client can set this. MFA integration is gated; tests use synthetic server proof.
    mfa_verified_at = models.DateTimeField(null=True)


class AuthIdentity(models.Model):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    provider = models.CharField(max_length=20, default="GOOGLE")
    subject = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "subject"], name="identity_subject_unique"),
            models.UniqueConstraint(
                fields=["account", "provider"], name="identity_provider_unique"
            ),
        ]


class Challenge(models.Model):
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=24)
    digest = models.CharField(max_length=64, unique=True)
    session_digest = models.CharField(max_length=64, blank=True)
    deletion_id = models.UUIDField(null=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=timezone.now)


class RateBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window_started = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)


class CommandReceipt(models.Model):
    scope = models.CharField(max_length=64)
    key_digest = models.CharField(max_length=64)
    body_digest = models.CharField(max_length=64)
    response = models.JSONField(default=dict)
    status = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "key_digest"], name="identity_command_unique")
        ]


class GoogleAuthorization(models.Model):
    state_digest = models.CharField(max_length=64, unique=True)
    session_digest = models.CharField(max_length=64)
    account = models.ForeignKey(Account, null=True, on_delete=models.PROTECT)
    intent = models.CharField(max_length=8)
    # PKCE verifier and nonce live only in the server-side Django session.
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True)
