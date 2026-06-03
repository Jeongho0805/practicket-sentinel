#!/usr/bin/env python3
"""practicket-sentinel 오케스트레이터.

systemd timer가 주기적으로 1회 실행. 한 tick 흐름:
  Sentry 조회(미해결·미할당) → 노이즈 필터 → 1건 선택
  → assign(claim) → 컨텍스트 수집 → claude 분석/수정/PR
  → 메일 + Sentry 코멘트 / 실패 시 unassign + 재시도 카운트
"""
import datetime
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import context as ctxmod      # noqa: E402
import filters                # noqa: E402
import mailer                 # noqa: E402
import state                  # noqa: E402
from analyst import run as run_claude   # noqa: E402
from sentry import Sentry     # noqa: E402


def log(msg):
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def sh(args, cwd):
    subprocess.run(args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _diff(repo, max_chars=1400):
    """HEAD 커밋의 변경 diff에서 메타 헤더를 빼고 +/- 위주로 정리."""
    r = subprocess.run(["git", "show", "HEAD", "-U2", "--format="],
                       cwd=repo, capture_output=True, text=True)
    keep = []
    for ln in r.stdout.splitlines():
        if ln.startswith(("diff --git", "index ", "--- ", "+++ ", "new file", "deleted file")):
            continue
        keep.append(ln)
    return "\n".join(keep)[:max_chars]


def ensure_repo(cfg):
    """분석용 practicket 클론 준비 + stage 최신화."""
    repo = os.path.join(ROOT, "work")
    if not os.path.isdir(os.path.join(repo, ".git")):
        os.makedirs(ROOT, exist_ok=True)
        sh(["git", "clone", f"https://github.com/{cfg['github']['repo']}.git", repo], ROOT)
        sh(["git", "config", "user.name", "jeongho"], repo)
        sh(["git", "config", "user.email", cfg["mail"]["from"]], repo)
    sh(["git", "fetch", "-q", "origin"], repo)
    base = cfg["github"]["base_branch"]
    sh(["git", "switch", "-C", base, f"origin/{base}"], repo)   # 깨끗한 상태로 리셋
    return repo


def main():
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml")))
    oauth = os.environ["CLAUDE_CODE_OAUTH_TOKEN"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    sentry = Sentry(cfg["sentry"]["org"])

    issues = sentry.candidate_issues(
        cfg["sentry"]["environment"], cfg["sentry"]["stats_period"],
        cfg["sentry"]["issue_limit"])
    issues = [i for i in issues if not filters.is_noise(i)]
    issues = [i for i in issues if state.attempts(i["id"]) < cfg["poll"]["max_retries"]]

    if not issues:
        log("처리할 신규 이슈 없음")
        return

    for issue in issues[: cfg["poll"]["per_tick"]]:
        iid, short = issue["id"], issue["shortId"]
        log(f"처리 시작: {short} ({issue.get('count')}건)")
        now = datetime.datetime.now().isoformat(timespec="seconds")
        sentry.assign(iid, cfg["github"]["assignee"])          # claim
        try:
            event = sentry.latest_event(iid)
            repo = ensure_repo(cfg)
            ctx = ctxmod.build(issue, event)
            ctx_path = os.path.join(ROOT, "context.json")
            ctxmod.write(ctx, ctx_path)

            out = run_claude(repo, ctx_path, os.path.join(ROOT, "prompts", "analyze.md"),
                             cfg["analysis"]["model"], oauth)
            if out is None:
                raise RuntimeError("claude가 out.json을 생성하지 못함")

            out.setdefault("count", issue.get("count"))
            out.setdefault("userCount", issue.get("userCount"))
            if out.get("pr_url"):
                out["diff"] = _diff(repo)
            sentry_url = issue.get("permalink", "")
            mailer.send(out, cfg, gmail_pass, sentry_url)

            if out.get("pr_url"):
                sentry.comment(iid, f"🤖 자동 분석 완료 · 수정 PR: {out['pr_url']}")
                log(f"완료: {short} → PR {out['pr_url']}")
            else:
                sentry.comment(iid, "🤖 자동 분석 완료 · 코드 자동수정 불가, 사람 확인 필요")
                log(f"분석만 완료: {short} (PR 없음)")
        except Exception as e:           # noqa: BLE001
            sentry.unassign(iid)         # 다음 tick 재시도 가능하게
            state.bump(iid, now)
            log(f"실패: {short} → unassign, 재시도 {state.attempts(iid)}/{cfg['poll']['max_retries']} ({e})")


if __name__ == "__main__":
    main()
