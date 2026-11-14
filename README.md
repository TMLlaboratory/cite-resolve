# cite-resolve

[日本語](README.ja.md)

Ask an AI to write a reference list and some of the DOIs, volume numbers and page ranges will be
wrong in ways that look right. Search tools (Exa, Claude's web search, and others) return little
more than a title and a URL, so the model fills in the rest from memory.

cite-resolve is a skill that looks those details up in bibliographic registries such as Crossref.
The model doesn't write bibliographic fields itself; it uses what the lookup returns.

Each reference comes back with one of three statuses:

| status | Meaning and what to do |
|---|---|
| `verified` | Matches a registry record (same title, or found by DOI or arXiv ID). Use it as is |
| `ambiguous` | Several papers share the title, only a subtitle differs, or the DOI and the title point to different papers. Don't pick one; ask the user |
| `not_found` | Not in any registry. Give the title and URL, mark it unverified, and don't fill in the rest from memory |

It queries Crossref, DataCite, the arXiv API, ACL Anthology and ScienceDirect (looking up the
PII in Crossref). Semantic Scholar is available as a fallback for CS conference papers that have
no DOI. BibTeX is fetched from doi.org.

It runs on the Python 3.8+ standard library and needs no API key.

## Installation

In Claude Code:

```text
/plugin marketplace add TMLlaboratory/cite-resolve
/plugin install cite-resolve@cite-resolve
```

For Codex and other agents that read `SKILL.md`, copy `skills/cite-resolve/` into the agent's
skills folder.

You can also run the script directly:

```bash
python3 skills/cite-resolve/scripts/resolve.py --url https://arxiv.org/abs/1706.03762
python3 skills/cite-resolve/scripts/resolve.py --title "Attention Is All You Need" --s2
python3 skills/cite-resolve/scripts/resolve.py refs.json --s2 --bibtex > resolved.json
```

`refs.json` is a list of `{title?, url?, doi?, arxiv?, authors?, year?}`. Include the year and
first author when you know them; they are how papers with the same title are told apart.

Both environment variables are optional. Set `CROSSREF_MAILTO` to your email address to use
Crossref's polite pool, and `S2_API_KEY` for a higher Semantic Scholar rate limit.

## How accurate it is

We took 40 paper pages from real Exa search results and passed their titles in unedited, with
"[PDF]" prefixes, "..." truncation, "N/A" and LaTeX commands still in them. 38 were resolved.
The other two were OpenReview papers. OpenReview's API is behind a bot check, so cite-resolve
doesn't query it directly; those papers are found only if Semantic Scholar has them.

## Limitations

- Only works that a registry holds can be resolved. Many domestic conference proceedings have
  no DOI.
- Matching is by title. A wrong title gives `not_found`, so check the title on the original page
  and run it again.
- Books, theses and web pages are out of scope.

## Tests

```bash
python3 tests/test_offline.py   # no network needed
```

## License

MIT. Developed at the TML Laboratory, Nagaoka University of Technology.
