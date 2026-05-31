"""
sheets.py - write results to Google Sheets
"""

import datetime
from typing import Optional

from google.oauth2.service_account import Credentials
import gspread
from config import CONFIG

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Date", "Source", "Title", "URL / Contact",
    "Email Sent To", "From Email", "Score (0-10)",
    "Status", "Reply Received", "Notes"
]

SHEETS_TIMEOUT = (10, 20)
ALL_JOBS_SHEET_TITLE = "Sheet2"


def _build_row(data: dict) -> list:
    return [
        data.get("date",        datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        data.get("source",      ""),
        data.get("title",       ""),
        data.get("url",         ""),
        data.get("email_sent",  "—"),
        CONFIG["GMAIL_ADDRESS"],
        data.get("score",       ""),
        data.get("status",      ""),
        data.get("reply",       "No"),
        data.get("notes",       ""),
    ]


def _open_spreadsheet() -> Optional[gspread.Spreadsheet]:
    try:
        creds = Credentials.from_service_account_file(
            CONFIG["GOOGLE_CREDENTIALS_FILE"],
            scopes=SCOPES,
        )
        client = gspread.authorize(creds)
        client.set_timeout(SHEETS_TIMEOUT)
        return client.open(CONFIG["SPREADSHEET_NAME"])
    except Exception as e:
        print(f"⚠️  Google Sheets unavailable: {e}")
        return None


def _ensure_headers(sheet: gspread.Worksheet):
    # Only check the first row instead of downloading the whole worksheet.
    if not sheet.row_values(1):
        sheet.append_row(HEADERS)
        sheet.format("A1:J1", {"textFormat": {"bold": True}})


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, title: str) -> Optional[gspread.Worksheet]:
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        try:
            return spreadsheet.add_worksheet(title=title, rows=1000, cols=10)
        except Exception as e:
            print(f"⚠️  Google Sheets create sheet error ({title}): {e}")
            return None


def get_sheets() -> tuple[Optional[gspread.Worksheet], Optional[gspread.Worksheet]]:
    spreadsheet = _open_spreadsheet()
    if spreadsheet is None:
        return None, None

    try:
        qualified_sheet = spreadsheet.sheet1
        _ensure_headers(qualified_sheet)
    except Exception as e:
        print(f"⚠️  Google Sheets first sheet error: {e}")
        qualified_sheet = None

    all_jobs_sheet = _get_or_create_sheet(spreadsheet, ALL_JOBS_SHEET_TITLE)
    if all_jobs_sheet is not None:
        try:
            _ensure_headers(all_jobs_sheet)
        except Exception as e:
            print(f"⚠️  Google Sheets second sheet error: {e}")
            all_jobs_sheet = None

    return qualified_sheet, all_jobs_sheet


def _refresh_sheet(sheet: gspread.Worksheet) -> Optional[gspread.Worksheet]:
    spreadsheet = _open_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        refreshed = spreadsheet.worksheet(sheet.title)
        _ensure_headers(refreshed)
        return refreshed
    except Exception as e:
        print(f"⚠️  Google Sheets refresh error ({sheet.title}): {e}")
        return None


def log_job(sheet: Optional[gspread.Worksheet], data: dict) -> Optional[gspread.Worksheet]:
    """Write one job row to the worksheet."""
    if sheet is None:
        return None

    row = _build_row(data)
    try:
        sheet.append_row(row)
        return sheet
    except Exception as e:
        print(f"⚠️  Google Sheets append failed: {e}")
        try:
            refreshed_sheet = _refresh_sheet(sheet)
            if refreshed_sheet is not None:
                refreshed_sheet.append_row(row)
                print("   ℹ️  Google Sheets reconnected, row saved on retry")
                return refreshed_sheet
        except Exception as retry_error:
            print(f"⚠️  Google Sheets retry failed: {retry_error}")
        return None


def mark_reply(sheet: Optional[gspread.Worksheet], from_email: str) -> Optional[gspread.Worksheet]:
    """Mark a row as replied when a matching response is found."""
    if sheet is None:
        return None

    try:
        cell = sheet.find(from_email)
        if cell:
            sheet.update_cell(cell.row, 9, "Yes ✅")
        return sheet
    except Exception as e:
        print(f"⚠️  Google Sheets reply mark failed: {e}")
        try:
            refreshed_sheet = _refresh_sheet(sheet)
            if refreshed_sheet is not None:
                cell = refreshed_sheet.find(from_email)
                if cell:
                    refreshed_sheet.update_cell(cell.row, 9, "Yes ✅")
                return refreshed_sheet
        except Exception as retry_error:
            print(f"⚠️  Google Sheets reply retry failed: {retry_error}")
        return None
