# zabbix-sms-iran

Send **Zabbix** problem/recovery alerts as **SMS** through Iranian gateways:
**Melipayamak (ملی پیامک)**, **Kavenegar (کاوه نگار)** and **SMS.ir**.

- One small Python 3 script, standard library only (no `pip install`)
- Works with Zabbix 5.4, 6.0 LTS, 6.4 and 7.x (media type *Script*)
- Several recipients per user: `09121111111,09122222222`
- Accepts `+98`, `0098`, `98` and Persian digits (`۰۹۱۲...`)
- Exit code ≠ 0 on failure, so Zabbix shows the error and retries

> ارسال هشدارهای زبیکس با پیامک از طریق سامانه‌های پیامک ایرانی (ملی پیامک، کاوه‌نگار، SMS.ir). [راهنمای فارسی پایین صفحه](#راهنمای-فارسی)

## Install

```bash
# on the Zabbix server (or proxy that sends alerts)
grep ^AlertScriptsPath /etc/zabbix/zabbix_server.conf   # default: /usr/lib/zabbix/alertscripts

sudo curl -fsSL -o /usr/lib/zabbix/alertscripts/zabbix_sms.py \
  https://raw.githubusercontent.com/amissboy/zabbix-sms-iran/main/zabbix_sms.py
sudo chmod 755 /usr/lib/zabbix/alertscripts/zabbix_sms.py

sudo curl -fsSL -o /etc/zabbix/zabbix_sms.ini \
  https://raw.githubusercontent.com/amissboy/zabbix-sms-iran/main/zabbix_sms.ini.example
sudo chown root:zabbix /etc/zabbix/zabbix_sms.ini
sudo chmod 640 /etc/zabbix/zabbix_sms.ini
sudo nano /etc/zabbix/zabbix_sms.ini      # provider + credentials
```

Test as the `zabbix` user:

```bash
sudo -u zabbix /usr/lib/zabbix/alertscripts/zabbix_sms.py 09120000000 "Test from Zabbix" "body"
```

## Zabbix configuration

1. **Alerts → Media types → Create media type**
   - Type: `Script`
   - Script name: `zabbix_sms.py`
   - Script parameters (in this order):
     1. `{ALERT.SENDTO}`
     2. `{ALERT.SUBJECT}`
     3. `{ALERT.MESSAGE}`
2. In **Message templates**, keep the subject short, for example:
   - Problem: `PROBLEM {HOST.NAME}: {EVENT.NAME} ({EVENT.SEVERITY})`
   - Problem recovery: `OK {HOST.NAME}: {EVENT.NAME} ({EVENT.DURATION})`
3. **Users → your user → Media → Add**: type = this media type, Send to = mobile number(s).
4. **Alerts → Actions → Trigger actions**: add an operation *Send message* to that user/group.
   Tip: send SMS only for `High` and `Disaster` severities and use Bale/Telegram/email for the rest.

## Providers

| provider | needed in config | API |
|---|---|---|
| `melipayamak` | `username`, `password`, and `from` (dedicated line) **or** `body_id` (pattern on service line) | `rest.payamak-panel.com/api/SendSMS/SendSMS` / `BaseServiceNumber` |
| `kavenegar` | `api_key`, optional `sender` | `api.kavenegar.com/v1/{key}/sms/send.json` |
| `smsir` | `api_key`, `line_number` | `api.sms.ir/v1/send/bulk` |

**Melipayamak pattern mode:** on the service (shared) line only approved patterns can be sent.
Create a pattern with one variable, e.g. `هشدار زبیکس: {0}`, and put its code in `body_id`.

A different config path can be set with the environment variable `ZBX_SMS_CONF`.

## Troubleshooting

- `config not found` → path or permissions of `/etc/zabbix/zabbix_sms.ini` (user `zabbix` must read it).
- Alert stays *In progress / Failed* → check **Reports → Action log**; the script's stderr is shown there.
- Melipayamak `RetStatus` ≠ 1 → wrong credentials, no credit, or text not matching the pattern.
- The server has no internet access → allow outbound HTTPS to the provider's API host.

---

## راهنمای فارسی

این اسکریپت هشدارهای زبیکس را از طریق سامانه‌ی پیامک ایرانی به موبایل مدیران شبکه می‌فرستد.

۱. فایل `zabbix_sms.py` را در مسیر AlertScriptsPath (معمولاً `/usr/lib/zabbix/alertscripts`) کپی و قابل اجرا کنید.
۲. فایل تنظیمات را در `/etc/zabbix/zabbix_sms.ini` بسازید، سامانه (`provider`) و اطلاعات API را وارد کنید.
۳. در زبیکس یک Media type از نوع **Script** با پارامترهای `{ALERT.SENDTO}`، `{ALERT.SUBJECT}` و `{ALERT.MESSAGE}` بسازید.
۴. در پروفایل کاربر، شماره‌ی موبایل را به‌عنوان Media اضافه کنید و در Action، ارسال پیام را تعریف کنید.

پیشنهاد: پیامک را فقط برای هشدارهای High و Disaster بفرستید و بقیه را به [ربات بله](https://github.com/amissboy/zabbix-bale-bot) یا ایمیل بسپارید.

راه‌اندازی مانیتورینگ و هشداردهی شبکه و سرور: [hermitweb.ir/services/network-monitoring](https://hermitweb.ir/services/network-monitoring/)

## License

MIT © HermitWeb
