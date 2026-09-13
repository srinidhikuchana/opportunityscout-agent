import csv
import io
import re
from datetime import datetime, timedelta
from typing import Dict, List
from urllib.parse import urlparse


FREE_TERMS = ("free", "no fee", "no cost", "complimentary", "0 fee")
REMOTE_TERMS = ("remote", "online", "virtual")
HYDERABAD_TERMS = ("hyderabad", "telangana", "hyd ")
STUDENT_TERMS = ("student", "undergraduate", "college", "engineering", "university")
TOP_ORGS = (
    "microsoft", "google", "aws", "amazon", "ibm", "oracle", "nvidia", "meta",
    "github", "intel", "adobe", "salesforce", "iit", "iiit", "t-hub"
)


def normalize_results(results: List[Dict]) -> List[Dict]:
    output = []
    for r in results:
        url = r.get("url") or r.get("link") or ""
        title = r.get("title") or "Untitled opportunity"
        snippet = r.get("snippet") or r.get("content") or r.get("description") or ""
        date = r.get("date") or r.get("last_updated") or ""
        output.append(
            {
                "title": str(title).strip(),
                "url": str(url).strip(),
                "snippet": str(snippet).strip(),
                "date": str(date).strip(),
                "domain": urlparse(url).netloc.replace("www.", "") if url else "",
            }
        )
    return dedupe(output)


def dedupe(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for item in items:
        key = item["url"].lower() or item["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def score_item(item: Dict, location: str, only_free: bool, student_only: bool) -> int:
    text = f"{item['title']} {item['snippet']} {item['domain']}".lower()
    score = 50

    if any(term in text for term in TOP_ORGS):
        score += 15
    if only_free:
        score += 18 if any(term in text for term in FREE_TERMS) else -7
    if student_only:
        score += 10 if any(term in text for term in STUDENT_TERMS) else 0

    location_l = location.lower()
    if "hyderabad" in location_l:
        score += 12 if any(term in text for term in HYDERABAD_TERMS) else 0
        score += 7 if any(term in text for term in REMOTE_TERMS) else 0
    elif "remote" in location_l or "online" in location_l:
        score += 12 if any(term in text for term in REMOTE_TERMS) else 0

    # Slight penalty for obvious aggregators; official sources tend to be stronger.
    if any(x in item["domain"].lower() for x in ("pinterest.", "quora.", "facebook.")):
        score -= 8

    return max(0, min(100, score))


def rank_results(items: List[Dict], location: str, only_free: bool, student_only: bool) -> List[Dict]:
    ranked = []
    for item in items:
        row = dict(item)
        row["match_score"] = score_item(row, location, only_free, student_only)
        ranked.append(row)
    return sorted(ranked, key=lambda x: x["match_score"], reverse=True)


def build_search_prompt(
    opportunity_type: str,
    interests: str,
    location: str,
    timeframe: str,
    only_free: bool,
    student_only: bool,
) -> str:
    constraints = []
    if only_free:
        constraints.append("free or no registration fee")
    if student_only:
        constraints.append("open to undergraduate engineering students")

    constraint_text = ", ".join(constraints) if constraints else "relevant and currently available"
    return (
        f"Find current {opportunity_type} related to {interests}. "
        f"Location preference: {location}. Timeframe: {timeframe}. "
        f"Prioritize {constraint_text}. Include official registration/application pages, "
        f"deadlines or dates when available, and avoid expired opportunities."
    )


def csv_bytes(items: List[Dict]) -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=["title", "match_score", "date", "domain", "url", "snippet"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(items)
    return stream.getvalue().encode("utf-8")


def make_ics(title: str, url: str, note: str, days_from_now: int = 1) -> bytes:
    """Create a simple reminder event. Users can edit the exact event date after import."""
    start = (datetime.utcnow() + timedelta(days=days_from_now)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    uid = re.sub(r"[^a-zA-Z0-9]", "", title)[:30] + "@opportunityscout"
    desc = (note + "\\n" + url).replace("\n", "\\n").replace(",", "\\,")
    safe_title = title.replace(",", "\\,")
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//OpportunityScout//AI Agent//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}
DTSTART:{start.strftime("%Y%m%dT%H%M%SZ")}
DTEND:{end.strftime("%Y%m%dT%H%M%SZ")}
SUMMARY:Review / Apply: {safe_title}
DESCRIPTION:{desc}
URL:{url}
END:VEVENT
END:VCALENDAR
"""
    return ics.encode("utf-8")
