"""
parsers.py - parse jobs from multiple sources
"""

import html
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
import feedparser
from bs4 import BeautifulSoup

from config import (
    JOBS_SK_RSS,
    KEYWORDS,
    LINKEDIN_LOCATION,
    LINKEDIN_MAX_RESULTS,
    LINKEDIN_SEARCH_TERMS,
    PROFESIA_SK_IT_URL,
    REDDIT_FEEDS,
    WORKI_SK_IT_URL,
)

REDDIT_HEADERS = {
    "User-Agent": "JobHunterAgent/1.0 (+https://github.com/TitovMykhailo)",
    "Accept": "application/json, application/rss+xml, application/xml;q=0.9",
}

LINKEDIN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SITE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SENIOR_ROLE_PATTERNS = (
    " senior ",
    " senior-",
    " senior,",
    " senior.",
    " sr ",
    " sr.",
    " staff ",
    " lead ",
    " principal ",
    " architect ",
    " head of ",
    " director ",
    " veduci ",
    " vedúci ",
    " seniorny ",
    " seniorný ",
)

REDDIT_CANDIDATE_SEEKING_PATTERNS = (
    "[for hire]",
    "for hire",
    "hire me",
    "open to work",
    "available for work",
    "available for hire",
    "looking for work",
    "looking for a job",
    "looking for job",
    "need a job",
    "seeking opportunities",
    "seeking opportunity",
    "my portfolio",
    "my rates",
    "dm me for work",
)

REDDIT_DISCUSSION_PATTERNS = (
    "how do i",
    "how can i",
    "where can i",
    "is anyone hiring",
    "advice",
    "any tips",
    "question",
    "help me",
    "what job",
    "what should i do",
    "can i get a job",
    "job search",
    "resume help",
)

REDDIT_HIRING_PATTERNS = (
    "[hiring]",
    "[task]",
    "[offer]",
    "we are hiring",
    "we're hiring",
    "hiring ",
    "looking for a ",
    "looking for an ",
    "need someone",
    "need a developer",
    "need a python",
    "job opening",
    "contract role",
    "paid task",
    "paid gig",
    "budget:",
    "send portfolio",
)


def _matches_keywords(text: str) -> bool:
    text = text.lower()
    return any(kw in text for kw in KEYWORDS)


def _normalize_text(text: str) -> str:
    return f" {text.lower()} "


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return any(pattern in normalized for pattern in patterns)


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    clean_html = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", clean_html)
    return re.sub(r"\s+", " ", text).strip()


def _extract_emails(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)


def _truncate(text: str, limit: int = 2000) -> str:
    return text[:limit]


def _fetch_soup(url: str, *, headers: dict | None = None, timeout: int = 12) -> BeautifulSoup:
    response = requests.get(url, headers=headers or SITE_HEADERS, timeout=timeout)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _job_matches(title: str, description: str = "") -> bool:
    return _matches_keywords(f"{title} {description}")


def _extract_reddit_post_id(link: str) -> str:
    match = re.search(r"/comments/([a-z0-9]+)/", link.lower())
    if not match:
        return ""
    return f"t3_{match.group(1)}"


def _extract_reddit_subreddit(link: str) -> str:
    match = re.search(r"/r/([^/]+)/", link.lower())
    if not match:
        return ""
    return match.group(1)


def _has_seniority_mismatch(title: str, description: str) -> bool:
    combined = f"{title} {description}"
    if _contains_any(combined, SENIOR_ROLE_PATTERNS):
        return True
    return bool(re.search(r"\b([5-9]|[1-9]\d)\+?\s*(years|yrs|year|rokov|roky|let)\b", combined.lower()))


def _is_reddit_candidate_seeking_post(title: str, description: str) -> bool:
    return _contains_any(f"{title} {description}", REDDIT_CANDIDATE_SEEKING_PATTERNS)


def _is_reddit_discussion_post(title: str, description: str) -> bool:
    combined = f"{title} {description}"
    return title.strip().endswith("?") or _contains_any(combined, REDDIT_DISCUSSION_PATTERNS)


def _has_reddit_hiring_signal(title: str, description: str) -> bool:
    return _contains_any(f"{title} {description}", REDDIT_HIRING_PATTERNS)


def prefilter_job(job: dict) -> tuple[bool, str]:
    title = job.get("title", "")
    description = job.get("description", "")
    source = job.get("source", "")

    if _has_seniority_mismatch(title, description):
        return False, "Filtered: senior-level role"

    if source == "Reddit":
        if _is_reddit_candidate_seeking_post(title, description):
            return False, "Filtered: candidate looking for work"

        has_hiring_signal = _has_reddit_hiring_signal(title, description)
        if _is_reddit_discussion_post(title, description) and not has_hiring_signal:
            return False, "Filtered: Reddit discussion/question"

        if not has_hiring_signal and not job.get("contact_email"):
            return False, "Filtered: no clear hiring signal"

    return True, ""


def _reddit_json_to_rss(url: str) -> str:
    parsed = urlparse(url)
    limit = parse_qs(parsed.query).get("limit", ["25"])[0]
    path = parsed.path.removesuffix(".json").rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}/.rss?sort=new&limit={limit}"


def _build_reddit_job(title: str, text: str, link: str) -> dict | None:
    normalized_text = _html_to_text(text)
    full_text = f"{title} {normalized_text}"
    if not _matches_keywords(full_text):
        return None

    emails_found = _extract_emails(normalized_text)
    post_id = _extract_reddit_post_id(link)
    subreddit = _extract_reddit_subreddit(link)
    return {
        "source": "Reddit",
        "title": title,
        "description": _truncate(normalized_text),
        "url": link,
        "contact_email": emails_found[0] if emails_found else "",
        "reddit_post_id": post_id,
        "subreddit": subreddit,
    }


def _parse_reddit_json(url: str) -> list:
    jobs = []
    response = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()

    for post in data["data"]["children"]:
        payload = post["data"]
        job = _build_reddit_job(
            title=payload.get("title", ""),
            text=payload.get("selftext", ""),
            link=f"https://reddit.com{payload.get('permalink', '')}",
        )
        if job:
            if payload.get("name"):
                job["reddit_post_id"] = payload["name"]
            if payload.get("subreddit"):
                job["subreddit"] = payload["subreddit"].lower()
            jobs.append(job)
    return jobs


def _parse_reddit_rss(url: str) -> list:
    jobs = []
    response = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    for entry in feed.entries:
        body = entry.get("summary", "")
        job = _build_reddit_job(
            title=entry.get("title", ""),
            text=body,
            link=entry.get("link", ""),
        )
        if job:
            jobs.append(job)
    return jobs


def parse_reddit() -> list:
    jobs = []
    for url in REDDIT_FEEDS:
        json_error = None
        try:
            jobs.extend(_parse_reddit_json(url))
            continue
        except Exception as e:
            json_error = e

        rss_url = _reddit_json_to_rss(url)
        try:
            jobs.extend(_parse_reddit_rss(rss_url))
            if json_error is not None:
                print(f"   ℹ️  Reddit JSON failed, used RSS fallback: {rss_url}")
        except Exception as e:
            if json_error is None:
                print(f"⚠️  Reddit RSS error ({rss_url}): {e}")
            else:
                print(f"⚠️  Reddit error ({url}): JSON failed: {json_error}; RSS failed: {e}")
    return jobs


def _parse_profesia_detail(url: str) -> tuple[str, str, str]:
    soup = _fetch_soup(url)
    company_node = soup.select_one("h2")
    location_node = soup.select_one("span[itemprop='address']")
    description_node = soup.select_one("div.details[itemprop='description'] div.details-desc")

    company = company_node.get_text(" ", strip=True) if company_node else ""
    location = location_node.get_text(" ", strip=True) if location_node else ""
    description = _html_to_text(str(description_node)) if description_node else ""
    return company, location, description


def parse_profesia() -> list:
    jobs = []
    seen_urls = set()

    try:
        soup = _fetch_soup(PROFESIA_SK_IT_URL)
    except Exception as e:
        print(f"⚠️  Profesia.sk error: {e}")
        return jobs

    for link_node in soup.select("a[href*='/en/work/'][href*='/O']"):
        href = link_node.get("href", "")
        title = link_node.get_text(" ", strip=True)
        if not href or not title or title == "Save job offer":
            continue

        url = urljoin("https://www.profesia.sk", href.split("?", 1)[0])
        if url in seen_urls:
            continue
        seen_urls.add(url)

        if not _job_matches(title):
            continue

        try:
            company, location, description = _parse_profesia_detail(url)
        except Exception:
            company, location, description = "", "", ""

        full_description = " | ".join(filter(None, [company, location, description]))
        if not _job_matches(title, full_description):
            continue

        emails_found = _extract_emails(description)
        jobs.append({
            "source": "Profesia.sk",
            "title": title,
            "description": _truncate(full_description),
            "url": url,
            "contact_email": emails_found[0] if emails_found else "",
        })
    return jobs


def _parse_worki_detail(url: str) -> tuple[str, str, str]:
    soup = _fetch_soup(url)
    company_node = soup.select_one("h3.fs-sm")
    main_node = soup.select_one("main")
    description_node = None

    for heading in soup.select("h4"):
        heading_text = heading.get_text(" ", strip=True).lower()
        if "náplň práce" in heading_text:
            description_node = heading.find_next("div")
            break

    company = company_node.get_text(" ", strip=True) if company_node else ""
    main_text = main_node.get_text(" ", strip=True) if main_node else ""
    location = ""
    location_match = re.search(r"Miesto výkonu práce\s+(.*?)\s+(Home office|Druh pracovného pomeru|Mzda|Plat|Údaje o pracovnom mieste)", main_text)
    if location_match:
        location = location_match.group(1).strip()

    description = _html_to_text(str(description_node)) if description_node else ""
    return company, location, description


def parse_worki() -> list:
    jobs = []
    seen_urls = set()

    try:
        soup = _fetch_soup(WORKI_SK_IT_URL)
    except Exception as e:
        print(f"⚠️  Worki.sk error: {e}")
        return jobs

    for link_node in soup.select("h2 a[href*='ponuka-prace']"):
        href = link_node.get("href", "")
        title = link_node.get_text(" ", strip=True).removeprefix("TOP").strip()
        if not href or not title:
            continue

        url = href.split("?", 1)[0]
        if url in seen_urls:
            continue
        seen_urls.add(url)

        if not _job_matches(title):
            continue

        try:
            company, location, description = _parse_worki_detail(url)
        except Exception:
            company, location, description = "", "", ""

        full_description = " | ".join(filter(None, [company, location, description]))
        if not _job_matches(title, full_description):
            continue

        emails_found = _extract_emails(description)
        jobs.append({
            "source": "Worki.sk",
            "title": title,
            "description": _truncate(full_description),
            "url": url,
            "contact_email": emails_found[0] if emails_found else "",
        })
    return jobs


def _linkedin_search_url(term: str, start: int = 0) -> str:
    params = {
        "keywords": term,
        "location": LINKEDIN_LOCATION,
        "start": start,
        "f_TPR": "r604800",
        "position": 1,
        "pageNum": 0,
    }
    return (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
        + urlencode(params)
    )


def _linkedin_job_description(job_id: str) -> str:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    response = requests.get(url, headers=LINKEDIN_HEADERS, timeout=12)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    node = soup.select_one("div.show-more-less-html__markup")
    return _html_to_text(str(node)) if node else ""


def parse_linkedin() -> list:
    jobs = []
    seen_urls = set()

    for term in LINKEDIN_SEARCH_TERMS:
        if len(jobs) >= LINKEDIN_MAX_RESULTS:
            break

        search_url = _linkedin_search_url(term)
        try:
            response = requests.get(search_url, headers=LINKEDIN_HEADERS, timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f"⚠️  LinkedIn search error ({term}): {e}")
            continue

        for card in soup.select("div.base-search-card"):
            link_node = card.select_one("a.base-card__full-link")
            title_node = card.select_one("h3.base-search-card__title")
            company_node = card.select_one("h4.base-search-card__subtitle")
            location_node = card.select_one("span.job-search-card__location")

            link = (link_node.get("href", "") if link_node else "").split("?", 1)[0]
            title = title_node.get_text(" ", strip=True) if title_node else ""
            company = company_node.get_text(" ", strip=True) if company_node else ""
            location = location_node.get_text(" ", strip=True) if location_node else ""

            if not link or link in seen_urls or not title:
                continue

            description = ""
            urn = card.get("data-entity-urn", "")
            job_id = urn.rsplit(":", 1)[-1] if urn else ""
            if job_id:
                try:
                    description = _linkedin_job_description(job_id)
                except Exception:
                    description = ""

            full_text = " ".join(filter(None, [title, company, location, description]))
            if not _matches_keywords(full_text):
                continue

            emails_found = _extract_emails(description)
            jobs.append({
                "source": "LinkedIn",
                "title": title,
                "description": _truncate(
                    " | ".join(filter(None, [company, location, description]))
                ),
                "url": link,
                "contact_email": emails_found[0] if emails_found else "",
            })
            seen_urls.add(link)

            if len(jobs) >= LINKEDIN_MAX_RESULTS:
                break

    return jobs


def parse_rss(url: str, source_name: str) -> list:
    jobs = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            desc  = entry.get("summary", "")
            link  = entry.get("link", "")

            if not _matches_keywords(title + " " + desc):
                continue

            jobs.append({
                "source": source_name,
                "title": title,
                "description": _truncate(desc),
                "url": link,
                "contact_email": "",
            })
    except Exception as e:
        print(f"⚠️  RSS error ({source_name}): {e}")
    return jobs


def get_all_jobs() -> list:
    print("🔍 Parsing sources...")
    profesia_jobs = parse_profesia()
    worki_jobs = parse_worki()
    linkedin_jobs = parse_linkedin()
    reddit_jobs = parse_reddit()
    jobs_sk_jobs = parse_rss(JOBS_SK_RSS, "Jobs.sk")

    jobs = []
    jobs += profesia_jobs
    jobs += worki_jobs
    jobs += linkedin_jobs
    jobs += jobs_sk_jobs
    jobs += reddit_jobs

    print(
        "   Sources → "
        f"Profesia.sk: {len(profesia_jobs)} | "
        f"Worki.sk: {len(worki_jobs)} | "
        f"LinkedIn: {len(linkedin_jobs)} | "
        f"Jobs.sk: {len(jobs_sk_jobs)} | "
        f"Reddit: {len(reddit_jobs)}"
    )
    print(f"   Found {len(jobs)} relevant postings")
    return jobs
