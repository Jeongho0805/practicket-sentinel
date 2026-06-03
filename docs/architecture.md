# 아키텍처

## 실행 위치
모두 홈서버 hoya(k3s 단일노드)의 **호스트**에서 동작. k3s 파드가 아니라 호스트 systemd 서비스 —
claude·git·gh·gradle를 자유롭게 쓰기 위함.

```
홈서버 hoya
├── ~/.local/bin/claude, gh            # 유저공간 설치
├── /home/hoya/practicket-sentinel/    # 이 레포 (봇 코드)
│   ├── bot/, prompts/, config.yaml
│   ├── .env                           # 토큰 (git 제외, 600)
│   ├── venv/                          # python 가상환경
│   ├── work/                          # 분석용 practicket 클론 (git 제외)
│   └── state.json                     # 재시도 카운트 (git 제외)
└── /etc/systemd/system/
    ├── practicket-sentinel.service
    └── practicket-sentinel.timer
```

## 생명주기
| 구성 | 상태 |
|---|---|
| timer | 항상 (시계 역할, 토큰 0) |
| main.py | 3분마다 깼다 종료 (보통 1초) |
| claude | 진짜 버그 있을 때만 떴다 종료 (~2-5분) |

## 한 tick 시퀀스
```
1. Sentry 조회 (is:unresolved is:unassigned environment:prod)
2. filters.is_noise() 로 노이즈 제거
3. state.attempts < 3 인 것만 → per_tick(1)건 선택
4. sentry.assign() 로 claim
5. ensure_repo(): work/ 클론 fetch + stage 리셋
6. context.build() → context.json
7. analyst.run(): claude -p (브랜치·수정·빌드·push·gh PR·out.json)
8. mailer.send() + sentry.comment(PR링크)
   예외 → sentry.unassign() + state.bump()
```

## 데이터 소스
- **Sentry API**: 이슈 목록, latest event(stacktrace/request/tags)
- **git**: `work/` 클론의 실제 소스 (배포 코드 ≈ stage/master HEAD)
- (제외) k3s/Loki 로그 — 향후 Grafana 프록시로 추가 가능

## 인증
- `CLAUDE_CODE_OAUTH_TOKEN` (Max 구독, setup-token)
- `SENTRY_ADMIN_TOKEN` (read)
- `GMAIL_APP_PASSWORD` (SMTP)
- GitHub: `gh auth login --with-token` (fine-grained PAT, practicket repo, Contents+PR write)
