import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt, jwt
from identity import google
from identity.security import IdentityError


@pytest.mark.parametrize("invalid", [None, "signature", "expired", "audience"])
def test_google_oidc_real_signature_expiry_and_audience_without_provider_network(settings, invalid):
    settings.GOOGLE_CLIENT_ID = "synthetic-client"
    settings.GOOGLE_CLIENT_SECRET = "synthetic-fixture"  # noqa: S105 -- local test fixture.
    settings.GOOGLE_REDIRECT_URI = "http://127.0.0.1:3000/ar/account"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "synthetic-test")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    signing_key = (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        if invalid == "signature"
        else key
    )
    signer = crypt.RSASigner.from_string(
        signing_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        key_id="synthetic-key",
    )
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "wrong" if invalid == "audience" else "synthetic-client",
        "sub": "synthetic-subject",
        "email_verified": True,
        "nonce": "synthetic-nonce",
        "iat": int((now - timedelta(hours=1)).timestamp()),
        "exp": int((now + timedelta(minutes=-1 if invalid == "expired" else 5)).timestamp()),
    }
    token = jwt.encode(signer, claims).decode()

    def transport(*args, **kwargs):
        return SimpleNamespace(
            status=200,
            data=json.dumps(
                {"synthetic-key": certificate.public_bytes(serialization.Encoding.PEM).decode()}
            ).encode(),
        )

    with (
        patch.object(google.requests, "post") as response,
        patch.object(google, "GoogleRequest", return_value=transport),
    ):
        response.return_value.json.return_value = {"id_token": token}
        if invalid:
            with pytest.raises(IdentityError):
                google.exchange("synthetic-code", "synthetic-verifier", "synthetic-nonce")
        else:
            assert (
                google.exchange("synthetic-code", "synthetic-verifier", "synthetic-nonce")["sub"]
                == "synthetic-subject"
            )
