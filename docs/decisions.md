# 설계 결정사항

| 항목 | 결정 | 이유 |
|---|---|---|
| 트리거 | **폴링** (systemd timer 3분) | 외부 엔드포인트 노출 없음, 단순, 유실 없음. webhook은 즉시 200+백그라운드 분리가 필요해 과함 |
| 한 tick 처리량 | **1건** | 동시 claude 방지, 부하·사용량 자연 분산. 백로그는 여러 tick에 걸쳐 소화 |
| 중복 관리 | **Sentry-native** (assign + 코멘트) | redis 불필요(클러스터 내부라 부적합). `is:unassigned`로 작업중/완료 자동 제외. Sentry UI에 감사추적 남음 |
| 멱등성 | 시작 시 **assign(claim)**, 실패 시 **unassign** | 크래시/중복 방지 + 자동 재시도 |
| 재시도 | 로컬 `state.json`, **3회 초과 시 포기** | poison 이슈 무한루프 방지 |
| 분석 모델 | `claude-sonnet-4-6` 단일 | triage(haiku) 없이도 충분, 단순 |
| 인증 | **claude setup-token (Max 구독)** | API 키 추가비용 0. Mac 인터랙티브 로그인과 토큰 별개라 충돌 없음 |
| 로그 소스 | **stacktrace + 소스코드만** (k3s/Loki 제외) | 대부분 stacktrace로 진단 충분. Loki는 내부 ClusterIP라 접근 부가작업 필요 → 나중에 Grafana 프록시로 추가 가능 |
| PR | base `stage`, **draft, auto-merge 금지** | feature→stage→master 플로우 준수, 사람 리뷰 필수 |
| assign 대상 | 본인(Jeongho0805) | 단순 |
| 메일 | Gmail SMTP(smtplib), **테이블 HTML** | 받은편지함 실제 발송. Gmail이 flex 버려서 테이블 레이아웃 |
| 커밋/PR 컨벤션 | 한글 + Conventional 접두사, **Co-Authored-By/Generated 푸터 금지** | 전역 CLAUDE.md 규칙. 홈서버 claude는 이를 모르므로 `prompts/analyze.md`에 명시 |

## 보류 / 향후
- **release=git SHA 매핑**: 현재 이미지 태그가 타임스탬프라 정확한 배포 커밋 역추적 불가. master HEAD 기준 분석으로 충분하나, Sentry release를 SHA로 박으면 정확도↑ (suspect commit 연동)
- **Loki 로그 컨텍스트**: Grafana 프록시 경유로 추가 가능 (`bot/context.py`에 플러그인)
- **webhook 전환**: 실시간 필요 시
