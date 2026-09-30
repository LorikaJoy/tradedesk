import json,os,re,time,datetime,urllib.request,xml.etree.ElementTree as ET
FEEDS=["https://www.coindesk.com/arc/outboundfeeds/rss/","https://cointelegraph.com/rss","https://decrypt.co/feed","https://www.theblock.co/rss.xml",
"https://news.google.com/rss/search?q=SEC+OR+ETF+OR+crypto+regulation+when:1d&hl=en-US&gl=US&ceid=US:en"]
def get(u,data=None,h=None):
    r=urllib.request.Request(u,data=data,headers=h or {"User-Agent":"Mozilla/5.0"})
    return urllib.request.urlopen(r,timeout=30).read()
def headlines():
    out=[]
    for u in FEEDS:
        try:
            for it in ET.fromstring(get(u)).iter("item"):
                t=(it.findtext("title") or "").strip();d=re.sub("<[^>]+>","",it.findtext("description") or "")[:200]
                if t:out.append(f"{t} - {d}")
                if len(out)>=200:break
        except Exception as e:print("feed fail",u,e)
    return list(dict.fromkeys(out))[:70]
PROMPT="""You scan crypto/macro headlines for tradable catalysts on Binance USDT perps, aimed at catching a narrative BEFORE the crowd.
Return ONLY a JSON array of at most 6 objects: {"t":short title,"s":"building" or "fading","c":"low"|"medium"|"high" confidence,"coins":[tickers like WLD],"b":1-2 sentence why it matters,"per":{ticker:one-line take}}.
Prefer fresh, under-covered narratives with a clear link to a specific token. Skip noise and price predictions. No markdown.
Headlines:
"""
def llm(hl):
    body=json.dumps({"contents":[{"parts":[{"text":PROMPT+"\n".join(hl)}]}],"generationConfig":{"responseMimeType":"application/json"}}).encode()
    for m in ("gemini-2.5-flash-lite","gemini-2.5-flash"):
        try:
            u=f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key="+os.environ["GEMINI_API_KEY"]
            r=json.loads(get(u,body,{"content-type":"application/json"}))
            txt=r["candidates"][0]["content"]["parts"][0]["text"];return json.loads(txt[txt.index("["):txt.rindex("]")+1])
        except Exception as e:print(m,"failed",e)
    raise RuntimeError("all models failed")
COINS={"BTC":"bitcoin|btc","ETH":"ethereum|ether\\b|eth\\b","SOL":"solana","XRP":"xrp|ripple","DOGE":"dogecoin|doge","BNB":"binance coin|bnb","WLD":"worldcoin|world id","LINK":"chainlink","AVAX":"avalanche","SUI":"\\bsui\\b","ARB":"arbitrum","HYPE":"hyperliquid"}
def fallback(hl):
    cards=[]
    for k,p in COINS.items():
        m=[h for h in hl if re.search(p,h,re.I)]
        if len(m)>=2:cards.append({"t":f"{k} in the news ({len(m)} headlines)","s":"building","c":"low","coins":[k],"b":m[0][:160],"per":{}})
    return sorted(cards,key=lambda c:-int(re.search(r"\((\d+)",c["t"]).group(1)))[:6]
hl=headlines();print(len(hl),"headlines")
try:cards=llm(hl) if os.environ.get("GEMINI_API_KEY") else fallback(hl)
except Exception as e:print("llm fail",e);cards=fallback(hl)
if cards:json.dump({"updated":datetime.datetime.utcnow().isoformat()+"Z","cards":cards},open("catalysts.json","w"),indent=1)
print(len(cards),"cards")
