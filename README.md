# practicket-sentinel 🛡️

practicket 운영 중 발생하는 **Sentry 에러를 사전탐지 → 원인분석 → 자동 수정/PR → 메일 알림**까지 무인으로 처리하는 파이프라인.

홈서버에서 [Claude Code](https://claude.com/claude-code)를 headless로 1회씩 깨워 분석가로 활용한다. 사람이 터미널에서 하던 "에러 보고 → 코드 읽고 → 원인 찾고 → 고치고 → PR" 과정을 그대로 자동 재생한다.

## 동작 흐름

```
systemd timer (3분마다)
   └─ bot/main.py (1 tick = 1건)
        1. Sentry 조회   (is:unresolved is:unassigned, prod)
        2. 노이즈 필터    (broken pipe·재시작 등 → LLM 안 부름)
        3. 1건 선택 후 assign (claim, 중복 방지)
        4. 컨텍스트 수집  (stacktrace + 소스코드)
        5. claude -p     분석 → 수정 → 빌드 → push → PR
        6. 결과 전달:
             ├─ 📧 Gmail 메일 (원인분석 카드)
             └─ 💬 Sentry 코멘트 (PR 링크)
           실패 시 → unassign + 재시도 카운트 (최대 3회)
```

## 구조

| 경로 | 역할 |
|---|---|
| `bot/main.py` | 오케스트레이터 (폴링·분기) |
| `bot/sentry.py` | Sentry API (조회·assign·코멘트) |
| `bot/filters.py` | 노이즈 규칙 |
| `bot/context.py` | stacktrace → context.json |
| `bot/analyst.py` | `claude -p` 실행 |
| `bot/mailer.py` | Gmail SMTP 발송 (테이블 HTML) |
| `bot/state.py` | 재시도 카운트 |
| `prompts/analyze.md` | claude 지시문 (커밋/PR 컨벤션 포함) |
| `systemd/` | timer + service 유닛 |
| `config.yaml` | 튜닝값 |
| `docs/` | 아키텍처·결정사항·운영 문서 |

## 설치 / 운영

[docs/operations.md](docs/operations.md) 참고.

## 설계 결정

[docs/decisions.md](docs/decisions.md) 참고.
