# 설치 / 운영

## 선결 준비물 (토큰 3종)
1. **Claude OAuth** — Mac에서 `claude setup-token` (Max 구독) → `sk-ant-oat...`
2. **GitHub PAT** — fine-grained, repo=`Jeongho0805/practicket`, Contents=RW + Pull requests=RW
3. **Gmail 앱비번** — myaccount.google.com/apppasswords (16자)

## 홈서버 설치

```bash
# 1) claude / gh (유저공간, sudo 불필요)
curl -fsSL https://claude.ai/install.sh | bash
# gh: github 릴리스 tar 받아 ~/.local/bin/gh 배치
export PATH="$HOME/.local/bin:$PATH"

# 2) 레포 clone + venv
cd ~ && git clone https://github.com/Jeongho0805/practicket-sentinel.git
cd practicket-sentinel
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt

# 3) GitHub 인증 (PAT)
printf '%s' "<PAT>" | gh auth login --with-token && gh auth setup-git

# 4) .env 작성 (600)
umask 077
cat > .env <<EOF
SENTRY_ADMIN_TOKEN=...
CLAUDE_CODE_OAUTH_TOKEN=...
GMAIL_APP_PASSWORD=...
EOF

# 5) systemd 등록
sudo cp systemd/practicket-sentinel.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now practicket-sentinel.timer
```

## 운영 명령
```bash
systemctl list-timers practicket-sentinel.timer     # 다음 실행
journalctl -u practicket-sentinel.service -f        # 로그
systemctl start practicket-sentinel.service         # 즉시 1회 실행 (테스트)
systemctl disable --now practicket-sentinel.timer   # 중지
```

## 튜닝
`config.yaml` — 폴링 범위, per_tick, 재시도 한도, 모델, base 브랜치, 수신 메일.

## 트러블슈팅
| 증상 | 원인/조치 |
|---|---|
| push 403 | PAT에 Contents=Read and write 누락 → 권한 추가 |
| claude 인증 실패 | `CLAUDE_CODE_OAUTH_TOKEN` 만료(~1년) → `claude setup-token` 재발급 |
| 같은 이슈 반복 처리 | assign이 안 됨 → Sentry 멤버 해석/권한 확인 |
| 메일 안옴 | 앱비번 오류 / 2단계인증 미설정 |
