"""
qaforge.api.grpc.client
=======================
Thin wrapper around `grpc` for unary, server-streaming, client-streaming and
bidi-streaming RPCs.

Usage pattern:
    from generated_pb2_grpc import UserServiceStub
    from generated_pb2 import GetUserRequest

    grpc_client = GrpcClient(cfg).connect()
    stub = grpc_client.stub(UserServiceStub)
    resp = stub.GetUser(GetUserRequest(id="123"), metadata=grpc_client.auth_metadata())

We intentionally do NOT import generated stubs here — they belong with the
proto files in `proto/` and are imported in the steps.
"""
from __future__ import annotations

from typing import Iterator, List, Optional, Tuple

import grpc

from qaforge.api.auth_manager import AuthManager, AuthToken
from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class GrpcClient:
    def __init__(self, cfg: Config, auth: Optional[AuthManager] = None):
        self.cfg = cfg
        self.auth = auth
        self._channel: Optional[grpc.Channel] = None
        self._token: Optional[AuthToken] = None

    def connect(self) -> "GrpcClient":
        target = f"{self.cfg.api.grpc.host}:{self.cfg.api.grpc.port}"
        if self.cfg.api.grpc.use_tls:
            creds = grpc.ssl_channel_credentials()
            self._channel = grpc.secure_channel(target, creds)
        else:
            self._channel = grpc.insecure_channel(target)
        log.info(f"gRPC channel connected to {target} (tls={self.cfg.api.grpc.use_tls})")
        return self

    def with_oauth(self, scope: Optional[str] = None) -> "GrpcClient":
        assert self.auth
        self._token = self.auth.oauth_token(scope=scope)
        return self

    def auth_metadata(self) -> List[Tuple[str, str]]:
        if not self._token:
            return []
        return [("authorization", f"{self._token.token_type} {self._token.access_token}")]

    def stub(self, stub_class):
        """Create a gRPC stub bound to the active channel."""
        if not self._channel:
            raise RuntimeError("Call .connect() first")
        return stub_class(self._channel)

    # ---------- streaming helpers ----------
    @staticmethod
    def collect_server_stream(call: Iterator) -> List:
        """Drain a server-streaming response into a list."""
        return list(call)

    def close(self) -> None:
        if self._channel:
            self._channel.close()
            self._channel = None
