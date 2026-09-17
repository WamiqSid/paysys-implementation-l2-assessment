from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("minipay.support")


class SupportClientError(Exception):
    def __init__(self, message: str, exit_code: int = 3):
        super().__init__(message)
        self.exit_code = exit_code


class MiniPayClient:
    def __init__(self, base_url: str, api_key: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Accept": "application/json"}

    def request(self, method: str, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(method, url, headers=self._headers(), timeout=self.timeout)
        except httpx.TimeoutException as exc:
            raise SupportClientError(f"timeout calling {url}", 3) from exc
        except httpx.HTTPError as exc:
            raise SupportClientError(f"cannot reach API {url}: {exc}", 3) from exc
        if response.status_code == 401:
            raise SupportClientError("API authentication failed", 3)
        if response.status_code == 404:
            raise SupportClientError("not found", 1)
        if response.status_code >= 500:
            raise SupportClientError(f"API error {response.status_code}: {response.text}", 3)
        if response.status_code >= 400:
            raise SupportClientError(f"API rejected request ({response.status_code}): {response.text}", 3)
        return response.json()

    def health(self) -> dict[str, Any]:
        live = self.request("GET", "/live")
        try:
            full = self.request("GET", "/api/ops/health")
        except SupportClientError:
            full = {"api": live.get("status"), "database": "unknown"}
        return {"live": live, "ops": full}

    def search(self, transaction_ref: str) -> dict[str, Any]:
        return self.request("GET", f"/api/search?q={transaction_ref}")

    def stuck(self, minutes: int = 15) -> list[dict[str, Any]]:
        return self.request("GET", f"/api/ops/stuck?minutes={minutes}")

    def failed(self) -> list[dict[str, Any]]:
        return self.request("GET", "/api/ops/failed")
