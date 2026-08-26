"""
core.py — shared logic for fetching AI news/tools/research items,
filtering out already-seen ones, judging relevance, and generating
one-line highlights.

Used by check_and_notify.py, which GitHub Actions runs on a schedule.
"""

import feedparser
import requests
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

MAX_ITEMS_PER_SOURCE = 8

FEEDS = {
    # --- News ---
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "Hacker News (AI)": "https://hnrss.org/newest?q=AI+OR+LLM+OR+%22machine+learning%22",

    # --- New tool launches ---
    "Product Hunt": "https://www.producthunt.com/feed",

    # --- Research ---
    "arXiv cs.AI": "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=20",
}

AI_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "gpt", "claude", "gemini", "openai",
    "anthropic", "machine learning", "ml model", "neural", "chatbot", "agent",
    "diffusion", "transformer", "copilot", "genai", "generative",
]


def is_relevant_source(source_name, title, summary):
    """Pre-filter: for general feeds (Product Hunt, HN) only keep AI-tagged items."""
    if source_name not in ("Product Hunt", "Hacker News (AI)"):
        return True
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in AI_KEYWORDS)


def fetch_new_items(seen_ids):
    """Returns a list of new (not-yet-seen) items across all feeds."""
    new_items = []
    for source_name, url in FEEDS.items():
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"[warn] failed to fetch {source_name}: {e}")
            continue

        count = 0
        for entry in parsed.entries:
            if count >= MAX_ITEMS_PER_SOURCE:
                break
            item_id = entry.get("id") or entry.get("link")
            if not item_id or item_id in seen_ids:
                continue

            title = entry.get("title", "").strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            published = entry.get("published", "") or entry.get("updated", "")

            if not is_relevant_source(source_name, title, summary):
                continue

            new_items.append({
                "id": item_id,
                "source": source_name,
                "title": title,
                "summary": summary[:600],
                "link": link,
                "published": published,
            })
            count += 1

    return new_items


# ---------------------------------------------------------------------------
# Relevance judging + highlight generation
# ---------------------------------------------------------------------------

def evaluate_item(item):
    """
    Judge whether this item is worth a notification, and if so, produce the
    one-line highlight. Uses Claude if ANTHROPIC_API_KEY is set, otherwise
    falls back to a free keyword-based filter.

    Returns: {"relevant": bool, "highlight": str}
    """
    if not ANTHROPIC_API_KEY:
        return _keyword_evaluate(item)

    prompt = f"""You are filtering a personal AI-news feed for someone who is a
DATA ANALYST / data science student. They only want to be interrupted with a
phone notification for:
(a) tools, techniques, or releases directly useful to data analysis work
    (SQL, dashboards, BI tools, data pipelines, pandas/analytics libraries,
    data visualization, analytics platforms), OR
(b) genuinely major new AI model or research breakthroughs (a significant new
    model release, a new capability that didn't exist before, a notable
    architecture or technique) — NOT routine incremental product updates,
    funding news, opinion pieces, or minor feature additions.

Everything else should be marked not relevant, including generic "AI startup
raises funding" or "company adds AI feature" stories.

Source: {item['source']}
Title: {item['title']}
Snippet: {item['summary']}

Respond with ONLY a JSON object, no other text, no markdown fences:
{{"relevant": true or false, "highlight": "one line, max 15 words, on why this specifically matters — omit or leave empty if not relevant"}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        raw = " ".join(text_blocks).strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return {
            "relevant": bool(parsed.get("relevant", False)),
            "highlight": parsed.get("highlight") or item["title"],
        }
    except Exception as e:
        print(f"[warn] Claude evaluation failed for '{item['title']}': {e}")
        return _keyword_evaluate(item)  # fall back to free filter rather than dropping everything


# Things that make an item worth notifying about.
INCLUDE_SIGNALS = [
    # data analyst / BI tooling
    "data analy", "data engineer", "data scien", "data pipeline", "data warehouse",
    "sql", "tableau", "power bi", "powerbi", "looker", "snowflake", "databricks",
    "pandas", "polars", "jupyter notebook", "dashboard", "business intelligence",
    "data visualization", "etl pipeline", "microsoft excel", "data cleaning",
    "no-code analytics",

    # major AI model / research releases — phrase-based, not bare brand names,
    # so a headline just mentioning "Claude" or "GPT" in passing doesn't match.
    "new model", "open-source model", "open sourced model", "releases new model",
    "launches new model", "unveils new model", "foundation model",
    "state of the art", "state-of-the-art", "new sota", "new architecture",
    "benchmark record", "outperforms all", "first model to", "breakthrough",
    "achieves human-level", "new frontier model", "stealth model",
    "new ai model", "major model release",
]

# Things that usually signal noise even if "AI" appears in the text.
EXCLUDE_SIGNALS = [
    "raises $", "raises funding", "seed round", "series a", "series b",
    "series c", "valuation", "acquired", "acquisition", "ipo", "ipo'd",
    "hedge fund", "lawsuit", "sues", "sec probe", "probed by", "joins the",
    "joins as", "hires", "steps down", "appoints", "conference stage",
    "disrupt stage", "opinion:", "here's why", "here's what", "explainer:",
]


def _keyword_evaluate(item):
    text = f"{item['title']} {item['summary']}".lower()

    has_exclude = any(sig in text for sig in EXCLUDE_SIGNALS)
    has_include = any(sig in text for sig in INCLUDE_SIGNALS)

    relevant = has_include and not has_exclude

    return {"relevant": relevant, "highlight": item["title"]}


def send_ntfy_notification(topic, item, highlight):
    if not topic:
        return
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=highlight.encode("utf-8"),
            headers={
                "Title": f"{item['source']}: {item['title'][:60]}".encode("utf-8"),
                "Click": item["link"],
                "Priority": "default",
                "Tags": "robot",
            },
            timeout=15,
        )
    except Exception as e:
        print(f"[warn] failed to send ntfy notification: {e}")
