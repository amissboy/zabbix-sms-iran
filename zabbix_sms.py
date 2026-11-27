#!/usr/bin/env python3
"""
zabbix_sms.py - Send Zabbix alerts as SMS through Iranian SMS gateways.

Supported providers: melipayamak, kavenegar, smsir
No third-party packages: Python 3.6+ standard library only.

Zabbix media type (type: Script), script parameters in this order:
    {ALERT.SENDTO}
    {ALERT.SUBJECT}
    {ALERT.MESSAGE}

Manual test:
    ./zabbix_sms.py 09120000000 "Test subject" "Test message"

https://github.com/amissboy/zabbix-sms-iran  -  MIT License
"""
import configparser
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CONF_PATH = os.environ.get("ZBX_SMS_CONF", "/etc/zabbix/zabbix_sms.ini")
TIMEOUT = 15

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_mobile(raw):
    """Return 09xxxxxxxxx or None."""
    num = re.sub(r"[^\d]", "", raw.translate(FA_DIGITS))
    if num.startswith("0098"):
        num = num[4:]
    elif num.startswith("98") and len(num) == 12:
        num = num[2:]
    if len(num) == 10 and num.startswith("9"):
        num = "0" + num
    return num if re.fullmatch(r"09\d{9}", num) else None


def build_text(subject, message, cfg):
    mode = cfg.get("mode", "subject").lower()
    if mode == "subject":
        text = subject
    elif mode == "message":
        text = message
    else:
        text = subject + "\n" + message
    text = text.replace("\r", "").strip()
    limit = cfg.getint("max_length", 300)
    return text[:limit]


def http_post(url, data=None, headers=None, as_json=False):
    headers = dict(headers or {})
    if as_json:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = urllib.parse.urlencode(data or {}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers.setdefault("Accept", "application/json")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- providers

def send_melipayamak(cfg, mobile, text):
    """Free text from a dedicated line, or a pattern (bodyId) from the service line."""
    base = "https://rest.payamak-panel.com/api/SendSMS/"
    body_id = cfg.get("body_id", "").strip()
    if body_id:
        # Pattern variables are separated by ';' - the whole alert text is variable {0}.
        data = {
            "username": cfg["username"],
            "password": cfg["password"],
            "to": mobile,
            "bodyId": body_id,
            "text": text.replace(";", ","),
        }
        status, out = http_post(base + "BaseServiceNumber", data)
    else:
        data = {
            "username": cfg["username"],
            "password": cfg["password"],
            "to": mobile,
            "from": cfg["from"],
            "text": text,
            "isFlash": "false",
        }
        status, out = http_post(base + "SendSMS", data)
    try:
        ok = json.loads(out).get("RetStatus") == 1
    except ValueError:
        ok = False
    return ok, out


def send_kavenegar(cfg, mobile, text):
    url = "https://api.kavenegar.com/v1/%s/sms/send.json" % urllib.parse.quote(cfg["api_key"])
    data = {"receptor": mobile, "message": text}
    if cfg.get("sender"):
        data["sender"] = cfg["sender"]
    status, out = http_post(url, data)
    try:
        ok = json.loads(out)["return"]["status"] == 200
    except (ValueError, KeyError, TypeError):
        ok = False
    return ok, out


def send_smsir(cfg, mobile, text):
    data = {
        "lineNumber": int(cfg["line_number"]),
        "messageText": text,
        "mobiles": [mobile],
    }
    status, out = http_post(
        "https://api.sms.ir/v1/send/bulk",
        data,
        headers={"X-API-KEY": cfg["api_key"]},
        as_json=True,
    )
    try:
        ok = json.loads(out).get("status") == 1
    except ValueError:
        ok = False
    return ok, out


PROVIDERS = {
    "melipayamak": send_melipayamak,
    "kavenegar": send_kavenegar,
    "smsir": send_smsir,
}


def main(argv):
    if len(argv) < 4:
        print("usage: zabbix_sms.py <mobile[,mobile...]> <subject> <message>", file=sys.stderr)
        return 2
    sendto, subject, message = argv[1], argv[2], argv[3]

    parser = configparser.ConfigParser()
    if not parser.read(CONF_PATH, encoding="utf-8"):
        print("config not found: %s" % CONF_PATH, file=sys.stderr)
        return 2
    if not parser.has_section("general"):
        print("missing [general] section in %s" % CONF_PATH, file=sys.stderr)
        return 2
    general = parser["general"]
    provider = general.get("provider", "").strip().lower()
    if provider not in PROVIDERS or not parser.has_section(provider):
        print("unknown provider or missing [%s] section" % provider, file=sys.stderr)
        return 2
    cfg = parser[provider]
    text = build_text(subject, message, general)

    failed = 0
    for raw in re.split(r"[,\s;]+", sendto):
        if not raw:
            continue
        mobile = normalize_mobile(raw)
        if not mobile:
            print("invalid mobile: %s" % raw, file=sys.stderr)
            failed += 1
            continue
        try:
            ok, out = PROVIDERS[provider](cfg, mobile, text)
        except Exception as e:  # network errors, missing keys
            ok, out = False, repr(e)
        if ok:
            print("sent to %s" % mobile)
        else:
            print("FAILED %s: %s" % (mobile, out[:300]), file=sys.stderr)
            failed += 1
    # Non-zero exit makes Zabbix mark the alert as failed and retry it.
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
