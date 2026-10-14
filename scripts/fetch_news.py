import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SOURCES = [
    ("HRT", "https://www.hrt.hr/rss/vijesti", "Hrvatska"),
    ("N1 Hrvatska", "https://n1info.hr/feed/", "Hrvatska"),
    ("Index", "https://www.index.hr/rss", "Hrvatska"),
    ("Telegram", "https://www.telegram.hr/feed/", "Hrvatska"),
    ("Tportal", "https://www.tportal.hr/rss", "Hrvatska"),
    ("Poslovni dnevnik", "https://www.poslovni.hr/feed", "Hrvatska"),
    ("Večernji list", "https://www.vecernji.hr/feeds/latest", "Hrvatska"),
    ("Jutarnji list", "https://news.google.com/rss/search?q=site%3Ajutarnji.hr+when%3A1d&hl=hr&gl=HR&ceid=HR%3Ahr", "Hrvatska"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "Svijet"),
    ("BBC Europe", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", "Svijet"),
    ("The Guardian", "https://www.theguardian.com/world/rss", "Svijet"),
    ("The Guardian Europe", "https://www.theguardian.com/world/europe-news/rss", "Svijet"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "Svijet"),
    ("DW", "https://rss.dw.com/rdf/rss-en-all", "Svijet"),
    ("France 24", "https://www.france24.com/en/rss", "Svijet"),
    ("Euronews", "https://www.euronews.com/rss", "Svijet"),
    ("Politico Europe", "https://www.politico.eu/feed/", "Svijet"),
    ("CNBC World", "https://www.cnbc.com/id/100727362/device/rss/rss.html", "Svijet"),
    ("TechCrunch", "https://techcrunch.com/feed/", "Svijet"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "Svijet"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "Svijet"),
    ("European Commission", "https://ec.europa.eu/commission/presscorner/api/rss?language=en", "Svijet"),
    ("ECB", "https://www.ecb.europa.eu/rss/press.html", "Svijet"),
]

NS_ATOM = "{http://www.w3.org/2005/Atom}"
NS_RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
NS_DC = "{http://purl.org/dc/elements/1.1/}"

def text(element, name):
    child = element.find(name)
    return "".join(child.itertext()).strip() if child is not None else ""

def parse_date(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def parse_feed(content, source, category):
    root = ET.fromstring(content)
    channel = root.find("channel")
    if channel is not None:
        items = channel.findall("item")
    elif root.tag == NS_ATOM + "feed":
        items = root.findall(NS_ATOM + "entry")
    else:
        items = root.findall(NS_RDF + "item")

    results = []
    for item in items[:25]:
        atom = item.tag.startswith(NS_ATOM)
        title = text(item, NS_ATOM + "title" if atom else "title")
        if atom:
            link = ""
            for candidate in item.findall(NS_ATOM + "link"):
                if candidate.get("rel", "alternate") == "alternate":
                    link = candidate.get("href", "")
                    break
            raw_date = text(item, NS_ATOM + "published") or text(item, NS_ATOM + "updated")
        else:
            link = text(item, "link")
            raw_date = text(item, "pubDate") or text(item, NS_DC + "date")

        if source == "Jutarnji list":
            publisher = text(item, "source")
            if publisher and "jutarnji" not in publisher.lower():
                continue
            if not publisher and "jutarnji" not in title.lower():
                continue
            if title.lower().endswith(" - jutarnji list"):
                title = title[:-len(" - Jutarnji list")]
        if title and link.startswith(("https://", "http://")):
            results.append({
                "title": title,
                "url": link,
                "source": source,
                "category": category,
                "published": raw_date,
                "published_iso": parse_date(raw_date)
            })
    return results

def main():
    articles = {}
    for name, url, category in SOURCES:
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; NewsroomRadar/0.2; RSS reader)",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
            })
            with urllib.request.urlopen(request, timeout=12) as response:
                content = response.read(2_000_000)
            found = parse_feed(content, name, category)
            for article in found:
                articles.setdefault(article["url"], article)
            print(f"OK {name}: {len(found)}")
        except Exception as exc:
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")

    sorted_articles = sorted(
        articles.values(),
        key=lambda a: a["published_iso"] or "",
        reverse=True
    )
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(sorted_articles),
        "articles": sorted_articles
    }
    with open("news.json", "w", encoding="utf-8") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)

    print(f"Saved {len(sorted_articles)} articles")
    if not sorted_articles:
        raise RuntimeError("No articles retrieved; inspect RSS URLs and network connectivity")

if __name__ == "__main__":
    main()
