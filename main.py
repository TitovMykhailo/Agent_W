"""
main.py — главный запуск Job Hunter Agent

Запуск:
    python main.py

Автозапуск каждые 6 часов (Linux/Mac):
    crontab -e
    0 */6 * * * cd /path/to/job_hunter && python main.py >> logs.txt 2>&1
"""

import os
import json
import datetime

from config import APPLY_THRESHOLD
from parsers import get_all_jobs, prefilter_job
from ai_engine import evaluate_job
from sheets import get_sheets, log_job

SEEN_FILE = "seen_jobs.json"


# ── Дедупликация ──────────────────────────────
def load_seen() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return set()

        data = json.loads(raw)
        if not isinstance(data, list):
            print(f"⚠️  {SEEN_FILE} is not a JSON list. Starting with empty seen set.")
            return set()

        return set(data)
    except json.JSONDecodeError:
        print(f"⚠️  {SEEN_FILE} is invalid JSON. Starting with empty seen set.")
        return set()
    except Exception as e:
        print(f"⚠️  Failed to read {SEEN_FILE}: {e}")
        return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2, ensure_ascii=False)


# ── Главный цикл ──────────────────────────────
def run():
    print("\n" + "═" * 50)
    print(f"🤖 Job Hunter Agent — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 50)

    qualified_sheet, all_sheet = get_sheets()
    seen = load_seen()

    # 1. Собрать вакансии
    all_jobs = get_all_jobs()
    new_jobs = [j for j in all_jobs if (j["url"] or j["title"]) not in seen]
    print(f"   New (unseen): {len(new_jobs)}")

    qualified = 0
    skipped = 0

    # 2. Обработать каждую вакансию
    for job in new_jobs:
        job_id = job["url"] or job["title"]
        seen.add(job_id)

        title = job["title"]
        desc  = job["description"]
        src   = job["source"]
        url   = job["url"]
        contact = job["contact_email"]

        print(f"\n📄 [{src}] {title[:55]}...")

        should_process, filter_reason = prefilter_job(job)
        if not should_process:
            skipped += 1
            print(f"   Filtered — {filter_reason}")
            all_sheet = log_job(all_sheet, {
                "source": src, "title": title, "url": url,
                "score": 0, "status": "Filtered", "notes": filter_reason,
            })
            continue

        # Оценить через AI
        result = evaluate_job(title, desc)
        score  = result.get("score", 0)
        reason = result.get("reason", "")
        apply  = result.get("apply", False)

        print(f"   Score: {score}/10 — {reason[:60]}")

        if not apply or score < APPLY_THRESHOLD:
            skipped += 1
            all_sheet = log_job(all_sheet, {
                "source": src, "title": title, "url": url,
                "score": score,
                "status": "Skipped",
                "notes": reason if apply is False else f"Below threshold (< {APPLY_THRESHOLD})",
            })
            continue

        qualified += 1
        row_data = {
            "source": src, "title": title, "url": url,
            "email_sent": contact or "—",
            "score": score,
            "status": "Qualified ✅",
            "notes": reason,
        }
        all_sheet = log_job(all_sheet, row_data)
        qualified_sheet = log_job(qualified_sheet, row_data)

    save_seen(seen)

    # 3. Проверить ответы
    replies = []

    # 4. Итоговый отчёт
    total = len(new_jobs)
    print(f"\n{'═'*50}")
    print(f"✅ Done! Scanned: {total} | Qualified: {qualified} | Skipped: {skipped} | Replies: {len(replies)}")
    print(f"{'═'*50}\n")


if __name__ == "__main__":
    run()
