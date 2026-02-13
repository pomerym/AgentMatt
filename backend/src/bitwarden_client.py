"""
Bitwarden Client

Provides read-only access to Bitwarden via the `bw serve` HTTP API.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BitwardenError(Exception):
    """Raised when Bitwarden lookups fail."""


class BitwardenClient:
    """Simple client for Bitwarden bw serve endpoints."""

    def __init__(self, base_url: str, cache_ttl: int = 30, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self._item_cache: Dict[str, Dict[str, Any]] = {}

    def _request_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)

    def list_items(self, search: str) -> List[Dict[str, Any]]:
        response = self._request_json("/list/object/items", {"search": search})
        # Bitwarden API returns {"success": true, "data": {"object": "list", "data": [...]}}
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            if isinstance(data, dict):
                return data.get("data", [])
        return []

    def get_item_by_name(self, name: str) -> Dict[str, Any]:
        cached = self._item_cache.get(name)
        if cached and time.time() - cached.get("fetched_at", 0) < self.cache_ttl:
            return cached["item"]

        items = self.list_items(name)
        if not items:
            raise BitwardenError(f"Bitwarden item not found: {name}")

        exact = [item for item in items if item.get("name") == name]
        item = exact[0] if exact else items[0]
        if len(items) > 1 and not exact:
            logger.warning("Multiple Bitwarden items matched '%s'; using first", name)

        self._item_cache[name] = {"item": item, "fetched_at": time.time()}
        return item

    def get_field_value(self, item: Dict[str, Any], field: str) -> Optional[str]:
        if field == "notes":
            return item.get("notes")

        login = item.get("login") or {}
        if field == "username":
            return login.get("username")
        if field == "password":
            return login.get("password")
        if field == "uri":
            uris = login.get("uris") or []
            if uris:
                return uris[0].get("uri")

        for entry in item.get("fields", []) or []:
            if entry.get("name") == field:
                return entry.get("value")

        return None

    def get_secret(self, item_name: str, field: str) -> str:
        item = self.get_item_by_name(item_name)
        value = self.get_field_value(item, field)
        if value is None:
            raise BitwardenError(f"Field '{field}' not found on Bitwarden item '{item_name}'")
        return value
