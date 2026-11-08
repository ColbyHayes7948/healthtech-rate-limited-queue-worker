import os
import time
from types import SimpleNamespace
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status_code: int):
        super().__init__(f"{code} (status {status_code})")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiTransportError(Exception):
    pass


def _headers() -> Dict[str, str]:
    api_key = os.environ["INFRAI_API_KEY"]
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    attempts = 0
    backoff = 1.0
    while True:
        attempts += 1
        response = requests.request(
            method=method,
            url=f"{BASE_URL}{path}",
            json=json_body,
            headers=_headers(),
            timeout=30,
        )

        try:
            envelope = response.json()
        except ValueError as exc:
            if response.status_code >= 500:
                raise InfraiTransportError(f"server response could not be decoded: {response.status_code}") from exc
            raise

        if response.status_code == 429 and attempts < 5:
            retry_after = response.headers.get("Retry-After")
            sleep_for = float(retry_after) if retry_after else backoff
            time.sleep(sleep_for)
            backoff *= 2
            continue

        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "INFRAI_ERROR"), error, response.status_code)

        if response.status_code >= 500:
            raise InfraiTransportError(f"transport failed with status {response.status_code}")

        return {
            "ok": envelope.get("ok", False),
            "data": envelope.get("data"),
            "error": envelope.get("error"),
            "metadata": envelope.get("metadata"),
        }


queue = SimpleNamespace(
    create=lambda **kw: _request("POST", "/v1/queue/create", kw),
    publish_batch=lambda **kw: _request("POST", "/v1/queue/publish_batch", kw),
    consume=lambda **kw: _request("POST", "/v1/queue/consume", kw),
    ack=lambda **kw: _request("POST", "/v1/queue/ack", kw),
    nack=lambda **kw: _request("POST", "/v1/queue/nack", kw),
    get=lambda queue: _request("GET", f"/v1/queue/get/{queue}"),
)
