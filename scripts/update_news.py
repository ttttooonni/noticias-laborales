import json, re, hashlib, html
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/"sources.json").read_text(encoding="utf-8"))
OUT=ROOT/"data/noticias.json"
MAX_ITEMS=250
LOOKBACK_DAYS=14
KEYWORDS={
 "laboral": ["laboral","trabajo","trabajador","trabajadora","empleo","jornada","salario","salarial","convenio","contrato","despido","vacaciones","permiso","igualdad","conciliación","cotización","pensión","seguridad social","riesgo laboral","prevención","huelga","negociación colectiva","hostelería","turismo","camarera","camarero","fijo discontinuo"],
 "sentencia": ["sentencia","tribunal supremo","tribunal superior de justicia","audiencia nacional","juzgado","poder judicial","tsj","sala de lo social","ecli"],
 "canarias": ["canarias","las palmas","tenerife","gran canaria","lanzarote","fuerteventura","la palma","la gomera","el hierro"],
 "hosteleria": ["hostelería","hotel","hoteles","restauración","turismo","alojamiento","camareras de piso","camarero","camarera"]
}

def fetch(url):
    req=Request(url,headers={"User-Agent":"NoticiasLaboralesPWA/1.0 (+GitHub Actions)"})
    with urlopen(req,timeout=30) as r:
        return r.read()

def clean(s):
    s=html.unescape(s or "")
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def first_text(node,*names):
    for n in names:
        x=node.find(n)
        if x is not None and x.text:
            return clean(x.text)
    return ""

def parse_date(s):
    if not s: return datetime.now(timezone.utc)
    s=s.strip()
    from email.utils import parsedate_to_datetime
    try:
        d=parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception: pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S","%Y-%m-%d"):
        try:
            d=datetime.strptime(s,fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception: pass
    return datetime.now(timezone.utc)

def parse_rss(raw,source):
    root=ET.fromstring(raw)
    items=root.findall(".//item")
    out=[]
    for item in items:
        title=first_text(item,"title")
        link=first_text(item,"link")
        desc=first_text(item,"description","summary")
        pub=first_text(item,"pubDate","published","date")
        if not title or not link: continue
        d=parse_date(pub)
        text=(title+" "+desc).lower()
        out.append({
            "id":hashlib.sha1((source["id"]+"|"+link).encode()).hexdigest()[:16],
            "title":title,
            "source":source["name"],
            "source_type":source["type"],
            "source_label":source["label"],
            "published":d.isoformat(),
            "categories":classify(text,source),
            "type":"sentencia" if any(k in text for k in KEYWORDS["sentencia"]) or source["type"]=="JUSTICIA" else "noticia",
            "summary":desc[:360],
            "what_happened":desc[:700],
            "who_affected":"",
            "impact":"",
            "ugt_position":"",
            "url":link,
            "_weight":source.get("weight",50)
        })
    return out

def classify(text,source):
    cats=list(source.get("categories",[]))
    if any(k in text for k in KEYWORDS["sentencia"]) and "Sentencias" not in cats: cats.append("Sentencias")
    if any(k in text for k in KEYWORDS["canarias"]) and "Canarias" not in cats: cats.append("Canarias")
    if any(k in text for k in KEYWORDS["hosteleria"]) and "Hostelería" not in cats: cats.append("Hostelería")
    mapping=[("Salarios",["salario","salarial","sueldo","retribución","poder adquisitivo"]),
             ("Jornada",["jornada","horas semanales","tiempo de trabajo","descanso"]),
             ("Convenios",["convenio colectivo","convenios colectivos","negociación colectiva"]),
             ("Empleo",["empleo","paro","desempleo","contratación","contrato"]),
             ("Derechos laborales",["derecho laboral","despido","permiso","vacaciones","igualdad","conciliación"])]
    for cat,words in mapping:
        if any(w in text for w in words) and cat not in cats: cats.append(cat)
    return cats[:8]

def relevant(item):
    text=(item["title"]+" "+item.get("summary","")).lower()
    if item["source_type"] in ("OFICIAL","JUSTICIA","UGT"):
        return any(k in text for group in KEYWORDS.values() for k in group) or "Canarias" in item["categories"]
    return False

def main():
    old={"updated_at":None,"items":[]}
    if OUT.exists():
        try: old=json.loads(OUT.read_text(encoding="utf-8"))
        except Exception: pass
    collected=[]
    failures=[]
    for source in CONFIG["sources"]:
        if source.get("enabled",True) is False: continue
        if source.get("kind")!="rss": continue
        try:
            collected.extend(parse_rss(fetch(source["url"]),source))
        except Exception as e:
            failures.append({"source":source["name"],"error":str(e)})
    cutoff=datetime.now(timezone.utc)-timedelta(days=LOOKBACK_DAYS)
    merged={}
    for item in old.get("items",[])+collected:
        if not relevant(item): continue
        try:
            d=parse_date(item.get("published"))
        except Exception:
            d=datetime.now(timezone.utc)
        if d < cutoff: continue
        merged[item["id"]]=item
    items=sorted(merged.values(),key=lambda x:(parse_date(x.get("published")),x.get("_weight",0)),reverse=True)[:MAX_ITEMS]
    for x in items: x.pop("_weight",None)
    now=datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    OUT.write_text(json.dumps({"updated_at":now,"items":items,"health":{"sources_checked":len([s for s in CONFIG["sources"] if s.get("enabled",True) and s.get("kind")=="rss"]),"failures":failures}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{len(items)} noticias conservadas; {len(failures)} fuentes con error.")
    if failures:
        for f in failures: print("WARN",f)

if __name__=="__main__": main()
