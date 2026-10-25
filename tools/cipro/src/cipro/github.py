"""Minimal GitHub REST client (stdlib only) with an injectable transport for tests."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self):
        return json.loads(self.body.decode("utf-8"))


Transport = Callable[[str, dict[str, str]], Response]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def urllib_transport(url: str, headers: dict[str, str]) -> Response:  # pragma: no cover - network
    req = urllib.request.Request(url, headers=headers)
    try:
        with _opener.open(req, timeout=60) as r:
            return Response(r.status, {k.lower(): v for k, v in r.headers.items()}, r.read())
    except urllib.error.HTTPError as e:
        return Response(e.code, {k.lower(): v for k, v in e.headers.items()}, e.read())


def resolve_token() -> str | None:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


class GitHubError(RuntimeError):
    pass


class GitHub:
    def __init__(
        self,
        repo: str,
        token: str | None = None,
        transport: Transport = urllib_transport,
        base: str = "https://api.github.com",
        max_retries: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if repo.count("/") != 1:
            raise ValueError("repo must be OWNER/NAME")
        self.repo = repo
        self.token = token
        self.transport = transport
        self.base = base.rstrip("/")
        self.max_retries = max_retries
        self.sleep = sleep

    def _headers(self, api: bool = True) -> dict[str, str]:
        h = {"User-Agent": "cipro/0.1"}
        if api:
            h["Accept"] = "application/vnd.github+json"
            h["X-GitHub-Api-Version"] = "2022-11-28"
            if self.token:
                h["Authorization"] = f"Bearer {self.token}"
        return h

    def url(self, path: str, params: dict | None = None) -> str:
        u = f"{self.base}/repos/{self.repo}/{path.lstrip('/')}"
        if params:
            u += "?" + urllib.parse.urlencode(params)
        return u

    def request(self, url: str, api: bool = True) -> Response:
        delay = 2.0
        r = self.transport(url, self._headers(api))
        for _ in range(self.max_retries):
            retryable = r.status >= 500 or r.status == 429 or (
                r.status == 403 and r.headers.get("x-ratelimit-remaining") == "0"
            )
            if not retryable:
                break
            self.sleep(delay)
            delay *= 2
            r = self.transport(url, self._headers(api))
        return r

    def get(self, path: str, params: dict | None = None):
        r = self.request(self.url(path, params))
        if r.status != 200:
            raise GitHubError(f"GET {path} -> {r.status}: {r.body[:200]!r}")
        return r.json()

    def paginate(
        self, path: str, key: str, params: dict | None = None, limit: int | None = None
    ) -> Iterator[dict]:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        page = 1
        seen = 0
        while True:
            params["page"] = page
            data = self.get(path, params)
            items = data.get(key, [])
            for item in items:
                yield item
                seen += 1
                if limit is not None and seen >= limit:
                    return
            if len(items) < params["per_page"]:
                return
            page += 1

    # ---- endpoints used by cipro
    def workflow_runs(
        self, workflow: str, branch: str | None = None, limit: int | None = None, created: str | None = None
    ) -> Iterator[dict]:
        params: dict = {"status": "completed"}
        if branch:
            params["branch"] = branch
        if created:
            params["created"] = created
        return self.paginate(f"actions/workflows/{workflow}/runs", "workflow_runs", params, limit)

    def run_jobs(self, run_id: int) -> list[dict]:
        return list(self.paginate(f"actions/runs/{run_id}/jobs", "jobs"))

    def run_timing(self, run_id: int) -> dict | None:
        r = self.request(self.url(f"actions/runs/{run_id}/timing"))
        return r.json() if r.status == 200 else None

    def job_log(self, job_id: int) -> str | None:
        r = self.request(self.url(f"actions/jobs/{job_id}/logs"))
        if r.status in (301, 302, 303, 307, 308) and "location" in r.headers:
            # Follow the signed redirect WITHOUT the API token.
            r = self.request(r.headers["location"], api=False)
        if r.status != 200:
            return None
        return r.body.decode("utf-8", errors="replace")
