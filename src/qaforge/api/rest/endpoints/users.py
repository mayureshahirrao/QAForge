"""
qaforge.api.rest.endpoints.users
================================
Domain-specific wrapper around `RestClient` for the /users endpoints.
Keeps step definitions short and readable.
"""
from __future__ import annotations

from typing import Any, Dict

import httpx

from qaforge.api.rest.client import RestClient


class UsersAPI:
    BASE = "/users"

    def __init__(self, client: RestClient):
        self.client = client

    def list_users(self, page: int = 1, limit: int = 20) -> httpx.Response:
        return self.client.get(self.BASE, params={"page": page, "limit": limit})

    def get_user(self, user_id: str) -> httpx.Response:
        return self.client.get(f"{self.BASE}/{user_id}")

    def create_user(self, payload: Dict[str, Any]) -> httpx.Response:
        return self.client.post(self.BASE, json=payload)

    def update_user(self, user_id: str, payload: Dict[str, Any]) -> httpx.Response:
        return self.client.patch(f"{self.BASE}/{user_id}", json=payload)

    def delete_user(self, user_id: str) -> httpx.Response:
        return self.client.delete(f"{self.BASE}/{user_id}")
