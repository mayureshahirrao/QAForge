"""
qaforge.api.graphql.client
==========================
GraphQL client based on `gql` (sync transport). Supports queries, mutations,
and subscriptions via `WebsocketsTransport` if needed.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from qaforge.api.auth_manager import AuthManager, AuthToken
from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class GraphQLClient:
    def __init__(self, cfg: Config, auth: Optional[AuthManager] = None):
        self.cfg = cfg
        self.auth = auth
        self._token: Optional[AuthToken] = None
        self._endpoint = cfg.api.graphql.endpoint
        self._client: Optional[Client] = None

    def with_oauth(self, scope: Optional[str] = None) -> "GraphQLClient":
        assert self.auth, "AuthManager required"
        self._token = self.auth.oauth_token(scope=scope)
        self._client = None  # rebuild on next use
        return self

    def _ensure_client(self) -> Client:
        if self._client:
            return self._client
        headers = self._token.header if self._token else {}
        transport = RequestsHTTPTransport(
            url=self._endpoint, headers=headers, retries=2, verify=True
        )
        self._client = Client(transport=transport, fetch_schema_from_transport=False)
        return self._client

    # ---------- operations ----------
    def query(self, document: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        client = self._ensure_client()
        log.debug(f"GraphQL query, vars={variables!r}")
        return client.execute(gql(document), variable_values=variables)

    def mutation(self, document: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Mechanically same as query, but kept distinct for readability in tests.
        return self.query(document, variables)

    def introspect(self) -> Dict[str, Any]:
        return self.query(
            """
            query IntrospectionQuery {
              __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
              }
            }
            """
        )
