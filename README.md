# Job Hunter Agent Setup Guide

## What the agent does
- Searches jobs on Profesia.sk, Worki.sk, LinkedIn, Jobs.sk, and Reddit
- Filters out low-signal posts such as:
  - candidate "for hire" posts
  - general Reddit discussions/questions
  - senior-only roles and postings with strong seniority mismatch
- Scores each job with Azure OpenAI on a 0-10 scale
- Writes results to Google Sheets:
  - `sheet1` (the first worksheet): jobs that passed filters and scored `>= 7`
  - `Sheet2`: all newly discovered jobs, including filtered and skipped ones
- Tracks processed jobs in `seen_jobs.json` to avoid duplicates

## Step 1 - Install dependencies

```bash
pip install -r requirements.txt
```

## Step 2 - Configure secrets

Keep real secrets in `config_local.py`. The committed `config.py` is only a safe template.

Example:

```python
CONFIG_OVERRIDES = {
    "AZURE_API_KEY": "your-key",
    "GMAIL_ADDRESS": "your.email@gmail.com",
    "GMAIL_APP_PASSWORD": "xxxx xxxx xxxx xxxx",
}
```

## Step 3 - OpenAI / Azure OpenAI

1. Create or use an Azure OpenAI resource
2. Copy the key and endpoint into `config_local.py`
3. Set the deployment names used by the app:
   - `AZURE_DEPLOYMENT_MINI`
   - `AZURE_DEPLOYMENT_MAIN`

## Step 4 - Gmail App Password

1. Open your Google account security settings
2. Enable 2-Factor Authentication
3. Open `App Passwords`
4. Create an app password for Mail
5. Put it into `CONFIG_OVERRIDES["GMAIL_APP_PASSWORD"]` in `config_local.py`

The code removes spaces automatically, so both of these formats work:
- `abcd efgh ijkl mnop`
- `abcdefghijklmnop`

## Step 5 - Google Sheets API

1. Go to https://console.cloud.google.com
2. Create a project
3. Enable:
   - Google Sheets API
   - Google Drive API
4. Create a Service Account
5. Download the JSON credentials file
6. Save it as `google_credentials.json` next to `main.py`
7. Create a Google Sheet named `Job Hunter`
8. Share that sheet with the service account email from the JSON file (`client_email`)

## Step 6 - Run

```bash
python main.py
```

### Auto-run every 6 hours on Linux or Mac

```bash
crontab -e
# Add:
0 */6 * * * cd /path/to/job_hunter && python main.py >> logs.txt 2>&1
```

### Windows

Use Task Scheduler or run the script manually.

## Google Sheets columns

| Date | Source | Title | URL/Contact | Email Sent | From Email | Score | Status | Reply Received | Notes |
|------|--------|-------|-------------|------------|------------|-------|--------|----------------|-------|

## Notes

- Run it 2-3 times per day for best coverage
- `sheet1` contains only qualified jobs after filtering
- `Sheet2` is the full log of all newly processed jobs
- Do not delete `seen_jobs.json` unless you want to reprocess existing jobs
- Gmail reply checking is currently disabled in `main.py`
