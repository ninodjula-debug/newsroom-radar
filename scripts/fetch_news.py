import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SOURCES = [
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "Svijet"),
    ("BBC Europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "Svijet"),
    ("The Guardian", "https://www.theguardian.com/world/rss", "Svijet"),
    ("HRT", "https://www.hrt.hr/rss/vijesti", "Hrvatska"),
]

news = []

for name, url, category in SOURCES:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "NewsroomRadar/0.1"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()

        root = ET.fromstring(content)

        for item in root.findall(".//channel/item")[:15]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            date = item.findtext("pubDate", "").strip()

            if title and link:
                news.append({
                    "title": title,
                    "url": link,
                    "source": name,
                    "category": category,
                    "published": date
                })

        print(f"OK: {name}")

    except Exception as error:
        print(f"ERROR: {name}: {error}")

news = list({item["url"]: item for item in news}.values())

output = {
    "updated": datetime.now(timezone.utc).isoformat(),
    "count": len(news),
    "articles": news
}

with open("news.json", "w", encoding="utf-8") as file:
    json.dump(output, file, ensure_ascii=False, indent=2)

print(f"Saved {len(news)} articles")
