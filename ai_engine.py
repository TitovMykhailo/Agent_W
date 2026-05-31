"""
ai_engine.py - score jobs and generate outreach text with Azure OpenAI
"""

import json
from openai import AzureOpenAI
from config import CONFIG, CANDIDATE_PROFILE, APPLY_THRESHOLD

client = AzureOpenAI(
    api_key=CONFIG["AZURE_API_KEY"],
    azure_endpoint=CONFIG["AZURE_ENDPOINT"],
    api_version=CONFIG["AZURE_API_VERSION"],
    timeout=45.0,
)

EVALUATE_MAX_COMPLETION_TOKENS = 800
PROPOSAL_MAX_COMPLETION_TOKENS = 1600
REDDIT_COMMENT_MAX_COMPLETION_TOKENS = 320
OUTREACH_PLAN_MAX_COMPLETION_TOKENS = 1200


def _create_json_completion(model: str, prompt: str, max_completion_tokens: int) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        reasoning_effort="low",
        max_completion_tokens=max_completion_tokens,
    )
    choice = resp.choices[0]
    content = (choice.message.content or "").strip()
    if not content:
        usage = getattr(resp, "usage", None)
        reasoning_tokens = None
        if usage and usage.completion_tokens_details:
            reasoning_tokens = usage.completion_tokens_details.reasoning_tokens
        raise ValueError(
            "Model returned empty JSON content "
            f"(finish_reason={choice.finish_reason}, "
            f"max_completion_tokens={max_completion_tokens}, "
            f"reasoning_tokens={reasoning_tokens})"
        )
    return json.loads(content)


def _create_text_completion(model: str, prompt: str, max_completion_tokens: int) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        reasoning_effort="low",
        max_completion_tokens=max_completion_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def evaluate_job(title: str, description: str) -> dict:
    """
    Score a job from 0 to 10.
    Returns: {"score": 8, "reason": "...", "apply": True}
    """
    prompt = f"""
You are evaluating if a job posting matches a candidate profile.

CANDIDATE:
{CANDIDATE_PROFILE}

JOB POSTING:
Title: {title}
Description: {description[:1200]}

Rate the match from 0 to 10. Return ONLY valid JSON, no extra text:
{{"score": 7, "reason": "Short reason here", "apply": true}}

Scoring rules:
- 8-10: Perfect match, strong skills overlap, remote or Slovakia
- 6-7: Good match, most skills present
- 4-5: Partial match, worth considering
- 0-3: Poor match, skip
- Score 0 and apply=false if this is not an actual employer/client job post
- Score 0 and apply=false if this is a candidate advertising themselves, looking for work,
  asking career questions, or discussing jobs in general
- Strongly penalize senior/staff/lead/principal/head/director roles and jobs asking for 5+ years
  of experience unless the posting explicitly says that seniority is optional
- Set apply=true only if score >= {APPLY_THRESHOLD}
"""
    try:
        return _create_json_completion(
            model=CONFIG["AZURE_DEPLOYMENT_MINI"],
            prompt=prompt,
            max_completion_tokens=EVALUATE_MAX_COMPLETION_TOKENS,
        )
    except Exception as e:
        print(f"⚠️  Evaluate error: {e}")
        return {"score": 0, "reason": str(e), "apply": False}


def generate_proposal(title: str, description: str) -> dict:
    """
    Generate a personalized proposal.
    Returns: {"subject": "...", "body": "..."}
    """
    prompt = f"""
Write a professional job application email for this posting.

CANDIDATE:
{CANDIDATE_PROFILE}

JOB:
Title: {title}
Description: {description[:800]}

Requirements:
- Max 180 words in body
- Professional but human, not robotic
- Mention 1-2 specific relevant projects from candidate profile
- Show you read the job description (reference something specific)
- Clear call to action at the end
- Sign off with name, GitHub link, and email
- If the posting is clearly senior-only, managerial, discussion-only, or not a real job opening,
  return a minimal safe JSON with a generic subject/body instead of inventing details
- Return ONLY valid JSON, no extra text:
{{"subject": "Application for [role]", "body": "Dear hiring manager,\\n\\n..."}}
"""
    try:
        return _create_json_completion(
            model=CONFIG["AZURE_DEPLOYMENT_MAIN"],
            prompt=prompt,
            max_completion_tokens=PROPOSAL_MAX_COMPLETION_TOKENS,
        )
    except Exception as e:
        print(f"⚠️  Proposal error: {e}")
        return {
            "subject": f"Application: {title}",
            "body": f"Hi,\n\nI'm interested in this position. Please find my profile at {CONFIG['YOUR_GITHUB']}.\n\nBest,\n{CONFIG['YOUR_NAME']}"
        }


def generate_reddit_comment(title: str, description: str) -> str:
    prompt = f"""
Write a short public Reddit reply to a hiring post.

CANDIDATE:
{CANDIDATE_PROFILE}

POST:
Title: {title}
Description: {description[:900]}

Requirements:
- Maximum 90 words
- Sound human and direct, not salesy
- Say briefly why the candidate fits
- Invite the poster to DM on Reddit if interested
- Do not include email, phone, or external contact details
- Do not invent experience that is not in the candidate profile
- Return only the comment text, no quotes or extra formatting
"""
    try:
        comment = _create_text_completion(
            model=CONFIG["AZURE_DEPLOYMENT_MAIN"],
            prompt=prompt,
            max_completion_tokens=REDDIT_COMMENT_MAX_COMPLETION_TOKENS,
        )
        return comment.strip()
    except Exception as e:
        print(f"⚠️  Reddit comment generation error: {e}")
        return (
            f"Hi, I'm {CONFIG['YOUR_NAME']}. I work with Python, AI automation, "
            "APIs, and workflow integrations. This looks like a strong fit for my "
            "background. If you're interested, feel free to DM me here on Reddit."
        )


def generate_outreach_plan(title: str, description: str, source: str, contact: str = "") -> dict:
    prompt = f"""
You are preparing a manual outreach suggestion for a job candidate.

CANDIDATE:
{CANDIDATE_PROFILE}

JOB:
Source: {source}
Title: {title}
Description: {description[:1400]}
Known contact: {contact or "none"}

Return ONLY valid JSON, no extra text:
{{
  "message": "Short outreach message to send",
  "estimated_work_days": 5,
  "buffered_days": 6,
  "price_amount": 900,
  "price_currency": "EUR",
  "contact_channel": "email",
  "reason": "Why this is worth writing to"
}}

Rules:
- This is not an email subject/body pair; it is one short message to send manually.
- Keep the message under 120 words.
- Match the job post language when obvious, otherwise use English.
- Mention fit briefly and confidently.
- Include a price and delivery time naturally in the message.
- estimated_work_days must be your best estimate for the implementation itself.
- buffered_days must equal estimated_work_days + 1.
- Choose a realistic price for a freelance AI/Python automation task.
- Use EUR for Slovakia-focused jobs, otherwise USD.
- contact_channel should be one of: email, linkedin, reddit, website, unknown.
"""
    try:
        plan = _create_json_completion(
            model=CONFIG["AZURE_DEPLOYMENT_MAIN"],
            prompt=prompt,
            max_completion_tokens=OUTREACH_PLAN_MAX_COMPLETION_TOKENS,
        )
        estimated = int(plan.get("estimated_work_days", 5) or 5)
        plan["estimated_work_days"] = max(1, estimated)
        plan["buffered_days"] = plan["estimated_work_days"] + 1
        plan["price_amount"] = int(plan.get("price_amount", 700) or 700)
        plan["price_currency"] = (plan.get("price_currency", "USD") or "USD").upper()
        plan["contact_channel"] = (plan.get("contact_channel", "unknown") or "unknown").lower()
        plan["message"] = (plan.get("message", "") or "").strip()
        plan["reason"] = (plan.get("reason", "") or "").strip()
        return plan
    except Exception as e:
        print(f"⚠️  Outreach plan error: {e}")
        currency = "EUR" if source in {"Profesia.sk", "Worki.sk", "Jobs.sk"} else "USD"
        estimated_work_days = 5
        buffered_days = estimated_work_days + 1
        price_amount = 900 if currency == "EUR" else 1000
        return {
            "message": (
                f"Hi, I'm {CONFIG['YOUR_NAME']}. This looks like a strong match for my Python and AI "
                f"automation background. I can take this on for {price_amount} {currency} and deliver "
                f"it in {buffered_days} days. If helpful, I can share relevant examples and start right away."
            ),
            "estimated_work_days": estimated_work_days,
            "buffered_days": buffered_days,
            "price_amount": price_amount,
            "price_currency": currency,
            "contact_channel": "email" if contact else "unknown",
            "reason": "Strong fit for Python, AI automation, and API integration work.",
        }
