"""로컬 상태 — 재시도 횟수만 추적 (중복관리는 Sentry assign이 담당).

state.json 예: { "7138628062": {"attempts": 2, "last": "..."} }
"""
import json
import os

PATH = os.path.join(os.path.dirname(__file__), "..", "state.json")


def _load():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save(d):
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def attempts(issue_id):
    return _load().get(str(issue_id), {}).get("attempts", 0)


def bump(issue_id, when):
    d = _load()
    rec = d.setdefault(str(issue_id), {"attempts": 0})
    rec["attempts"] += 1
    rec["last"] = when
    _save(d)
