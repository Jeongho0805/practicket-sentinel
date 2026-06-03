"""노이즈 필터 — LLM 호출 *전*에 규칙으로 걸러 비용 0으로 버린다.

prod 25개 이슈 분석에서 도출한 패턴:
- 클라이언트 연결 끊김(broken pipe) = 정상 동작
- 앱 재시작 시점 커넥션풀/빈 생명주기 에러 = 일시적 인프라
"""
import re

DROP_TYPES = {
    "ClientAbortException",
    "HttpRequestMethodNotSupportedException",
}

DROP_PATTERNS = [
    r"Broken pipe",
    r"Connection reset by peer",
    r"Connection prematurely closed",
    r"LettuceConnectionFactory has been STOPPED",
    r"Interrupted during connection acquisition",
    r"BeanCreationNotAllowedException",
    r"Redis command interrupted",
]
_RE = [re.compile(p) for p in DROP_PATTERNS]


def is_noise(issue) -> bool:
    title = issue.get("title", "") or ""
    etype = (issue.get("metadata", {}) or {}).get("type", "") or ""
    if etype in DROP_TYPES:
        return True
    return any(rx.search(title) for rx in _RE)
