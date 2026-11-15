"""
Signed-JWT verification tests for Auth0 mode.

Tokens are signed with synthetic RSA keys generated at test time and exercise
the real ``_verify_auth0_token`` and ``resolve_current_user`` code paths. Only
the JWKS HTTP transport (``urllib.request.OpenerDirector.open``) is replaced,
so ``PyJWKClient`` caching, ``kid`` lookup, and refresh behavior stay real.
No Auth0 credentials or network access are involved.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from typing import Any

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from camply.db.models import User
from camply.server import auth
from camply.server.config import AuthMode, backend_config
from tests.server.conftest import maker

AUTH0_DOMAIN = "jwt-tests.us.auth0.com"
# Synthetic tenant domain used for issuer and JWKS URL derivation.

AUTH0_AUDIENCE = "https://api.camply.test"
# Synthetic API audience the verifier is configured to accept.

ISSUER = f"https://{AUTH0_DOMAIN}/"
# Issuer claim value the verifier expects.

JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
# JWKS URL the verifier is expected to fetch.


# ---------------------------------------------------------------------------
# Synthetic keys, tokens, and JWKS transport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticKey:
    """
    RSA key pair published under a ``kid`` in the synthetic JWKS.

    Attributes
    ----------
    kid : str
        Key identifier placed in the JWT header and the JWKS entry.
    private_pem : bytes
        PEM-encoded private key used to sign tokens.
    public_pem : bytes
        PEM-encoded public key (used to craft algorithm-confusion tokens).
    jwk : dict[str, Any]
        Public JSON Web Key entry as served by the JWKS endpoint.
    """

    kid: str
    private_pem: bytes
    public_pem: bytes
    jwk: dict[str, Any]


def _make_key(*, kid: str) -> SyntheticKey:
    """
    Generate a fresh RSA key pair and its public JWK.

    Parameters
    ----------
    kid : str
        Key identifier for the new key.

    Returns
    -------
    SyntheticKey
        The generated key material.
    """
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public))
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return SyntheticKey(
        kid=kid,
        private_pem=private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        public_pem=public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
        jwk=jwk,
    )


def _claims(**overrides: Any) -> dict[str, Any]:
    """
    Build a valid claim set for a unique user, applying overrides.

    Parameters
    ----------
    **overrides : Any
        Claims to replace; a value of ``None`` removes that claim.

    Returns
    -------
    dict[str, Any]
        Claims accepted by the verifier unless overridden.
    """
    subject = f"auth0|{uuid.uuid4().hex}"
    claims: dict[str, Any] = {
        "sub": subject,
        "email": f"{subject.split('|')[1]}@example.test",
        "email_verified": True,
        "iss": ISSUER,
        "aud": AUTH0_AUDIENCE,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    return {name: value for name, value in claims.items() if value is not None}


def _sign(key: SyntheticKey, claims: dict[str, Any] | None = None) -> str:
    """
    Sign claims as an RS256 JWT carrying the key's ``kid``.

    Parameters
    ----------
    key : SyntheticKey
        Signing key.
    claims : dict[str, Any] or None
        Claims to sign; defaults to a fresh valid claim set.

    Returns
    -------
    str
        Compact serialized JWT.
    """
    return jwt.encode(
        claims if claims is not None else _claims(),
        key.private_pem,
        algorithm="RS256",
        headers={"kid": key.kid},
    )


def _b64url(data: bytes) -> bytes:
    """Return unpadded URL-safe base64 for hand-built token segments."""
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _bearer(token: str) -> dict[str, str]:
    """Return an ``Authorization`` header carrying ``token``."""
    return {"Authorization": f"Bearer {token}"}


@dataclass
class JwksTransport:
    """
    Replacement JWKS HTTP transport that records requests.

    Attributes
    ----------
    keys : list[dict[str, Any]]
        JWK entries served by the next response.
    error : Exception or None
        When set, raised instead of serving a response.
    body : bytes or None
        When set, served verbatim instead of the JSON-encoded ``keys``.
    urls : list[str]
        URLs requested so far; its length is the fetch count.
    """

    keys: list[dict[str, Any]] = field(default_factory=list)
    error: Exception | None = None
    body: bytes | None = None
    urls: list[str] = field(default_factory=list)

    @property
    def fetches(self) -> int:
        """Return how many JWKS requests reached the transport."""
        return len(self.urls)

    def publish(self, *keys: SyntheticKey) -> None:
        """Serve exactly ``keys`` from the JWKS endpoint from now on."""
        self.keys = [key.jwk for key in keys]


@pytest.fixture(scope="module")
def key_one() -> SyntheticKey:
    """Return the primary synthetic signing key."""
    return _make_key(kid="key-one")


@pytest.fixture(scope="module")
def key_two() -> SyntheticKey:
    """Return a second key, used for rotation and wrong-key signatures."""
    return _make_key(kid="key-two")


@dataclass
class UserinfoTransport:
    """
    Mock transport for the Auth0 /userinfo endpoint.

    Attributes
    ----------
    responses : dict[str, dict[str, Any]]
        Bearer token to userinfo payload mapping.
    default_payload : dict[str, Any] or None
        Fallback payload when token is not in ``responses``.
    error : Exception or None
        When set, raised on the next request.
    status_code : int
        HTTP status code to return.
    requests : list[httpx2.Request]
        Recorded requests.
    """

    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_payload: dict[str, Any] | None = None
    error: Exception | None = None
    status_code: int = 200
    requests: list[httpx2.Request] = field(default_factory=list)

    @property
    def fetches(self) -> int:
        """Return how many requests reached userinfo."""
        return len(self.requests)

    def set_userinfo(self, token: str, payload: dict[str, Any]) -> None:
        """Set the mock response payload for ``token``."""
        self.responses[token] = payload

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Process the HTTP request and return the mock response."""
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.status_code != 200:
            return httpx2.Response(
                status_code=self.status_code,
                request=request,
            )
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        data = self.responses.get(token, self.default_payload)
        if data is None:
            return httpx2.Response(
                status_code=401,
                request=request,
            )
        return httpx2.Response(
            status_code=200,
            json=data,
            request=request,
        )


@pytest.fixture(autouse=True)
def auth0_jwt_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """
    Configure Auth0 mode for a synthetic tenant with clean caches.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest patching fixture.

    Yields
    ------
    None
        Control to the test; client caches are cleared afterward.
    """
    monkeypatch.setattr(backend_config, "auth_mode", AuthMode.AUTH0)
    monkeypatch.setattr(backend_config, "auth0_domain", AUTH0_DOMAIN)
    monkeypatch.setattr(backend_config, "auth0_audience", AUTH0_AUDIENCE)
    default_userinfo = UserinfoTransport()
    monkeypatch.setattr(
        auth,
        "_userinfo_transport",
        httpx2.MockTransport(default_userinfo.handle_request),
    )
    auth._jwks_client_cache.clear()
    auth._userinfo_cache.clear()
    yield
    auth._jwks_client_cache.clear()
    auth._userinfo_cache.clear()


@pytest.fixture
def userinfo(monkeypatch: pytest.MonkeyPatch) -> UserinfoTransport:
    """
    Replace the userinfo HTTP transport, reset cache, and return the transport.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.

    Returns
    -------
    UserinfoTransport
        Configurable userinfo mock transport.
    """
    transport = UserinfoTransport()
    mock_transport = httpx2.MockTransport(transport.handle_request)
    monkeypatch.setattr(auth, "_userinfo_transport", mock_transport)
    auth._userinfo_cache.clear()
    return transport


@pytest.fixture
def jwks(monkeypatch: pytest.MonkeyPatch, key_one: SyntheticKey) -> JwksTransport:
    """
    Replace only the JWKS HTTP transport, initially publishing ``key_one``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest patching fixture.
    key_one : SyntheticKey
        Key published by default.

    Returns
    -------
    JwksTransport
        Controllable transport shared with the test.
    """
    transport = JwksTransport()
    transport.publish(key_one)

    def fake_open(
        self: urllib.request.OpenerDirector,
        fullurl: urllib.request.Request | str,
        data: Any = None,
        timeout: float | None = None,
    ) -> io.BytesIO:
        """Serve the configured JWKS document or raise the configured error."""
        url = fullurl if isinstance(fullurl, str) else fullurl.full_url
        transport.urls.append(url)
        if transport.error is not None:
            raise transport.error
        if transport.body is not None:
            return io.BytesIO(transport.body)
        return io.BytesIO(json.dumps({"keys": transport.keys}).encode())

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fake_open)
    return transport


def _verify(token: str) -> dict[str, Any]:
    """Run the real async verifier to completion and return its claims."""
    return asyncio.run(auth._verify_auth0_token(token))


def _reject(token: str) -> HTTPException:
    """
    Run the verifier and return the ``HTTPException`` it must raise.

    Parameters
    ----------
    token : str
        Token expected to be rejected.

    Returns
    -------
    HTTPException
        The raised exception, for status and detail assertions.
    """
    with pytest.raises(HTTPException) as excinfo:
        _verify(token)
    return excinfo.value


# ---------------------------------------------------------------------------
# T2.6.1 / T2.6.2 — claim and algorithm enforcement
# ---------------------------------------------------------------------------


class TestSignedTokenVerification:
    """The real verifier accepts only correctly signed, complete tokens."""

    def test_valid_token_returns_claims(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A correctly signed token yields its claims via the real JWKS URL."""
        claims = _claims()
        payload = _verify(_sign(key_one, claims))
        assert payload["sub"] == claims["sub"]
        assert payload["email"] == claims["email"]
        assert jwks.urls == [JWKS_URL]

    def test_audience_list_containing_expected_value_is_accepted(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Auth0 may issue ``aud`` as a list that includes the API audience."""
        claims = _claims(aud=[AUTH0_AUDIENCE, f"https://{AUTH0_DOMAIN}/userinfo"])
        assert _verify(_sign(key_one, claims))["sub"] == claims["sub"]

    def test_expired_token_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A token past its ``exp`` yields 401 'Token has expired'."""
        error = _reject(_sign(key_one, _claims(exp=int(time.time()) - 60)))
        assert error.status_code == 401
        assert error.detail == "Token has expired"

    @pytest.mark.parametrize(
        "missing", ["exp", "sub", "iss", "aud"], ids=lambda name: f"no-{name}"
    )
    def test_missing_required_claim_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey, missing: str
    ) -> None:
        """Tokens lacking any required claim are rejected with 401."""
        error = _reject(_sign(key_one, _claims(**{missing: None})))
        assert error.status_code == 401
        assert missing in str(error.detail)

    @pytest.mark.parametrize("subject", ["", "   "], ids=["empty", "blank"])
    def test_empty_subject_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey, subject: str
    ) -> None:
        """A present but empty or blank ``sub`` is not an identity."""
        error = _reject(_sign(key_one, _claims(sub=subject)))
        assert error.status_code == 401

    @pytest.mark.parametrize(
        "issuer",
        [
            "https://evil.us.auth0.com/",
            f"https://{AUTH0_DOMAIN}",
        ],
        ids=["other-tenant", "missing-trailing-slash"],
    )
    def test_wrong_issuer_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey, issuer: str
    ) -> None:
        """The issuer must match the configured tenant exactly."""
        error = _reject(_sign(key_one, _claims(iss=issuer)))
        assert error.status_code == 401
        assert "issuer" in str(error.detail).lower()

    @pytest.mark.parametrize(
        "audience",
        ["https://other-api.test", ["https://other-api.test"]],
        ids=["string", "list"],
    )
    def test_wrong_audience_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey, audience: Any
    ) -> None:
        """The audience must include the configured API."""
        error = _reject(_sign(key_one, _claims(aud=audience)))
        assert error.status_code == 401
        assert "audience" in str(error.detail).lower()

    def test_signature_from_unpublished_key_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey, key_two: SyntheticKey
    ) -> None:
        """A token signed by another key but claiming a trusted ``kid`` fails."""
        forged = jwt.encode(
            _claims(),
            key_two.private_pem,
            algorithm="RS256",
            headers={"kid": key_one.kid},
        )
        error = _reject(forged)
        assert error.status_code == 401
        assert "signature" in str(error.detail).lower()

    def test_tampered_signature_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Altering a signature byte invalidates the token."""
        header, body, signature = _sign(key_one).split(".")
        middle = len(signature) // 2
        flipped = "A" if signature[middle] != "A" else "B"
        tampered = ".".join(
            [header, body, signature[:middle] + flipped + signature[middle + 1 :]]
        )
        assert _reject(tampered).status_code == 401

    def test_tampered_payload_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Swapping the subject while keeping the old signature fails."""
        header, body, signature = _sign(key_one, _claims(sub="auth0|victim")).split(".")
        padded = body + "=" * (-len(body) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
        claims["sub"] = "auth0|attacker"
        forged_body = _b64url(json.dumps(claims).encode()).decode()
        error = _reject(".".join([header, forged_body, signature]))
        assert error.status_code == 401
        assert "signature" in str(error.detail).lower()

    def test_hs256_signed_with_public_key_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """The classic RS256-to-HS256 confusion attack is rejected."""
        header = _b64url(
            json.dumps({"alg": "HS256", "typ": "JWT", "kid": key_one.kid}).encode()
        )
        body = _b64url(json.dumps(_claims()).encode())
        signing_input = header + b"." + body
        mac = hmac.new(key_one.public_pem, signing_input, hashlib.sha256).digest()
        error = _reject((signing_input + b"." + _b64url(mac)).decode())
        assert error.status_code == 401
        assert "alg" in str(error.detail).lower()

    def test_unsecured_alg_none_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Unsigned ``alg=none`` tokens are never accepted."""
        token = jwt.encode(
            _claims(), key=None, algorithm="none", headers={"kid": key_one.kid}
        )
        assert _reject(token).status_code == 401

    def test_other_rsa_algorithm_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Only RS256 is allowed, even with the correct private key."""
        token = jwt.encode(
            _claims(),
            key_one.private_pem,
            algorithm="RS384",
            headers={"kid": key_one.kid},
        )
        error = _reject(token)
        assert error.status_code == 401
        assert "alg" in str(error.detail).lower()

    def test_malformed_token_is_rejected(self, jwks: JwksTransport) -> None:
        """Garbage that is not a JWT yields 401 without a JWKS request."""
        assert _reject("not-a-jwt").status_code == 401
        assert jwks.fetches == 0


# ---------------------------------------------------------------------------
# T2.6.3 — JWKS caching, rotation, unknown kids, outages
# ---------------------------------------------------------------------------


class TestJwksBehavior:
    """JWKS handling distinguishes bad credentials from service failures."""

    def test_keys_are_cached_across_verifications(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """Repeated verifications fetch the JWKS only once."""
        for _ in range(3):
            _verify(_sign(key_one))
        assert jwks.fetches == 1

    def test_cached_key_survives_jwks_outage(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A warm cache keeps authenticating while the JWKS endpoint is down."""
        _verify(_sign(key_one))
        jwks.error = urllib.error.URLError("connection refused")
        assert _verify(_sign(key_one))["iss"] == ISSUER
        assert jwks.fetches == 1

    def test_unknown_kid_is_rejected_as_invalid_credentials(
        self, jwks: JwksTransport, key_two: SyntheticKey
    ) -> None:
        """A ``kid`` absent from the JWKS yields 401, not a service error."""
        error = _reject(_sign(key_two))
        assert error.status_code == 401
        assert "key-two" in str(error.detail)

    def test_token_without_kid_is_rejected(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A token lacking a ``kid`` header cannot select a signing key."""
        token = jwt.encode(_claims(), key_one.private_pem, algorithm="RS256")
        assert _reject(token).status_code == 401

    def test_repeated_unknown_kid_does_not_hammer_jwks(
        self, jwks: JwksTransport, key_two: SyntheticKey
    ) -> None:
        """Unknown-``kid`` refreshes are rate limited by the client cooldown."""
        for _ in range(5):
            assert _reject(_sign(key_two)).status_code == 401
        assert jwks.fetches == 1

    def test_key_rotation_accepts_new_kid(
        self, jwks: JwksTransport, key_one: SyntheticKey, key_two: SyntheticKey
    ) -> None:
        """A newly published key is fetched on demand and then cached."""
        _verify(_sign(key_one))
        jwks.publish(key_one, key_two)
        # Skip PyJWT's 30s refresh cooldown instead of sleeping.
        auth._get_jwks_client().cooldown_duration = 0

        assert _verify(_sign(key_two))["iss"] == ISSUER
        assert _verify(_sign(key_two))["iss"] == ISSUER
        assert jwks.fetches == 2

    def test_rotated_in_key_signed_token_with_old_cache_is_cooldown_limited(
        self, jwks: JwksTransport, key_one: SyntheticKey, key_two: SyntheticKey
    ) -> None:
        """Within the cooldown window a freshly rotated key is still unknown."""
        _verify(_sign(key_one))
        jwks.publish(key_one, key_two)
        assert _reject(_sign(key_two)).status_code == 401
        assert jwks.fetches == 1

    def test_outage_with_cold_cache_is_service_unavailable(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """An unreachable JWKS endpoint is 503, and recovery needs no restart."""
        jwks.error = urllib.error.URLError("connection refused")
        assert _reject(_sign(key_one)).status_code == 503

        jwks.error = None
        assert _verify(_sign(key_one))["iss"] == ISSUER

    def test_jwks_http_error_is_service_unavailable(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A 5xx response from the JWKS endpoint is a temporary failure."""
        jwks.error = urllib.error.HTTPError(
            JWKS_URL,
            502,
            "Bad Gateway",
            {},
            io.BytesIO(b""),  # type: ignore[arg-type]
        )
        assert _reject(_sign(key_one)).status_code == 503

    def test_jwks_timeout_is_service_unavailable(
        self, jwks: JwksTransport, key_one: SyntheticKey
    ) -> None:
        """A JWKS request timeout is a temporary failure."""
        jwks.error = TimeoutError("timed out")
        assert _reject(_sign(key_one)).status_code == 503

    @pytest.mark.parametrize(
        "body",
        [b"<html>gateway error</html>", b'{"keys": []}'],
        ids=["not-json", "no-keys"],
    )
    def test_unusable_jwks_document_is_service_unavailable(
        self, jwks: JwksTransport, key_one: SyntheticKey, body: bytes
    ) -> None:
        """A garbage or empty JWKS document is the service's fault, not 401."""
        jwks.body = body
        assert _reject(_sign(key_one)).status_code == 503

    def test_outage_during_unknown_kid_refresh_is_service_unavailable(
        self, jwks: JwksTransport, key_one: SyntheticKey, key_two: SyntheticKey
    ) -> None:
        """If the refresh for an unknown ``kid`` fails, report 503 not 401."""
        _verify(_sign(key_one))
        auth._get_jwks_client().cooldown_duration = 0
        jwks.error = urllib.error.URLError("connection refused")
        assert _reject(_sign(key_two)).status_code == 503
        # Known keys still verify from cache during the same outage.
        assert _verify(_sign(key_one))["iss"] == ISSUER

    def test_key_removed_from_jwks_stops_verifying(
        self, jwks: JwksTransport, key_one: SyntheticKey, key_two: SyntheticKey
    ) -> None:
        """A key dropped from the published JWKS is rejected once cache refreshes."""
        _verify(_sign(key_one))
        jwks.publish(key_two)
        auth._get_jwks_client().jwk_set_cache.put(None)
        auth._get_jwks_client().cooldown_duration = 0
        assert _reject(_sign(key_one)).status_code == 401


# ---------------------------------------------------------------------------
# T2.6.4 — signed-token API requests
# ---------------------------------------------------------------------------

API_ME = "/api/me"
API_SCANS = "/api/scans"


def _fetch_user(*, auth0_id: str) -> User | None:
    """Return the persisted user for ``auth0_id`` (or ``None``)."""

    async def query() -> User | None:
        async with maker() as session:
            return await session.scalar(select(User).where(User.auth0_id == auth0_id))

    return asyncio.run(query())


def _invite(*, auth0_id: str) -> None:
    """Mark the persisted user for ``auth0_id`` as invited."""

    async def update() -> None:
        async with maker() as session:
            user = await session.scalar(select(User).where(User.auth0_id == auth0_id))
            assert user is not None
            user.is_invited = True
            await session.commit()

    asyncio.run(update())


@pytest.fixture
def signed_token(
    jwks: JwksTransport, key_one: SyntheticKey
) -> Callable[..., tuple[str, dict[str, str]]]:
    """
    Return a factory minting a signed token and its bearer headers.

    Parameters
    ----------
    jwks : JwksTransport
        Ensures the JWKS transport is replaced and publishes ``key_one``.
    key_one : SyntheticKey
        Signing key.

    Returns
    -------
    Callable[..., tuple[str, dict[str, str]]]
        Factory taking claim overrides, returning ``(sub, headers)``.
    """

    def mint(**overrides: Any) -> tuple[str, dict[str, str]]:
        """Create a token for a unique user and return its subject and headers."""
        claims = _claims(**overrides)
        return claims["sub"], _bearer(_sign(key_one, claims))

    return mint


def _scan_payload() -> dict[str, Any]:
    """Return a valid scan creation body for the seeded campground."""
    return {
        "provider_id": 1,
        "campground_id": "cg_1",
        "start_date": "2027-07-01",
        "end_date": "2027-07-05",
        "min_stay_length": 1,
        "preferred_types": [],
        "require_electric": False,
    }


class TestSignedTokenApi:
    """Signed bearer tokens drive provisioning, isolation, and invitations."""

    def test_missing_bearer_is_unauthorized(self, test_client: TestClient) -> None:
        """Requests without credentials get 401 in Auth0 mode."""
        assert test_client.get(API_ME).status_code == 401

    def test_invalid_token_is_unauthorized_and_outage_is_unavailable(
        self,
        test_client: TestClient,
        jwks: JwksTransport,
        key_one: SyntheticKey,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """Bad credentials return 401 while a JWKS outage returns 503."""
        _, expired = signed_token(exp=int(time.time()) - 60)
        assert test_client.get(API_ME, headers=expired).status_code == 401

        jwks.error = urllib.error.URLError("connection refused")
        auth._jwks_client_cache.clear()
        _, valid = signed_token()
        assert test_client.get(API_ME, headers=valid).status_code == 503

    def test_first_request_provisions_user_once(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """First sight of a ``sub`` creates one uninvited, non-admin user."""
        subject, headers = signed_token(email="Mixed.Case@Example.TEST")
        assert _fetch_user(auth0_id=subject) is None

        first = test_client.get(API_ME, headers=headers)
        second = test_client.get(API_ME, headers=headers)

        assert first.status_code == second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        user = _fetch_user(auth0_id=subject)
        assert user is not None
        assert user.email == "mixed.case@example.test"
        assert user.is_invited is False
        assert user.is_admin is False
        assert first.json()["is_invited"] is False

    def test_email_less_token_never_populates_user_email_with_sub(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Ensure tokens without email claims or userinfo email never provision with sub as email.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        subject, headers = signed_token(
            email=None,
            email_verified=None,
            sub=f"auth0|NoEmail{uuid.uuid4().hex}",
        )
        userinfo.default_payload = {}
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "ERR_VERIFIED_EMAIL_REQUIRED"
        assert _fetch_user(auth0_id=subject) is None

    def test_unverified_email_in_jwt_is_rejected_for_new_user(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Ensure an unverified email claim rejects new user provisioning with HTTP 403.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        subject, headers = signed_token(
            email="unverified@example.test",
            email_verified=False,
        )
        userinfo.default_payload = {
            "email": "unverified@example.test",
            "email_verified": False,
        }
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "ERR_VERIFIED_EMAIL_REQUIRED"
        assert _fetch_user(auth0_id=subject) is None

    def test_userinfo_fallback_provisions_user(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Verify userinfo fallback provisions the account when the JWT lacks email.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        subject, headers = signed_token(email=None, email_verified=None)
        token = headers["Authorization"].removeprefix("Bearer ").strip()
        userinfo.set_userinfo(
            token=token,
            payload={"email": "Fallback.User@Example.Test", "email_verified": True},
        )
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "fallback.user@example.test"
        user = _fetch_user(auth0_id=subject)
        assert user is not None
        assert user.email == "fallback.user@example.test"

    def test_userinfo_cache_hit_avoids_repeated_requests(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Ensure cached userinfo resolves subsequent requests without extra network calls.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        subject, headers = signed_token(email=None, email_verified=None)
        token = headers["Authorization"].removeprefix("Bearer ").strip()
        userinfo.set_userinfo(
            token=token,
            payload={"email": "cached@example.test", "email_verified": True},
        )
        resp1 = test_client.get(API_ME, headers=headers)
        resp2 = test_client.get(API_ME, headers=headers)
        assert resp1.status_code == resp2.status_code == 200
        assert userinfo.fetches == 1

    def test_userinfo_outage_returns_503(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Verify that identity provider userinfo outages yield 503 so clients can retry.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        _, headers = signed_token(email=None, email_verified=None)
        userinfo.error = httpx2.ConnectError("Connection refused")
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 503
        assert "retry" in response.json()["detail"].lower()

    def test_userinfo_token_rejected_returns_401(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Verify that token rejection by userinfo yields 401 Unauthorized.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        _, headers = signed_token(email=None, email_verified=None)
        userinfo.status_code = 401
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 401

    def test_namespaced_claims_are_recognized(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Verify that namespaced https://camply/ claims are accepted for verified email.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        subject, headers = signed_token(
            email=None,
            email_verified=None,
            **{
                "https://camply/email": "Namespaced@Example.Test",
                "https://camply/email_verified": True,
            },
        )
        response = test_client.get(API_ME, headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == "namespaced@example.test"

    def test_duplicate_email_conflict_returns_409_not_500(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """
        Verify that sign-in colliding with an existing user's email returns 409 ERR_EMAIL_CONFLICT.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        """
        shared_email = "shared.identity@example.test"
        sub_one, headers_one = signed_token(email=shared_email)
        assert test_client.get(API_ME, headers=headers_one).status_code == 200
        user_one = _fetch_user(auth0_id=sub_one)
        assert user_one is not None

        sub_two, headers_two = signed_token(email=shared_email)
        res = test_client.get(API_ME, headers=headers_two)
        assert res.status_code == 409
        assert res.json()["detail"] == {
            "error": "ERR_EMAIL_CONFLICT",
            "message": "An account with this email address already exists.",
        }
        assert _fetch_user(auth0_id=sub_two) is None
        user_one_check = _fetch_user(auth0_id=sub_one)
        assert user_one_check is not None
        assert user_one_check.id == user_one.id

    def test_concurrent_first_login_race_on_same_auth0_id_returns_winner(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Ensure concurrent first-login on the same auth0_id resolves to the winner without 500.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        monkeypatch : pytest.MonkeyPatch
            Pytest monkeypatch fixture.
        """
        from sqlalchemy.exc import IntegrityError

        from camply.server.services.users import flush_new_user as real_flush

        subject, headers = signed_token(email="concurrent.winner@example.test")

        async def race_flush(session: Any, user: User) -> None:
            async with maker() as other_session:
                other_user = User(
                    auth0_id=user.auth0_id,
                    email=user.email,
                    is_invited=False,
                    is_admin=False,
                    scanning_enabled=True,
                )
                await real_flush(other_session, other_user)
                await other_session.commit()
            raise IntegrityError(
                "duplicate key",
                params={},
                orig=Exception("duplicate key"),
            )

        monkeypatch.setattr(auth, "flush_new_user", race_flush)
        res = test_client.get(API_ME, headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "concurrent.winner@example.test"
        persisted = _fetch_user(auth0_id=subject)
        assert persisted is not None

    def test_concurrent_first_login_race_with_different_auth0_id_returns_409(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Ensure concurrent first-login with duplicate email returns 409 without 500.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        monkeypatch : pytest.MonkeyPatch
            Pytest monkeypatch fixture.
        """
        from sqlalchemy.exc import IntegrityError

        from camply.server.services.users import flush_new_user as real_flush

        subject, headers = signed_token(email="concurrent.conflict@example.test")

        async def race_flush(session: Any, user: User) -> None:
            async with maker() as other_session:
                other_user = User(
                    auth0_id=f"auth0|other_{uuid.uuid4().hex}",
                    email=user.email,
                    is_invited=False,
                    is_admin=False,
                    scanning_enabled=True,
                )
                await real_flush(other_session, other_user)
                await other_session.commit()
            raise IntegrityError(
                "duplicate key",
                params={},
                orig=Exception("duplicate key"),
            )

        monkeypatch.setattr(auth, "flush_new_user", race_flush)
        res = test_client.get(API_ME, headers=headers)
        assert res.status_code == 409
        assert res.json()["detail"] == {
            "error": "ERR_EMAIL_CONFLICT",
            "message": "An account with this email address already exists.",
        }

    def test_existing_user_email_change_sync_preserves_associations(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        key_one: SyntheticKey,
    ) -> None:
        """
        Verify that a verified email change updates User.email and preserves user data.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        key_one : SyntheticKey
            Primary synthetic RSA key.
        """
        subject, headers_old = signed_token(email="old.address@example.test")
        assert test_client.get(API_ME, headers=headers_old).status_code == 200
        _invite(auth0_id=subject)

        patch_res = test_client.patch(
            API_ME,
            json={"pushover_token": "token_xyz123"},
            headers=headers_old,
        )
        assert patch_res.status_code == 200

        scan_res = test_client.post(
            API_SCANS, json=_scan_payload(), headers=headers_old
        )
        assert scan_res.status_code == 201
        scan_id = scan_res.json()["id"]

        user_before = _fetch_user(auth0_id=subject)
        assert user_before is not None

        claims_new = _claims(
            sub=subject,
            email="NEW.ADDRESS@EXAMPLE.TEST",
            email_verified=True,
        )
        headers_new = _bearer(_sign(key_one, claims_new))

        me_res = test_client.get(API_ME, headers=headers_new)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "new.address@example.test"
        assert me_res.json()["id"] == str(user_before.id)
        assert me_res.json()["pushover_token"] == "token_xyz123"
        assert me_res.json()["is_invited"] is True

        user_after = _fetch_user(auth0_id=subject)
        assert user_after is not None
        assert user_after.id == user_before.id
        assert user_after.email == "new.address@example.test"
        assert user_after.pushover_token == "token_xyz123"
        assert user_after.is_invited is True

        scans_res = test_client.get(API_SCANS, headers=headers_new)
        assert scans_res.status_code == 200
        assert [s["id"] for s in scans_res.json()["scans"]] == [scan_id]

    def test_existing_user_email_change_conflict_returns_409(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        key_one: SyntheticKey,
    ) -> None:
        """
        Verify that changing an email to one claimed by another returns 409 without altering the user.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        key_one : SyntheticKey
            Primary synthetic RSA key.
        """
        sub_a, headers_a = signed_token(email="user.alpha@example.test")
        sub_b, headers_b = signed_token(email="user.beta@example.test")
        assert test_client.get(API_ME, headers=headers_a).status_code == 200
        assert test_client.get(API_ME, headers=headers_b).status_code == 200

        claims_conflict = _claims(
            sub=sub_a,
            email="user.beta@example.test",
            email_verified=True,
        )
        headers_conflict = _bearer(_sign(key_one, claims_conflict))
        res = test_client.get(API_ME, headers=headers_conflict)
        assert res.status_code == 409
        assert res.json()["detail"] == {
            "error": "ERR_EMAIL_CONFLICT",
            "message": "An account with this email address already exists.",
        }

        user_a = _fetch_user(auth0_id=sub_a)
        assert user_a is not None
        assert user_a.email == "user.alpha@example.test"

    def test_existing_user_unverified_email_does_not_sync(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        key_one: SyntheticKey,
    ) -> None:
        """
        Verify that an unverified email for an existing user does not overwrite stored email.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        key_one : SyntheticKey
            Primary synthetic RSA key.
        """
        subject, headers_valid = signed_token(email="verified.original@example.test")
        assert test_client.get(API_ME, headers=headers_valid).status_code == 200

        claims_unverified = _claims(
            sub=subject,
            email="unverified.candidate@example.test",
            email_verified=False,
        )
        token_unverified = _sign(key_one, claims_unverified)
        userinfo.set_userinfo(
            token=token_unverified,
            payload={
                "email": "unverified.candidate@example.test",
                "email_verified": False,
            },
        )
        headers = _bearer(token_unverified)

        res = test_client.get(API_ME, headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "verified.original@example.test"

        user = _fetch_user(auth0_id=subject)
        assert user is not None
        assert user.email == "verified.original@example.test"

    def test_existing_user_missing_email_does_not_alter_user(
        self,
        test_client: TestClient,
        userinfo: UserinfoTransport,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
        key_one: SyntheticKey,
    ) -> None:
        """
        Verify that an existing user presenting a token lacking email claims keeps their stored email.

        Parameters
        ----------
        test_client : TestClient
            FastAPI test client.
        userinfo : UserinfoTransport
            Mock transport for Auth0 userinfo.
        signed_token : Callable[..., tuple[str, dict[str, str]]]
            Signed token factory.
        key_one : SyntheticKey
            Primary synthetic RSA key.
        """
        subject, headers_valid = signed_token(email="stable@example.test")
        assert test_client.get(API_ME, headers=headers_valid).status_code == 200

        claims_no_email = _claims(sub=subject, email=None, email_verified=None)
        token_no_email = _sign(key_one, claims_no_email)
        userinfo.set_userinfo(token=token_no_email, payload={})
        headers = _bearer(token_no_email)

        res = test_client.get(API_ME, headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "stable@example.test"

        user = _fetch_user(auth0_id=subject)
        assert user is not None
        assert user.email == "stable@example.test"

    def test_distinct_subjects_get_distinct_users(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """Different tokens map to different persisted accounts."""
        _, headers_a = signed_token()
        _, headers_b = signed_token()
        id_a = test_client.get(API_ME, headers=headers_a).json()["id"]
        id_b = test_client.get(API_ME, headers=headers_b).json()["id"]
        assert id_a != id_b

    def test_scan_ownership_is_isolated_between_users(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """One user cannot list, read, edit, or delete another user's scan."""
        _, owner = signed_token()
        _, other = signed_token()

        created = test_client.post(API_SCANS, json=_scan_payload(), headers=owner)
        assert created.status_code == 201, created.text
        scan_id = created.json()["id"]
        scan_url = f"{API_SCANS}/{scan_id}"

        owned = test_client.get(API_SCANS, headers=owner).json()
        assert [scan["id"] for scan in owned["scans"]] == [scan_id]
        assert test_client.get(API_SCANS, headers=other).json()["scans"] == []
        assert test_client.get(scan_url, headers=other).status_code == 404
        assert (
            test_client.patch(
                scan_url, json={"is_active": False}, headers=other
            ).status_code
            == 404
        )
        assert test_client.delete(scan_url, headers=other).status_code == 404

        # The owner's scan is untouched by the foreign attempts.
        still_there = test_client.get(scan_url, headers=owner)
        assert still_there.status_code == 200
        assert still_there.json()["is_active"] is True
        assert test_client.delete(scan_url, headers=owner).status_code == 204

    def test_invite_only_blocks_uninvited_signed_user(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """Invite-only mode returns ERR_INVITE_REQUIRED until the user is invited."""
        monkeypatch.setattr(backend_config, "invite_only", True)
        subject, headers = signed_token()

        # Profile access stays open so the UI can show the request-access flow.
        assert test_client.get(API_ME, headers=headers).status_code == 200
        for response in (
            test_client.get(API_SCANS, headers=headers),
            test_client.post(API_SCANS, json=_scan_payload(), headers=headers),
        ):
            assert response.status_code == 403
            assert response.json()["detail"]["error"] == "ERR_INVITE_REQUIRED"

        _invite(auth0_id=subject)
        assert test_client.get(API_SCANS, headers=headers).status_code == 200
        created = test_client.post(API_SCANS, json=_scan_payload(), headers=headers)
        assert created.status_code == 201, created.text

    def test_open_access_allows_uninvited_signed_user(
        self,
        test_client: TestClient,
        signed_token: Callable[..., tuple[str, dict[str, str]]],
    ) -> None:
        """Without invite-only mode an uninvited user manages scans."""
        _, headers = signed_token()
        created = test_client.post(API_SCANS, json=_scan_payload(), headers=headers)
        assert created.status_code == 201, created.text
