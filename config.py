# ─────────────────────────────────────────────
# config.py — безопасный шаблон конфигурации
# Реальные секреты держи в config_local.py
# ─────────────────────────────────────────────

BASE_CONFIG = {
    # ── Azure OpenAI ──────────────────────────
    "AZURE_API_KEY": "",
    "AZURE_ENDPOINT": "https://your-resource-name.cognitiveservices.azure.com/",
    "AZURE_API_VERSION": "2025-04-01-preview",
    "AZURE_DEPLOYMENT_MINI": "gpt-5-mini",
    "AZURE_DEPLOYMENT_MAIN": "gpt-5-mini",

    # ── Gmail агента ──────────────────────────
    "GMAIL_ADDRESS": "",
    "GMAIL_APP_PASSWORD": "",

    # ── Google Sheets ─────────────────────────
    "GOOGLE_CREDENTIALS_FILE": "google_credentials.json",
    "SPREADSHEET_NAME": "Job Hunter",

    # ── Telegram уведомления (опционально) ────
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_CHAT_ID": "",

    # ── Твои данные ───────────────────────────
    "YOUR_NAME": "Your Name",
    "YOUR_LOCATION": "Bratislava, Slovakia",
    "YOUR_SKILLS": "Python, AI automation, integrations",
    "YOUR_GITHUB": "https://github.com/your-github-username",
    "YOUR_EMAIL": "your.email@example.com",
}

try:
    from config_local import CONFIG_OVERRIDES  # type: ignore
except ImportError:
    CONFIG_OVERRIDES = {}

CONFIG = BASE_CONFIG.copy()
CONFIG.update(CONFIG_OVERRIDES)

# ── Профиль кандидата для GPT ─────────────────
CANDIDATE_PROFILE = f"""
Name: {CONFIG["YOUR_NAME"]}
Location: {CONFIG["YOUR_LOCATION"]} (remote globally, on-site Slovakia/Ukraine)
Skills: Python, AI agents, n8n, Make, Zapier, ChatGPT API, Claude API,
        Azure OpenAI, prompt engineering, GEO content, automation workflows,
        Gmail SMTP/IMAP, Telegram API, Docker, Linux, Git, Google Sheets
Languages: English (B2), Ukrainian (native), Russian (native), Slovak (B2)
Projects:
  - Autonomous freelance agent (Python + Azure OpenAI + Gmail SMTP/IMAP + Telegram)
  - GEO Content QA Tool (Python + Claude API)
  - n8n content pipeline (RSS → GPT-4o → Telegram)
Education: ICT student at STU FEI Bratislava + CS at Dnipro University of Technology
Looking for: Remote freelance, part-time AI/automation work worldwide,
             full-time jobs in Slovakia
"""

# ── Ключевые слова для фильтрации вакансий ───
KEYWORDS = [
    "python", "ai", "automation", "n8n", "zapier", "make.com", "chatgpt",
    "openai", "claude", "anthropic", "workflow", "freelance", "remote",
    "bot", "scraping", "agent", "llm", "prompt", "gpt", "machine learning",
    "data", "api", "integration", "no-code", "low-code",
    "developer", "engineer", "backend", "frontend", "full stack", "devops",
    "programator", "programátor", "vyvojar", "vývojár", "analytik",
    "konzultant", "data scientist", "java", ".net", "angular"
]

# ── Источники Reddit ──────────────────────────
REDDIT_FEEDS = [
    "https://www.reddit.com/r/forhire/new.json?limit=25",
    "https://www.reddit.com/r/slavelabour/new.json?limit=25",
    "https://www.reddit.com/r/hiring/new.json?limit=25",
    "https://www.reddit.com/r/remotework/new.json?limit=15",
]

# ── RSS/HTML фиды работы в Словакии ───────────
JOBS_SK_RSS = "https://www.jobs.sk/rss/it"
PROFESIA_SK_RSS = "https://www.profesia.sk/rss/it"
PROFESIA_SK_IT_URL = "https://www.profesia.sk/en/work/information-technology/?count_days=7&sort_by=validity_from"
WORKI_SK_IT_URL = "https://www.worki.sk/ponuka-prace/2/it-a-telekomunikacie"

# ── LinkedIn public jobs (guest search) ──────
LINKEDIN_LOCATION = "Slovakia"
LINKEDIN_MAX_RESULTS = 12
LINKEDIN_SEARCH_TERMS = [
    "python developer",
    "ai automation",
    "data engineer",
    "api integration",
]

# ── Порог для отбора (0-10) ───────────────────
APPLY_THRESHOLD = 7
