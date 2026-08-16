#!/usr/bin/env python3
"""
Runs hourly via GitHub Actions (see .github/workflows/hourly-update.yml).

1. Reads feeds.json  -> the "must scan" outlet RSS feeds.
2. Reads discovery_domains.json -> reputable outlets allowed in from a
   broader Google News search, even if not in feeds.json.
3. Filters out anything already in data.json (by URL) or not AI-related.
4. Writes a catchy tagline for each new story via the Anthropic API.
5. Appends to data.json and regenerates index.html via build.py.

Standard library only -- no pip install required.
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

DATA_FILE = "data.json"
FEEDS_FILE = "feeds.json"
DISCOVERY_DOMAINS_FILE = "discovery_domains.json"
MAX_NEW_PER_RUN = 15
REQUEST_TIMEOUT = 20

AI_KEYWORDS = [
    "ai", "artificial intelligence", "llm", "gpt", "chatgpt", "openai",
    "anthropic", "claude", "machine learning", "genai", "generative ai",
    "ai agent", "gemini", "copilot", "neural network", "ai model",
    "large language model",
]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

UA = "Mozilla/5.0 (compatible; theinfo-ai-bot/1.0; +https://theinfo.ai)"


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def domain_of(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)/?", url)
    return m.group(1).lower() if m else ""


def is_ai_relevant(text):
    t = text.lower()
    return any(k in t for k in AI_KEYWORDS)


def http_get(url, timeout=REQUEST_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.geturl()


def parse_rss(xml_bytes):
    """Minimal RSS 2.0 parser. Returns list of {title, link, source_name}."""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    channel = root.find("channel")
    entries = channel.findall("item") if channel is not None else root.findall(".//item")
    for it in entries:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        source_el = it.find("source")
        source_name = None
        if source_el is not None and source_el.text:
            source_name = source_el.text.strip()
        if title and link:
            items.append({"title": title, "link": link, "source_name": source_name})
    return items


def fetch_primary_feeds(feeds):
    candidates = []
    for outlet in feeds:
        try:
            xml_bytes, _ = http_get(outlet["feed_url"])
            for item in parse_rss(xml_bytes):
                candidates.append({
                    "url": item["link"],
                    "title": item["title"],
                    "source": outlet["name"],
                })
        except Exception as ex:
            print(f"Failed to fetch feed {outlet.get('name')}: {ex}", file=sys.stderr)
    return candidates


def fetch_discovery_items(allowlist):
    """Broader sweep via Google News RSS search, restricted to reputable domains."""
    query = urllib.parse.quote('artificial intelligence when:1d')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    candidates = []
    try:
        xml_bytes, _ = http_get(url)
    except Exception as ex:
        print(f"Discovery feed fetch failed: {ex}", file=sys.stderr)
        return candidates

    for item in parse_rss(xml_bytes):
        dom = domain_of(item["link"])
        source_name = item["source_name"] or dom
        allowed = any(d in dom for d in allowlist) or any(
            d.split(".")[0].lower() in (source_name or "").lower() for d in allowlist
        )
        if not allowed:
            continue
        # Google News links are redirects; resolve to the real article URL.
        resolved_url = item["link"]
        try:
            _, final_url = http_get(item["link"], timeout=15)
            if final_url:
                resolved_url = final_url
        except Exception:
            pass
        candidates.append({"url": resolved_url, "title": item["title"], "source": source_name})
    return candidates


def catchy_tagline(title, source):
    if not ANTHROPIC_API_KEY:
        return title
    prompt = (
        "Write ONE short, catchy tagline (under 100 characters) for a hyperlink pointing to "
        "this news article. It should tease the story and differ from the literal headline, "
        "but must not misrepresent the facts. No quotation marks, no emoji, no trailing period, "
        "no hashtags. Respond with only the tagline text.\n\n"
        f"Headline: {title}\nSource: {source}\n\nTagline:"
    )
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 60,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        text = result["content"][0]["text"].strip()
        return text.strip('"').strip() or title
    except Exception as ex:
        print(f"Tagline generation failed for {title!r}: {ex}", file=sys.stderr)
        return title


def main():
    data = load_json(DATA_FILE, [])
    feeds = load_json(FEEDS_FILE, [])
    allowlist = load_json(DISCOVERY_DOMAINS_FILE, [])
    existing_urls = {s["url"] for s in data}

    candidates = fetch_primary_feeds(feeds)
    candidates += fetch_discovery_items(allowlist)

    new_items = []
    seen_this_run = set()
    for c in candidates:
        if not c["url"] or c["url"] in existing_urls or c["url"] in seen_this_run:
            continue
        if not is_ai_relevant(c["title"]):
            continue
        seen_this_run.add(c["url"])
        new_items.append(c)
        if len(new_items) >= MAX_NEW_PER_RUN:
            break

    if new_items:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for item in new_items:
            tagline = catchy_tagline(item["title"], item["source"])
            data.append({
                "url": item["url"],
                "source": item["source"],
                "tagline": tagline,
                "date_added": today,
            })
            print(f"Added [{item['source']}]: {tagline}")

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"Added {len(new_items)} new stories.")
    else:
        print("No new stories found this run.")

    # Always rebuild, even with no new stories, so template/style changes
    # (build.py, style.css) take effect on the very next run rather than
    # waiting for the next new story.
    print("Rebuilding index.html...")
    subprocess.run([sys.executable, "build.py"], check=True)


if __name__ == "__main__":
    main()
