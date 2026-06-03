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
        self._member_id = None

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

    # ---- 멤버(assign 대상) 해석 ----
    def _resolve_member(self, username_or_email):
        """assignee 문자열 → 'user:<id>' actor 문자열로 변환."""
        if self._member_id:
            return self._member_id
        url = f"{BASE}/organizations/{self.org}/members/?per_page=100"
        r = requests.get(url, headers=self.h, timeout=30)
        r.raise_for_status()
        key = username_or_email.lower()
        for m in r.json():
            u = m.get("user") or {}
            if key in (str(m.get("email", "")).lower(),
                       str(u.get("username", "")).lower(),
                       str(u.get("email", "")).lower()):
                self._member_id = f"user:{u.get('id') or m.get('id')}"
                return self._member_id
        # 못 찾으면 원문 그대로 시도 (Sentry가 username 해석)
        return username_or_email

    # ---- 변경 ----
    def assign(self, issue_id, assignee):
        actor = self._resolve_member(assignee)
        r = requests.put(f"{BASE}/issues/{issue_id}/", headers=self.h,
                         json={"assignedTo": actor}, timeout=30)
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
