"""Sentry API 클라이언트 — 이슈 조회 / 이벤트 / assign / 코멘트.

중복 관리는 Sentry-native 방식:
- 조회 시 `is:unassigned` 로 필터 → 작업중/완료 이슈 자동 제외
- 처리 시작 시 assign(claim), 실패 시 unassign
"""
import os
import urllib.parse
import requests

BASE = "https://sentry.io/api/0"


class Sentry:
    def __init__(self, org, token=None):
        self.org = org
        self.token = token or os.environ["SENTRY_ADMIN_TOKEN"]
        self.h = {"Authorization": f"Bearer {self.token}"}

    # ---- 조회 ----
    def candidate_issues(self, environment, stats_period="14d", limit=25):
        """미해결 + 미할당(=미처리) 이슈 목록 (prod)."""
        params = {
            "query": "is:unresolved is:unassigned",
            "environment": environment,
            "statsPeriod": stats_period,
            "limit": str(limit),
        }
        url = f"{BASE}/organizations/{self.org}/issues/?{urllib.parse.urlencode(params)}"
        r = requests.get(url, headers=self.h, timeout=30)
        r.raise_for_status()
        return r.json()

    def latest_event(self, issue_id):
        url = f"{BASE}/organizations/{self.org}/issues/{issue_id}/events/latest/"
        r = requests.get(url, headers=self.h, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- 변경 ----
    def assign(self, issue_id, assignee):
        """이메일로 직접 assign (멤버목록 조회 불필요 → member:read 권한 없이 동작)."""
        r = requests.put(f"{BASE}/issues/{issue_id}/", headers=self.h,
                         json={"assignedTo": assignee}, timeout=30)
        r.raise_for_status()
        return r.json()

    def unassign(self, issue_id):
        r = requests.put(f"{BASE}/issues/{issue_id}/", headers=self.h,
                         json={"assignedTo": None}, timeout=30)
        r.raise_for_status()
        return r.json()

    def comment(self, issue_id, text):
        r = requests.post(f"{BASE}/issues/{issue_id}/comments/", headers=self.h,
                          json={"text": text}, timeout=30)
        r.raise_for_status()
        return r.json()
