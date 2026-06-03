"""Sentry 이슈/이벤트 → claude가 읽을 context.json 으로 정리."""
import json


def build(issue, event):
    excs, req = [], {}
    for e in event.get("entries", []):
        if e["type"] == "exception":
            for v in e["data"].get("values", []):
                frames = [
                    {"module": f.get("module"), "function": f.get("function"),
                     "file": f.get("filename"), "line": f.get("lineNo")}
                    for f in (v.get("stacktrace") or {}).get("frames", [])
                    if f.get("inApp")
                ]
                excs.append({"type": v.get("type"),
                             "value": str(v.get("value"))[:300],
                             "frames": frames})
        elif e["type"] == "request":
            req = {"method": e["data"].get("method"), "url": e["data"].get("url")}

    tags = {t["key"]: t["value"] for t in event.get("tags", [])}
    return {
        "shortId": issue["shortId"],
        "title": issue["title"],
        "count": issue.get("count"),
        "userCount": issue.get("userCount"),
        "environment": tags.get("environment"),
        "transaction": tags.get("transaction"),
        "request": req,
        "exceptions": excs,
        "permalink": issue.get("permalink"),
    }


def write(ctx, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
