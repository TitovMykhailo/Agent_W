# 🤖 Job Hunter Agent — Setup Guide

## Что делает агент
- Сначала ищет вакансии на Profesia.sk, Worki.sk и LinkedIn
- Потом добирает Reddit (r/forhire, r/slavelabour, r/hiring, r/remotework)
- Оценивает каждую вакансию через GPT-4o-mini (0-10)
- Отсекает Reddit-посты "ищу работу", случайные обсуждения и senior-only роли
- Записывает всё в Google Sheets:
  - `sheet1` — вакансии со score >= 7, которые прошли фильтры
  - `sheet2` — вообще все найденные вакансии
- Проверяет входящие ответы

---

## Шаг 1 — Установка

```bash
pip install -r requirements.txt
```

---

## Шаг 2 — OpenAI API Key

1. Зайди на https://platform.openai.com/api-keys
2. Create new secret key
3. Вставь данные в `config_local.py`

---

## Шаг 3 — Gmail App Password

1. Зайди в Google аккаунт агента → Security
2. Включи 2-Factor Authentication
3. Найди "App Passwords" → создай для Mail
4. Получишь пароль вида: "xxxx xxxx xxxx xxxx"
5. Вставь его в `CONFIG_OVERRIDES["GMAIL_APP_PASSWORD"]` в `config_local.py` — код сам уберёт пробелы

---

## Шаг 4 — Google Sheets API

1. Зайди на https://console.cloud.google.com
2. Создай новый проект "JobHunter"
3. Включи Google Sheets API + Google Drive API
4. Создай Service Account → скачай JSON credentials
5. Сохрани файл как `google_credentials.json` рядом с `main.py`
6. Создай Google Sheet с названием "Job Hunter"
7. Поделись этим Sheet с email сервис аккаунта (из JSON файла, поле client_email)

---

## Шаг 5 — Запуск

```bash
python main.py
```

### Автозапуск каждые 6 часов (Linux/Mac):
```bash
crontab -e
# Добавь строку:
0 */6 * * * cd /path/to/job_hunter && python main.py >> logs.txt 2>&1
```

### На Windows — Task Scheduler или просто запускай вручную.

---

## Google Sheets колонки

| Date | Source | Title | URL/Contact | Email Sent | From Email | Score | Status | Reply Received | Notes |
|------|--------|-------|-------------|------------|------------|-------|--------|----------------|-------|

---

## Советы

- Запускай 2-3 раза в день
- `sheet1` = только сильные вакансии после фильтров
- `sheet2` = полный лог всех новых вакансий
- seen_jobs.json хранит уже обработанные вакансии — не удаляй
