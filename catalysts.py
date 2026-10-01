import json,os,re,time,datetime,urllib.request,xml.etree.ElementTree as ET
FEEDS=["https://news.google.com/rss/search?q=Binance+OR+Coinbase+OR+Upbit+OR+Bybit+listing+token+when:1d&hl=en-US&gl=US&ceid=US:en","https://news.google.com/rss/search?q=crypto+ETF+approval+OR+launch+OR+filing+when:1d&hl=en-US&gl=US&ceid=US:en","https://www.coindesk.com/arc/outboundfeeds/rss/","https://cointelegraph.com/rss","https://decrypt.co/feed","https://www.theblock.co/rss.xml",
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
    return list(dict.fromkeys(out))[:90]
PROMPT="""You are a STRICT crypto catalyst filter for a trader who only wants high-impact, tradable events and zero noise.
Return ONLY a JSON array (it may be empty: []) of at most 5 objects:
{"t":short title,"type":"listing"|"etf"|"regulation"|"unlock"|"hack"|"partnership"|"mainnet"|"treasury"|"burn"|"other","impact":integer 1-10,"s":"building"|"fading","c":"low"|"medium"|"high","coins":[tickers like WLD],"b":1-2 sentences why it moves this token,"per":{ticker:one-line take}}
INCLUDE only events that can move a specific token's price within hours: listings on top exchanges (Binance, Coinbase, Upbit, Bybit), spot ETF approvals/launches tied to a named token, regulatory decisions naming a token, large unlocks or burns, hacks/exploits, big-company partnerships or treasury purchases naming the token, mainnet/upgrade launches with a date.
IMPACT: 9-10 = Binance/Coinbase/Upbit listing, ETF approval or launch, major hack, large treasury buy. 7-8 = clear partnership or upgrade with a named token. Anything below 7: leave it out.
EXCLUDE: price predictions, analyst opinions, market recaps, opinion pieces, macro talk with no token, stories older than 24h, conferences, rumors with no named source, generic BTC/ETH price commentary.
Prefer stories covered by several headlines. If nothing qualifies return [].
Headlines:
"""
def pick():
    k=os.environ["GEMINI_API_KEY"]
    r=json.loads(get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key="+k))
    ms=[x["name"].split("/")[-1] for x in r.get("models",[]) if "generateContent" in x.get("supportedGenerationMethods",[])]
    ms=[m for m in ms if "flash" in m and not re.search("tts|live|image|audio|transcribe|robot|omni|preview|exp|thinking|native|computer|latest",m)]
    ver=lambda m:tuple(int(n) for n in (re.search(r"(\d+)\.(\d+)",m) or [0,0,0]).groups()) if re.search(r"(\d+)\.(\d+)",m) else (0,0)
    ms.sort(key=lambda m:(0 if "lite" in m else 1,tuple(-n for n in ver(m))))
    print("models:",ms[:5]);return ms[:4]
def llm(hl):
    body=json.dumps({"contents":[{"parts":[{"text":PROMPT+"\n".join(hl)}]}],"generationConfig":{"responseMimeType":"application/json"}}).encode()
    for m in pick():
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
if not os.environ.get("GEMINI_API_KEY"):
    print("no GEMINI_API_KEY, keeping previous file");raise SystemExit
try:cards=llm(hl)
except Exception as e:print("llm fail, keeping previous file:",e);raise SystemExit
cards=[c for c in cards if isinstance(c,dict) and c.get("coins") and int(c.get("impact",0))>=7][:5]
json.dump({"updated":datetime.datetime.now(datetime.timezone.utc).isoformat(),"cards":cards},open("catalysts.json","w"),indent=1)
print(len(cards),"high-impact cards")
