"""
telegram_notify.py — уведомления в Telegram
"""

import html

import requests
from config import CONFIG


def send(message: str):
    """Отправляет сообщение в Telegram"""
    token   = CONFIG.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = CONFIG.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        return  # Telegram не настроен — пропускаем

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id":    chat_id,
            "text":       message,
            "parse_mode": "HTML",
        }, timeout=10)
    except Exception as e:
        print(f"⚠️  Telegram error: {e}")


def report(scanned: int, suggested: int, skipped: int, replies: int):
    """Отправляет итоговый отчёт"""
    send(
        f"🤖 <b>Job Hunter Report</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 Scanned:  {scanned}\n"
        f"🎯 Suggested: {suggested}\n"
        f"⏭️  Skipped:  {skipped}\n"
        f"📨 Replies:  {replies}\n"
    )


def new_reply(from_email: str, subject: str):
    """Уведомление о новом ответе"""
    send(
        f"📨 <b>New Reply!</b>\n"
        f"From: {from_email}\n"
        f"Subject: {subject}"
    )


def job_suggestion(
    *,
    source: str,
    title: str,
    url: str,
    score: int,
    contact_channel: str,
    contact_value: str,
    buffered_days: int,
    price_amount: int,
    price_currency: str,
    reason: str,
    message: str,
):
    """Отправляет в Telegram вакансию, по которой стоит написать вручную"""
    safe_reason = html.escape(reason or "")
    safe_message = html.escape(message or "")
    safe_title = html.escape(title or "")
    safe_source = html.escape(source or "")
    safe_channel = html.escape(contact_channel or "unknown")
    safe_contact = html.escape(contact_value or "manual")
    safe_url = html.escape(url or "")

    send(
        f"🎯 <b>Стоит написать</b>\n"
        f"Source: {safe_source}\n"
        f"Title: {safe_title}\n"
        f"Score: {score}/10\n"
        f"Channel: {safe_channel}\n"
        f"Contact: {safe_contact}\n"
        f"Timeline: {buffered_days} days\n"
        f"Price: {price_amount} {html.escape(price_currency)}\n"
        f"Why: {safe_reason}\n"
        f"URL: {safe_url}\n\n"
        f"<b>Suggested message</b>\n"
        f"<pre>{safe_message}</pre>"
    )
