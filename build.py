#!/usr/bin/env python3
"""
Regenerates index.html from data.json.

data.json is a list of story objects:
  { "url": str, "source": str, "tagline": str, "date_added": "YYYY-MM-DD" }

Run this after data.json changes:
  python3 build.py
"""
import json
import html
from collections import OrderedDict
from datetime import datetime

DATA_FILE = "data.json"
OUTPUT_FILE = "index.html"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    stories = json.load(f)

# Sort newest first (by date_added, then by original order within a date)
stories.sort(key=lambda s: s["date_added"], reverse=True)

groups = OrderedDict()
for s in stories:
    groups.setdefault(s["date_added"], []).append(s)

def format_day_header(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%B %-d, %Y") if hasattr(d, "strftime") else date_str

def render_group(date_str, items):
    try:
        header = format_day_header(date_str)
    except Exception:
        header = date_str
    rows = []
    for s in items:
        tagline = html.escape(s["tagline"])
        source = html.escape(s["source"])
        url = html.escape(s["url"], quote=True)
        rows.append(f'''      <a class="story" href="{url}" target="_blank" rel="noopener noreferrer">
        <p class="tagline">{tagline}</p>
        <p class="meta">{source}</p>
      </a>''')
    rows_html = "\n".join(rows)
    return f'''    <section class="day-group">
      <h2>{header}</h2>
{rows_html}
    </section>'''

groups_html = "\n".join(render_group(d, items) for d, items in groups.items())

page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>theinfo.ai — AI trends, curated</title>
  <meta name="description" content="A running feed of the AI trend stories worth your attention, scanned from reputable outlets and updated hourly.">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="wrap">
    <header class="site-header">
      <h1>theinfo.ai</h1>
      <p>AI trends worth knowing about, scanned from reputable outlets and updated hourly.</p>
      <p class="disclaimer">This website is created, maintained, and updated 100% by AI.</p>
    </header>

    <main>
{groups_html}
    </main>

    <footer class="site-footer">
      <p>Curated automatically by AI agents &mdash; no human edits these headlines or picks these stories. Links go to the original source; taglines are AI-written.</p>
    </footer>
  </div>
</body>
</html>
'''

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(page)

print(f"Wrote {OUTPUT_FILE} with {len(stories)} stories across {len(groups)} day(s).")
