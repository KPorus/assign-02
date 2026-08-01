#!/usr/bin/env python3
"""
Live API smoke tests against a running Blog API.

Usage:
  # API must already be up (docker compose or uvicorn)
  python3 scripts/test_api.py
  python3 scripts/test_api.py --base-url http://127.0.0.1:8000

Uses only the Python standard library (no httpx/requests required).
"""

from __future__ import annotations

import argparse
import json
import uuid
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PASSED = 0
FAILED = 0


def ok(name: str) -> None:
    global PASSED
    PASSED += 1
    print(f"  PASS  {name}")


def fail(name: str, detail: str) -> None:
    global FAILED
    FAILED += 1
    print(f"  FAIL  {name}: {detail}")


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | list[Any] | None, str]:
    data: bytes | None = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason)) from exc

    parsed: dict[str, Any] | list[Any] | None
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = None
    return status, parsed, raw


def expect_status(name: str, status: int, expected: int, raw: str) -> bool:
    if status == expected:
        ok(f"{name} [{expected}]")
        return True
    fail(name, f"expected {expected}, got {status}: {raw[:300]}")
    return False


def as_dict(body: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
    return body if isinstance(body, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Blog API smoke tests")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    suffix = uuid.uuid4().hex[:8]
    username = f"tester_{suffix}"
    email = f"tester_{suffix}@example.com"
    password = "secret123"
    token: str | None = None
    user_id: str | None = None
    post_id: int | None = None

    print(f"\nTesting API at {base}")
    print(f"Temp user: {email}\n")

    print("Public")
    status, body, raw = request("GET", f"{base}/health")
    if expect_status("GET /health", status, 200, raw):
        if as_dict(body).get("success") is True:
            ok("GET /health success=true")
        else:
            fail("GET /health success=true", raw[:200])

    status, body, raw = request("GET", f"{base}/public/info")
    if expect_status("GET /public/info", status, 200, raw):
        expected_msg = "Welcome stranger! This info is public."
        if as_dict(body).get("message") == expected_msg:
            ok("GET /public/info message")
        else:
            fail("GET /public/info message", raw[:200])

    status, _, raw = request("GET", f"{base}/users/me")
    expect_status("GET /users/me without token", status, 401, raw)

    print("\nAuth / users")
    status, body, raw = request(
        "POST",
        f"{base}/users/create",
        json_body={"username": username, "email": email, "password": password},
    )
    if expect_status("POST /users/create", status, 201, raw):
        data = as_dict(body).get("data") or {}
        user_id = data.get("id") if isinstance(data, dict) else None
        if user_id:
            ok(f"created user_id={user_id}")
        else:
            fail("created user_id", raw[:200])

    status, body, raw = request(
        "POST",
        f"{base}/auth/login",
        json_body={"email": email, "password": password},
    )
    if expect_status("POST /auth/login", status, 200, raw):
        data = as_dict(body).get("data") or {}
        token = data.get("access_token") if isinstance(data, dict) else None
        if token:
            ok("login returned access_token")
        else:
            fail("login access_token", raw[:200])

    if not token:
        print("\nCannot continue without token.")
        print(f"\nResult: {PASSED} passed, {FAILED} failed")
        return 1

    auth = {"Authorization": f"Bearer {token}"}

    status, body, raw = request("GET", f"{base}/users/me", headers=auth)
    if expect_status("GET /users/me", status, 200, raw):
        data = as_dict(body).get("data") or {}
        if isinstance(data, dict) and data.get("email") == email:
            ok("profile email matches")
        else:
            fail("profile email matches", raw[:200])

    if user_id:
        status, _, raw = request(
            "PUT",
            f"{base}/users/update/{user_id}",
            headers=auth,
            json_body={"username": f"{username}_u"},
        )
        expect_status("PUT /users/update/{id}", status, 200, raw)

    print("\nPosts")
    status, body, raw = request(
        "POST",
        f"{base}/posts",
        headers=auth,
        json_body={"title": f"Hello {suffix}", "description": "api test post"},
    )
    if expect_status("POST /posts", status, 201, raw):
        data = as_dict(body).get("data") or {}
        post_id = data.get("id") if isinstance(data, dict) else None
        if post_id:
            ok(f"created post_id={post_id}")
        else:
            fail("created post_id", raw[:200])

    status, _, raw = request("GET", f"{base}/posts")
    expect_status("GET /posts", status, 200, raw)

    search_url = f"{base}/posts/search?{urllib.parse.urlencode({'q': suffix, 'page': 1, 'page_size': 10})}"
    status, body, raw = request("GET", search_url)
    if expect_status("GET /posts/search", status, 200, raw):
        data = as_dict(body).get("data") or {}
        total = data.get("total") if isinstance(data, dict) else None
        if isinstance(total, int) and total >= 1:
            ok("search found test post")
        else:
            fail("search found test post", raw[:200])

    if post_id:
        status, _, raw = request("GET", f"{base}/posts/{post_id}")
        expect_status("GET /posts/{id}", status, 200, raw)

        status, _, raw = request(
            "PUT",
            f"{base}/posts/{post_id}",
            headers=auth,
            json_body={"title": f"Updated {suffix}", "description": "updated"},
        )
        expect_status("PUT /posts/{id}", status, 200, raw)

        status, _, raw = request("DELETE", f"{base}/posts/{post_id}", headers=auth)
        expect_status("DELETE /posts/{id}", status, 200, raw)

    print("\nLogout")
    status, _, raw = request("POST", f"{base}/auth/logout", headers=auth)
    expect_status("POST /auth/logout", status, 200, raw)

    print("\nCleanup")
    status, body, raw = request(
        "POST",
        f"{base}/auth/login",
        json_body={"email": email, "password": password},
    )
    if status == 200:
        data = as_dict(body).get("data") or {}
        new_token = data.get("access_token") if isinstance(data, dict) else None
        if new_token and user_id:
            status, _, raw = request(
                "DELETE",
                f"{base}/users/delete/{user_id}",
                headers={"Authorization": f"Bearer {new_token}"},
            )
            expect_status("DELETE /users/delete/{id}", status, 200, raw)
        else:
            fail("cleanup login token", "missing token after re-login")
    else:
        fail("cleanup re-login", f"status {status}: {raw[:200]}")

    print(f"\nResult: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConnectionError as exc:
        print(f"\nCould not connect to API: {exc}")
        print("Start the server first, e.g. docker compose up --build")
        raise SystemExit(2) from exc
