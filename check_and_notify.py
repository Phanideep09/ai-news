#!/usr/bin/env python3
"""
check_and_notify.py — run by GitHub Actions on a schedule (see
.github/workflows/check-and-notify.yml).

Each run:
1. Loads what's already been seen from docs/data/seen_state.json
2. Fetches feeds, keeping only genuinely new items
3. Judges each new item for relevance (data-analyst tools / major AI news)
4. Sends a real push notification via ntfy.sh for each relevant item
5. Updates docs/data/feed_cache.json (what the phone app displays) and
   docs/data/seen_state.json (so items aren't re-processed next run)

The workflow then commits these two updated JSON files back to the repo,
so the static site (GitHub Pages) always serves the latest data — with no
server, and no laptop, needing to stay on.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import core

REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "docs" / "data"
STATE_FILE = DATA_DIR / "seen_state.json"
CACHE_FILE = DATA_DIR / "feed_cache.json"

MAX_CACHE_ITEMS = 100
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")


def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()).get("seen_ids", []))
    return set()


def save_seen(seen_ids):
    trimmed = list(seen_ids)[-2000:]
    STATE_FILE.write_text(json.dumps({"seen_ids": trimmed}, indent=2))


def load_cache():
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return []


def save_cache(items):
    CACHE_FILE.write_text(json.dumps(items[:MAX_CACHE_ITEMS], indent=2))


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not NTFY_TOPIC:
        print("[warn] NTFY_TOPIC is not set — no push notifications will be sent this run.")
    if not core.ANTHROPIC_API_KEY:
        print("[info] ANTHROPIC_API_KEY not set — using the free keyword-based relevance filter.")

    seen_ids = load_seen()
    print(f"[info] {len(seen_ids)} item(s) already seen")

    new_items = core.fetch_new_items(seen_ids)
    print(f"[info] fetched {len(new_items)} candidate new item(s) across all feeds")

    processed = []
    for item in new_items:
        evaluation = core.evaluate_item(item)
        seen_ids.add(item["id"])  # mark seen regardless, so we don't re-evaluate it forever

        if not evaluation["relevant"]:
            continue

        item["highlight"] = evaluation["highlight"]
        item["fetched_at"] = datetime.now(timezone.utc).isoformat()
        processed.append(item)

        core.send_ntfy_notification(NTFY_TOPIC, item, evaluation["highlight"])
        print(f"[notify] [{item['source']}] {item['title']} -> {evaluation['highlight']}")
        time.sleep(0.5)

    save_seen(seen_ids)

    cache = load_cache()
    cache = processed + cache  # newest first
    save_cache(cache)

    print(f"[done] {len(processed)} relevant item(s) this run. "
          f"{len(cache)} total item(s) now cached for the app.")


if __name__ == "__main__":
    main()
