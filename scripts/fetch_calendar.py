"""Conservative calendar extraction from official institutional announcement pages."""
import json, re, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

TZ=ZoneInfo("Europe/Zagreb")
SOURCES=[
 ("Hrvatski sabor","Hrvatska","https://www.sabor.hr/hr/sve-najave/mjesec/{month}"),
 ("Vijeće EU","Svijet","https://www.consilium.europa.eu/en/meetings/calendar/"),
]
class Blocks(HTMLParser):
 def __init__(self):
  super().__init__();self.blocks=[];self.current=[];self.href="";self.in_skip=0
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag in ("script","style","nav","footer"):self.in_skip+=1
  if self.in_skip:return
  if tag=="a":self.href=d.get("href","")
  if tag in ("h2","h3","h4","li","p","time","a","div"):self.current.append((tag,self.href,[]))
 def handle_data(self,data):
  if not self.in_skip and self.current:self.current[-1][2].append(data)
 def handle_endtag(self,tag):
  if tag in ("script","style","nav","footer") and self.in_skip:self.in_skip-=1;return
  if self.in_skip:return
  if self.current and self.current[-1][0]==tag:
   t,h,parts=self.current.pop();s=" ".join(" ".join(parts).split())
   if s and len(s)<250:self.blocks.append((t,s,h))
   if self.current:self.current[-1][2].append(s)
  if tag=="a":self.href=""
def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (NewsroomRadar; editorial calendar)"})
 with urllib.request.urlopen(req,timeout=18) as r:return r.read(2500000).decode("utf-8","replace")
def normalize_link(url,base):
 from urllib.parse import urljoin
 return urljoin(base,url) if url else base
def collect_sabor(html,url,dates):
 parser=Blocks();parser.feed(html);found=[]
 # Official page lists each announcement as a date/time followed by its title.
 blocks=[(s,h) for tag,s,h in parser.blocks if tag in ("a","p","h2","h3","h4","time","li") and len(s)<220]
 for i,(s,h) in enumerate(blocks):
  m=re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})\.?\s*(?:(\d{1,2}):(\d{2}))?",s)
  if not m:continue
  day=f"{m[3]}-{m[2]}-{m[1]}"
  if day not in dates:continue
  for title,href in blocks[i+1:i+5]:
   if title==s or re.match(r"^\d{2}\.\d{2}\.\d{4}",title):break
   if len(title)<18 or title.lower() in ("više","najave"):continue
   if "sjednica" not in title.lower() and "konferenc" not in title.lower() and "okrugli" not in title.lower() and "sudjeluje" not in title.lower() and "prima " not in title.lower() and "otvorenju" not in title.lower():continue
   found.append(dict(date=day,time=(m[4].zfill(2)+":"+m[5]) if m[4] else None,title=title,source="Hrvatski sabor",area="Hrvatska",url=normalize_link(href,url),status="Najavljeno",priority="B"))
   break
 return found
def collect_eu(html,url,dates):
 parser=Blocks();parser.feed(html);found=[]
 blocks=[(tag,s,h) for tag,s,h in parser.blocks if tag in ("a","h2","h3","h4","time") and len(s)<180]
 monthnames={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
 for i,(tag,s,href) in enumerate(blocks):
  m=re.fullmatch(r"(\d{1,2})\s+("+ "|".join(monthnames) +r")\s+(\d{4})",s)
  if not m:continue
  day=f"{m[3]}-{monthnames[m[2]]:02d}-{int(m[1]):02d}"
  if day not in dates:continue
  for t,title,link in blocks[i+1:i+9]:
   if re.fullmatch(r"\d{1,2}\s+("+ "|".join(monthnames) +r")\s+\d{4}",title):break
   if t!="a" or len(title)<14 or title.lower() in ("read more","more information"):continue
   if any(w in title.lower() for w in ("council","summit","meeting","ministers","eurogroup","conference")):
    found.append(dict(date=day,time=None,title=title,source="Vijeće EU",area="Svijet",url=normalize_link(link,url),status="Najavljeno",priority="A" if "summit" in title.lower() or "european council" in title.lower() else "B"))
 return found
def main():
 now=datetime.now(TZ);dates={(now+timedelta(days=d)).date().isoformat() for d in range(0,4)}
 items=[];checks=[]
 for name,area,url in SOURCES:
  url=url.format(month=now.strftime("%Y%m"))
  try:
   html=fetch(url)
   found=collect_sabor(html,url,dates) if area=="Hrvatska" else collect_eu(html,url,dates)
   items.extend(found);checks.append({"source":name,"ok":True,"events":len(found)})
  except Exception as exc:
   checks.append({"source":name,"ok":False,"error":str(exc)[:150]})
 unique={}
 for item in items:unique[(item["date"],item["title"].lower(),item["source"])]=item
 events=sorted(unique.values(),key=lambda x:(x["date"],x["time"] or "99:99",x["area"],x["title"]))
 if not any(c["ok"] for c in checks):raise RuntimeError("No calendar source could be checked")
 result={"updated":datetime.now(timezone.utc).isoformat(),"timezone":"Europe/Zagreb","events":events,"checks":checks,"note":"Only confirmed dates from official pages; missing time is not inferred."}
 with open("calendar.json","w",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2)
 print("Calendar events:",len(events),"source checks:",checks)
if __name__=="__main__":main()
