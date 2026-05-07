"""
qaforge.api.auth_manager
========================
Centralised auth — every protocol reuses this. Two flows are supported:

1. **OAuth 2.0 client_credentials** — service-to-service tokens.
2. **Password + OTP**             — interactive user login + 2FA.

Tokens are cached per (env, flow, identity) for the duration of the run.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from qaforge.core.config_loader import Config, secret
from qaforge.core.logger import get_logger

log = get_logger(__name__)


@dataclass
class AuthToken:
    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0  # epoch seconds

    @property
    def header(self) -> Dict[str, str]:
        return {"Authorization": f"{self.token_type} {self.access_token}"}

    def is_valid(self) -> bool:
        return self.access_token and time.time() < (self.expires_at - 30)


class AuthManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._cache: Dict[str, AuthToken] = {}

    # ---------- OAuth client_credentials ----------
    def oauth_token(self, scope: Optional[str] = None) -> AuthToken:
        key = f"oauth:{scope or self.cfg.auth.oauth.scope}"
        if key in self._cache and self._cache[key].is_valid():
            return self._cache[key]

        client_id = secret(self.cfg.auth.oauth.client_id_env)
        client_secret = secret(self.cfg.auth.oauth.client_secret_env)
        log.info("Requesting OAuth client_credentials token")
        resp = httpx.post(
            self.cfg.auth.oauth.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope or self.cfg.auth.oauth.scope,
            },
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        token = AuthToken(
            access_token=body["access_token"],
            token_type=body.get("token_type", "Bearer"),
            expires_at=time.time() + int(body.get("expires_in", 3600)),
        )
        self._cache[key] = token
        return token

    # ---------- Password + OTP ----------
    def password_otp_token(self, email: str, password: str, otp: str) -> AuthToken:
        key = f"pwotp:{email}"
        if key in self._cache and self._cache[key].is_valid():
            return self._cache[key]

        log.info(f"Logging in {email} via password+OTP")
        # Step 1: password login -> challenge
        r1 = httpx.post(
            self.cfg.auth.password_otp.login_url,
            json={"email": email, "password": password},
            timeout=20,
        )
        r1.raise_for_status()
        challenge_id = r1.json()["challenge_id"]

        # Step 2: verify OTP -> token
        r2 = httpx.post(
            self.cfg.auth.password_otp.otp_url,
            json={"challenge_id": challenge_id, "code": otp},
            timeout=20,
        )
        r2.raise_for_status()
        body = r2.json()
        token = AuthToken(
            access_token=body["access_token"],
            token_type=body.get("token_type", "Bearer"),
            expires_at=time.time() + int(body.get("expires_in", 3600)),
        )
        self._cache[key] = token
        return token

    # ---------- helper for role-based checks ----------
    def assume_role(self, role: str) -> AuthToken:
        """Return an OAuth token with a scope matching the role (smoke RBAC test pattern)."""
        scope_map = {
            "admin": "read write admin",
            "editor": "read write",
            "viewer": "read",
        }
        scope = scope_map.get(role)
        if not scope:
            raise ValueError(f"Unknown role: {role}")
        return self.oauth_token(scope=scope)
