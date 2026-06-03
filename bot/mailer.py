"""메일 발송 — Gmail SMTP(smtplib)로 받은편지함에 실제 발송.

Gmail이 display:flex 등을 버리므로 테이블 기반 HTML 사용 (검증 완료).
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

_TPL = """
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<tr><td align="center" style="padding:24px 12px;">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background-color:#ffffff;border-radius:12px;">
  <tr><td bgcolor="__HCOLOR__" style="padding:22px 26px;border-radius:12px 12px 0 0;">
    <div style="font-size:12px;color:#ffe0e0;text-transform:uppercase;letter-spacing:.5px;">practicket / __ENV__ / 자동 원인분석</div>
    <div style="font-size:20px;font-weight:bold;color:#ffffff;margin-top:6px;">__HEADLINE__</div>
    <div style="margin-top:10px;"><span style="background-color:rgba(0,0,0,.18);color:#ffffff;padding:4px 11px;border-radius:20px;font-size:12px;">__SHORT__</span></div>
  </td></tr>
  <tr><td style="padding:0;border-bottom:1px solid #eeeeee;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td width="50%" align="center" style="padding:16px 4px;border-right:1px solid #f0f0f0;"><div style="font-size:23px;font-weight:bold;color:#b71c1c;">__COUNT__</div><div style="font-size:11px;color:#888888;">발생 건수</div></td>
      <td width="50%" align="center" style="padding:16px 4px;"><div style="font-size:23px;font-weight:bold;color:#b71c1c;">__USERS__</div><div style="font-size:11px;color:#888888;">영향 사용자</div></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:24px 26px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td bgcolor="#fff8e1" style="padding:14px 16px;border-left:4px solid #ffb300;font-size:14px;line-height:1.6;color:#5d4037;"><b>요약 ·</b> __SUMMARY__</td>
    </tr></table>
    <div style="font-size:13px;color:#333;margin:24px 0 10px;font-weight:bold;">근본 원인</div>
    <div style="font-size:13.5px;color:#444;line-height:1.7;">__CAUSE__</div>
    __FIX__
    __BUTTONS__
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;"><tr>
      <td bgcolor="#f5f5f5" style="padding:12px 14px;border-radius:8px;font-size:12.5px;color:#555;line-height:1.8;">__ACTIONS__</td>
    </tr></table>
    <div style="font-size:11px;color:#bbbbbb;margin-top:20px;border-top:1px solid #eee;padding-top:12px;text-align:center;">practicket-sentinel · Sentry 자동 원인분석 파이프라인</div>
  </td></tr>
</table>
</td></tr></table>
"""


def _diff_html(diff):
    """diff 텍스트 → +/- 색상 입힌 HTML(pre)."""
    rows = []
    for ln in diff.splitlines():
        e = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if ln.startswith("+"):
            rows.append(f'<span style="color:#22863a;">{e}</span>')
        elif ln.startswith("-"):
            rows.append(f'<span style="color:#b31d28;">{e}</span>')
        elif ln.startswith("@@"):
            rows.append(f'<span style="color:#6f42c1;">{e}</span>')
        else:
            rows.append(f'<span style="color:#888;">{e}</span>')
    body = "\n".join(rows)
    return ('<pre style="background-color:#f6f8fa;border:1px solid #e1e4e8;padding:12px 14px;'
            'border-radius:8px;font-size:12px;line-height:1.6;overflow-x:auto;margin:8px 0 0;">'
            f'{body}</pre>')


def _fix_section(out):
    if not out.get("fixable"):
        return ""
    summ, diff = out.get("fix_summary"), out.get("diff")
    if not (summ or diff):
        return ""
    html = '<div style="font-size:13px;color:#333;margin:24px 0 10px;font-weight:bold;">적용한 수정</div>'
    if summ:
        html += f'<div style="font-size:13.5px;color:#444;line-height:1.7;">{summ}</div>'
    if diff:
        html += _diff_html(diff)
    return html


def _btn(href, label, color):
    return (f'<td bgcolor="{color}" style="border-radius:8px;">'
            f'<a href="{href}" style="display:inline-block;padding:12px 22px;color:#ffffff;'
            f'font-size:14px;font-weight:bold;text-decoration:none;">{label}</a></td>')


def _render(out, env, sentry_url):
    pr = out.get("pr_url")
    btns = [_btn(sentry_url, "Sentry 이슈 →", "#6c5fc7")]
    if pr:
        btns.insert(0, _btn(pr, "PR 리뷰 →", "#1f883d"))
    buttons = ('<table cellpadding="0" cellspacing="0" border="0" align="center" '
               'style="margin:26px auto 8px;"><tr>'
               + '<td style="width:12px;">&nbsp;</td>'.join(btns) + "</tr></table>")

    if pr:
        actions = ("✅ 원인분석 메일 발송 (본 메일)<br>"
                   f"✅ Draft PR 생성 — base <code>stage</code><br>"
                   "⬜ 사람 리뷰 후 머지 <span style='color:#999;'>(auto-merge 비활성)</span>")
        headline = "코드 수정 PR 자동 생성됨"
        hcolor = "#1f883d"
    else:
        actions = ("✅ 원인분석 메일 발송 (본 메일)<br>"
                   "⚠️ 코드로 자동수정 불가 — <b>사람 확인 필요</b>")
        headline = "원인 분석 (수동 확인 필요)"
        hcolor = "#c62828"

    return (_TPL.replace("__HCOLOR__", hcolor).replace("__ENV__", env)
            .replace("__HEADLINE__", headline).replace("__SHORT__", out["shortId"])
            .replace("__COUNT__", str(out.get("count", "?")))
            .replace("__USERS__", str(out.get("userCount", "?")))
            .replace("__SUMMARY__", out.get("summary", ""))
            .replace("__CAUSE__", out.get("root_cause", ""))
            .replace("__FIX__", _fix_section(out))
            .replace("__BUTTONS__", buttons).replace("__ACTIONS__", actions))


def send(out, cfg, gmail_pass, sentry_url):
    html = _render(out, cfg["sentry"]["environment"], sentry_url)
    icon = "\U0001F7E2" if out.get("pr_url") else "\U0001F534"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{icon} {out['shortId']} · {out.get('summary','')[:50]}"
    msg["From"] = cfg["mail"]["from"]
    msg["To"] = cfg["mail"]["to"]
    plain = f"{out.get('summary','')}\n\n원인: {out.get('root_cause','')}\nPR: {out.get('pr_url')}\nSentry: {sentry_url}"
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg["mail"]["smtp_host"], cfg["mail"]["smtp_port"], context=ctx) as s:
        s.login(cfg["mail"]["from"], gmail_pass)
        s.send_message(msg)
