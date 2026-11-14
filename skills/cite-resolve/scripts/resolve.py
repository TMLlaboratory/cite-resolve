#!/usr/bin/env python3
"""Resolve references to verified bibliographic records. Standard library only.

Never trusts the caller's bibliographic fields: every field in the output comes from a registry
(Crossref, DataCite, arXiv, optionally Semantic Scholar). The caller's title/URL is only a lookup key.

Order per reference:
  1. a DOI given, or a DOI inside the URL        -> Crossref, else DataCite (arXiv, Zenodo, ...)
  2. an arXiv ID given, or an arXiv URL          -> arXiv API; DOI 10.48550/arXiv.<id>
                                                    (+ the journal DOI if arXiv records one)
  3. a title                                     -> Crossref bibliographic search; accepted only
                                                    when the registry title matches the given title
  3b. ACL Anthology URL -> its .bib (+ Crossref when it has a DOI); ScienceDirect /pii/ -> Crossref
  4. (optional, --s2) title                      -> Semantic Scholar; for venues without DOIs
                                                    (many CS conferences)

Input:  JSON list (file or stdin) of {"title"?, "url"?, "doi"?, "arxiv"?, "authors"?, "year"?}
        or a single reference via --title / --url / --doi / --arxiv
Output: JSON list of {"input", "status", "source", "record", "bibtex", "note"}
        status: verified | ambiguous | not_found
        record: {title, authors[], year, venue, doi, url}   (registry values only)

    python3 resolve.py refs.json [--bibtex] [--s2] [--mailto you@example.org]
    python3 resolve.py --title "Attention is all you need"

Environment (optional): CROSSREF_MAILTO (Crossref polite pool), S2_API_KEY (Semantic Scholar).
"""
import argparse, html, json, os, re, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = "cite-resolve/0.1 (+https://github.com/TMLlaboratory/cite-resolve)"


def http(url, params=None, headers=None, tries=4, raw=False):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, **(headers or {})}
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
                b = r.read()
                return b.decode("utf-8", "replace") if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 * 2 ** i)
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 * 2 ** i)
    return None


def norm(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = html.unescape(re.sub(r"<[^>]+>", "", t))  # Crossref titles can carry <i>, <sub>, &amp;
    return re.sub(r"[^0-9a-z぀-ヿ一-鿿]", "", t)


def title_match(a, b):
    """2 = same title, 1 = one side drops a subtitle ("X" vs "X: Y", only for long titles), 0 = different."""
    if (a or "").endswith(TRUNC) or (b or "").endswith(TRUNC):  # truncated by the search engine
        x, y = sorted((a, b), key=lambda t: not t.endswith(TRUNC))
        x, y = norm(x), norm(y)
        return 2 if len(x) >= 25 and y.startswith(x) else 0
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0
    if a == b:
        return 2
    short, long_ = sorted((a, b), key=len)
    return 1 if len(short) >= 30 and long_.startswith(short) else 0


def overlap(a, b):
    """Share of the given title's words found in the registry title."""
    w = lambda t: set(re.findall(r"[a-z0-9]{3,}|[\u3040-\u30ff\u4e00-\u9fff]", unicodedata.normalize("NFKC", t).lower()))
    a, b = w(a.replace(TRUNC, "")), w(b)
    return len(a & b) / len(a) if a else 1.0


def surname_ok(given, rec):
    """True when no authors were given, or the first given surname appears among the record's authors."""
    if not given:
        return True
    first = given[0] if isinstance(given, list) else re.split(r"[,;]| and ", given)[0]
    sur = norm(first.split(",")[0] if "," in first else (first.split() or [""])[-1])
    return not sur or any(sur in norm(a) for a in rec.get("authors", []))


def year_ok(year, rec):
    return not year or not rec.get("year") or abs(int(rec["year"]) - int(year)) <= 1


PLACEHOLDER = {"", "na", "n/a", "none", "untitled", "pdf"}
TRUNC = "\u2026"


def clean_title(t):
    """Strip what search engines add around a title. A trailing '...' is kept as TRUNC (prefix match)."""
    t = (t or "").strip()
    if t.strip().lower() in PLACEHOLDER:
        return ""
    t = re.sub(r"^\[[^\]]*\]\s*", "", t)                 # "[2411.14491] Title", "[PDF] Title"
    t = re.sub(r"^(review|research|original|full[- ]length) (article|paper)\s+", "", t, flags=re.I)
    t = re.sub(r"\\[a-zA-Z]+\*?", "", t)                  # LaTeX macros in arXiv html titles
    trunc = bool(re.search(r"(\.\.\.|\u2026)\s*(-.*)?$", t))
    t = re.sub(r"\s*(\.\.\.|\u2026).*$", "", t)
    t = re.split(r"\s+[|–—]\s+|\s+-\s+(?=[A-Z][^ ]*$)", t)[0]  # "Title | Site", "Title - arXiv"
    t = t.strip().rstrip(".")
    return t + TRUNC if trunc and t else t


# ---------- registries ----------

def crossref_work(doi, mailto):
    j = http("https://api.crossref.org/works/" + urllib.parse.quote(doi), {"mailto": mailto} if mailto else None)
    return from_crossref(j["message"]) if j and j.get("message") else None


def from_crossref(m):
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = (m.get(k) or {}).get("date-parts") or [[None]]
        if dp[0] and dp[0][0]:
            year = dp[0][0]
            break
    authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
               for a in m.get("author", [])]
    return {"title": html.unescape(re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0])), "authors": authors, "year": year,
            "venue": html.unescape((m.get("container-title") or [""])[0] or m.get("publisher", "")),
            "volume": m.get("volume"), "issue": m.get("issue"), "pages": m.get("page"),
            "type": m.get("type"), "doi": m.get("DOI"), "url": m.get("URL")}


def datacite_work(doi):
    j = http("https://api.datacite.org/dois/" + urllib.parse.quote(doi))
    a = (j or {}).get("data", {}).get("attributes")
    if not a:
        return None
    return {"title": (a.get("titles") or [{}])[0].get("title", ""),
            "authors": [c.get("name", "") for c in a.get("creators", [])], "year": a.get("publicationYear"),
            "venue": a.get("publisher", ""), "type": (a.get("types") or {}).get("resourceTypeGeneral"),
            "doi": a.get("doi"), "url": a.get("url")}


def arxiv_work(aid):
    x = http("https://export.arxiv.org/api/query", {"id_list": aid}, raw=True)
    if not x:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    e = ET.fromstring(x).find("a:entry", ns)
    if e is None or e.find("a:title", ns) is None:
        return None
    base = re.sub(r"v\d+$", "", aid)
    jdoi = e.findtext("x:doi", None, ns)
    return {"title": " ".join(e.findtext("a:title", "", ns).split()),
            "authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
            "year": int(e.findtext("a:published", "0000", ns)[:4]), "venue": "arXiv",
            "eprint": base, "doi": "10.48550/arXiv." + base, "journal_doi": jdoi,
            "journal_ref": e.findtext("x:journal_ref", None, ns), "url": "https://arxiv.org/abs/" + base}


def acl_work(acl_id):
    t = http(f"https://aclanthology.org/{acl_id}.bib", raw=True)
    if not t or not t.lstrip().startswith("@"):
        return None
    f = lambda k: (re.search(k + r'\s*=\s*"(.*?)",?\s*\n', t, re.S) or [None, None])[1]
    auth = [" ".join(reversed([x.strip() for x in a.split(",", 1)])) for a in (f("author") or "").replace("\n", " ").split(" and ") if a.strip()]
    return {"title": re.sub(r"[{}]", "", " ".join((f("title") or "").split())), "authors": auth,
            "year": int(f("year")) if (f("year") or "").isdigit() else None, "venue": re.sub(r"[{}]", "", " ".join((f("booktitle") or f("journal") or "").split())),
            "pages": f("pages"), "doi": f("doi"), "url": f("url") or f"https://aclanthology.org/{acl_id}", "bibtex_source": t.strip()}


def crossref_pii(pii, mailto):
    p = {"filter": "alternative-id:" + pii, "rows": 1}
    if mailto:
        p["mailto"] = mailto
    j = http("https://api.crossref.org/works", p)
    items = ((j or {}).get("message") or {}).get("items", [])
    return from_crossref(items[0]) if items else None


def crossref_search(title, mailto, year=None, authors=None):
    """[(match score, record)] for registry records whose title matches, after year/author filters."""
    first = authors[0] if isinstance(authors, list) and authors else (authors or "")
    p = {"query.bibliographic": " ".join(str(x) for x in (title.replace(TRUNC, ""), first, year or "") if x), "rows": 10}
    if mailto:
        p["mailto"] = mailto
    j = http("https://api.crossref.org/works", p)
    recs = [from_crossref(m) for m in ((j or {}).get("message") or {}).get("items", [])]
    return [(sc, r) for r in recs if (sc := title_match(title, r["title"])) and year_ok(year, r) and surname_ok(authors, r)]


def s2_search(title):
    key = os.environ.get("S2_API_KEY")
    j = http("https://api.semanticscholar.org/graph/v1/paper/search/match",
             {"query": title.replace(TRUNC, ""), "fields": "title,authors,year,venue,externalIds,url"},
             headers={"x-api-key": key} if key else None)
    d = ((j or {}).get("data") or [None])[0]
    if not d or not title_match(title, d.get("title")):
        return None
    ids = d.get("externalIds") or {}
    return {"title": d["title"], "authors": [a["name"] for a in d.get("authors", [])], "year": d.get("year"),
            "venue": d.get("venue", ""), "doi": ids.get("DOI"), "eprint": ids.get("ArXiv"), "url": d.get("url")}


def bibtex_for(doi):
    t = http("https://doi.org/" + doi, headers={"Accept": "application/x-bibtex"}, raw=True)
    return t.strip() if t and t.lstrip().startswith("@") else None


# ---------- one reference ----------

ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf|html)/|arxiv:\s*)(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
ACL_RE = re.compile(r"aclanthology\.org/([A-Za-z0-9.\-]+?)(?:\.pdf|\.bib|/)?$")
PII_RE = re.compile(r"/pii/([SB]?[0-9X]{15,17})", re.I)
# journal sites (jclinepi.com, thelancet.com, cell.com ...) show the PII formatted: /article/S0895-4356(21)00240-7/
PII_FMT_RE = re.compile(r"/article/([SB]\d{4}-?\d{3}[\dX]\(\d{2}\)\d{5}-[\dX])", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>?#]+)", re.I)


def resolve(ref, mailto, use_s2):
    out = {"input": ref, "status": "not_found", "source": None, "record": None, "note": ""}
    url, title = ref.get("url") or "", clean_title(ref.get("title") or "")
    doi = ref.get("doi") or (DOI_RE.search(url).group(1) if DOI_RE.search(url) else None)
    if doi:
        doi = re.sub(r"(\.pdf|\.full|/full|\.)$", "", doi.strip(), flags=re.I)
        doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    m = ARXIV_RE.search(url) or ARXIV_RE.search("arxiv:" + (ref.get("arxiv") or ""))
    aid = m.group(1) if m else None
    if doi and doi.lower().startswith("10.48550/arxiv."):
        aid, doi = doi.split(".", 2)[-1], None

    rec, src = None, None
    if doi:
        rec, src = crossref_work(doi, mailto), "crossref"
        if not rec:
            rec, src = datacite_work(doi), "datacite"
    if not rec and aid:
        rec, src = arxiv_work(aid), "arxiv"
    if not rec and (m := ACL_RE.search(url.split("?")[0])):
        rec, src = acl_work(m.group(1)), "aclanthology"
        if rec and rec.get("doi"):
            rec = {**(crossref_work(rec["doi"], mailto) or rec), "url": rec["url"]}
    if not rec and (m := PII_RE.search(url) or PII_FMT_RE.search(url)):
        rec, src = crossref_pii(re.sub(r"[-()]", "", m.group(1)), mailto), "crossref"
    if rec:
        out.update(status="verified", source=src, record=rec)
        if title and not title_match(title, rec["title"]) and overlap(title, rec["title"]) < 0.5:
            out["status"] = "ambiguous"
            out["note"] = "identifier resolves, but to a different title than given; check which one is meant"
        return out

    if title:
        year, authors = ref.get("year"), ref.get("authors")
        cands = [(sc, "crossref", r) for sc, r in crossref_search(title, mailto, year, authors)]
        s2 = s2_search(title) if use_s2 else None
        if s2 and year_ok(year, s2) and surname_ok(authors, s2):
            cands.append((title_match(title, s2["title"]), "semanticscholar", s2))
        exact = [c for c in cands if c[0] == 2]
        if exact and len(norm(title)) < 25 and not authors and not title.endswith(TRUNC):
            out.update(status="ambiguous", source=None, record=None,
                       candidates=[{"source": c[1], **{k: c[2].get(k) for k in ("title", "authors", "year", "venue", "doi")}}
                                   for c in exact][:5],
                       note="title too generic to identify one work; give the first author")
            return out
        if exact:
            # same work if DOIs agree; S2 without a DOI agrees with nothing
            key = lambda c: (c[2].get("doi") or "").lower() or id(c[2])
            works = {}
            for c in exact:
                works.setdefault(key(c), c)
            if len(works) == 1:
                c = next(iter(works.values()))
                cr = [x for x in exact if x[1] == "crossref"]
                c = cr[0] if cr else c  # prefer the DOI registry's record
                out.update(status="verified", source=c[1], record=c[2],
                           note="" if c[2].get("doi") else "no DOI registered (common for CS conference papers)")
                return out
            out.update(status="ambiguous", source=None, record=None,
                       candidates=[{"source": c[1], **{k: c[2].get(k) for k in ("title", "authors", "year", "venue", "doi")}}
                                   for c in works.values()][:5],
                       note="several different works have this exact title; give year and first author")
            return out
        if cands:
            out.update(status="ambiguous", source=None, record=None,
                       candidates=[{"source": c[1], **{k: c[2].get(k) for k in ("title", "authors", "year", "venue", "doi")}}
                                   for c in cands][:5],
                       note="only titles that add or drop a subtitle were found; confirm which work is meant")
            return out
    out["note"] = "no registry record matched; do not fill in details from memory"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="JSON list of references; '-' for stdin")
    for f in ("title", "url", "doi", "arxiv"):
        ap.add_argument("--" + f)
    ap.add_argument("--bibtex", action="store_true", help="fetch BibTeX from doi.org for resolved DOIs")
    ap.add_argument("--s2", action="store_true", help="fall back to Semantic Scholar for titles Crossref misses")
    ap.add_argument("--mailto", default=os.environ.get("CROSSREF_MAILTO"))
    a = ap.parse_args()
    if a.file:
        refs = json.load(sys.stdin if a.file == "-" else open(a.file, encoding="utf-8"))
    else:
        refs = [{k: v for k, v in (("title", a.title), ("url", a.url), ("doi", a.doi), ("arxiv", a.arxiv)) if v}]
        if not refs[0]:
            ap.error("give a file or one of --title/--url/--doi/--arxiv")
    res = []
    for r in refs:
        o = resolve(r, a.mailto, a.s2)
        if a.bibtex and o["status"] == "verified" and (o["record"] or {}).get("doi"):
            o["bibtex"] = bibtex_for(o["record"]["doi"])
        res.append(o)
        time.sleep(0.2)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
    print()
    n = {s: sum(o["status"] == s for o in res) for s in ("verified", "ambiguous", "not_found")}
    print(f"verified {n['verified']}, ambiguous {n['ambiguous']}, not_found {n['not_found']}", file=sys.stderr)


if __name__ == "__main__":
    main()
