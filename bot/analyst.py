"""분석가 — claude 를 headless(-p)로 1회 실행해 분석·수정·PR을 수행시킨다.

claude 가 repo 클론 안에서: 브랜치 생성 → 원인분석 → 코드수정 → 빌드 →
push → gh PR 생성 → out.json 기록. 사람이 터미널에서 하던 일을 무인 재생.
"""
import json
import os
import subprocess


def run(repo_dir, context_path, prompt_path, model, oauth_token, timeout=900):
    """repo_dir 에서 claude 실행 후 out.json(dict) 반환. 실패 시 None."""
    out_path = os.path.join(repo_dir, "out.json")
    if os.path.exists(out_path):
        os.remove(out_path)

    prompt = open(prompt_path, encoding="utf-8").read()
    prompt += (f"\n\ncontext.json 경로는 {context_path} 이다. "
               f"이 지침대로 처리하라. out.json은 현재 디렉토리에 써라.")

    env = dict(os.environ)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")

    subprocess.run(
        ["claude", "-p", prompt, "--model", model, "--dangerously-skip-permissions"],
        cwd=repo_dir, env=env, timeout=timeout,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    if not os.path.exists(out_path):
        return None
    with open(out_path, encoding="utf-8") as f:
        return json.load(f)
