---
name: cite-resolve
description: >
  Verify references against bibliographic registries (Crossref, DataCite, arXiv, Semantic Scholar)
  instead of writing DOIs, venues, volumes, pages or author lists from memory. Use whenever you are
  about to cite a paper, build a bibliography or BibTeX file, turn web-search results (Exa, web_search,
  etc., which return title and URL but no DOI) into references, or check a reference list someone gave
  you. Triggers: "cite", "reference list", "bibliography", "BibTeX", "DOI", "check these references",
  「引用して」「参考文献」「文献リスト」「書誌を確かめて」「DOIを付けて」「bibを作って」.
---

# cite-resolve: references come from registries, not from memory

Search tools return a title and a URL. Everything else in a reference (DOI, venue, volume, issue,
pages, year, full author list) is easy to get subtly wrong when written from memory, and the errors
look plausible. This skill moves those fields to a lookup.

## The rule

- **Never write a DOI, venue, volume, issue, page range or author list yourself.** Take them from
  `scripts/resolve.py` output, or leave them out.
- A reference the resolver cannot verify is still usable, but say so: write it as
  *unverified* (title + URL only) and tell the user. Do not "fix it up" from memory.
- The title and URL you pass in are lookup keys only. The output record replaces them.

## How to run

Standard library only (Python 3.8+), no API key needed.

```bash
# one reference
python3 scripts/resolve.py --url https://arxiv.org/abs/1706.03762
python3 scripts/resolve.py --title "Deep residual learning for image recognition"

# many: a JSON list of {title?, url?, doi?, arxiv?, authors?, year?}
python3 scripts/resolve.py refs.json --s2 --bibtex > resolved.json
```

- Pass **everything you know**: URL, title, first author, year. Year and first author are what
  separate different papers with the same title.
- `--s2` adds Semantic Scholar as a second source. Use it for computer science: many CS conference
  papers (NeurIPS, ICLR, ICML) have no DOI and are not in Crossref.
- `--bibtex` fetches BibTeX for each resolved DOI from doi.org (the registry's own export).
- Optional environment: `CROSSREF_MAILTO` (an address you choose, for Crossref's polite pool;
  not required), `S2_API_KEY` (higher Semantic Scholar rate limit).

## Reading the output

Each item has a `status`:

| status | meaning | what to do |
|---|---|---|
| `verified` | One registry record with the same title (or the given DOI/arXiv ID) | Use `record` (and `bibtex`) as is |
| `ambiguous` | Several works share the title, the title differs by a subtitle, or the DOI points to a different title | Show `candidates` to the user, or rerun with year and first author. Do not pick one silently |
| `not_found` | No registry record | Cite as unverified (title + URL), or ask the user for the DOI |

`source` says where the record came from. `note` explains anything unusual, such as
"no DOI registered" for conference papers found through Semantic Scholar.

## How it resolves

1. A DOI (given, or inside the URL) → Crossref; if Crossref does not have it, DataCite.
2. An arXiv ID or arXiv URL → the arXiv API. The DOI is `10.48550/arXiv.<id>` (a DataCite DOI;
   Crossref does not hold arXiv). If arXiv records a journal DOI, it is in `journal_doi`: cite the
   published version when the user wants that.
3. An ACL Anthology URL → the Anthology's own BibTeX (and Crossref when it lists a DOI).
   A ScienceDirect `/pii/` URL → Crossref by PII.
4. A title → Crossref search, accepted only on an **exact** title match after year and
   author filters. Search-engine debris is stripped first ("[PDF]", "Review article", "| Site",
   LaTeX macros); a title cut off with "..." is matched as a prefix. Short, generic titles ("Deep learning") without an author are not accepted.
5. With `--s2`, Semantic Scholar's title match is checked too. If it and Crossref point to different
   works, the result is `ambiguous`, not a guess.

## Limits

- Coverage follows the registries. Japanese papers on J-STAGE usually have Crossref DOIs; many
  domestic conference proceedings and CiNii-only items have none and come back `not_found`.
- Matching is by title, so a mistyped title gives `not_found`. Fix the title from the source page
  (not from memory) and rerun.
- OpenReview puts a bot check in front of its API, so OpenReview URLs are not read directly;
  with `--s2` they are usually found through Semantic Scholar, otherwise `not_found`.
- Books, theses and web pages are out of scope; cite them by URL.
- Fields are the registry's spelling, including its mistakes (e.g. a missing space). Keep them.
