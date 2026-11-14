# cite-resolve

[日本語](README.ja.md)

An agent skill that makes references come from bibliographic registries instead of from the
model's memory.

Search tools (Exa, Claude's web search, and others) return a title and a URL. When an LLM turns
that into a reference, it fills in the DOI, venue, volume, pages and author list from memory, and
the errors look plausible. `cite-resolve` moves those fields to a lookup:

| status | meaning |
|---|---|
| `verified` | One registry record matches (same title, or the given DOI / arXiv ID). Use it as is |
| `ambiguous` | Several works share the title, a subtitle differs, or the DOI points to a different title. Ask, don't pick |
| `not_found` | No registry record. Cite as unverified (title + URL); don't fill in from memory |

Sources: Crossref, DataCite, the arXiv API, ACL Anthology, ScienceDirect PII (via Crossref), and
optionally Semantic Scholar (for CS conference papers without DOIs). BibTeX comes from doi.org.

Python 3.8+ standard library only. No API key.

## Install

Claude Code:

```text
/plugin marketplace add TMLlaboratory/cite-resolve
/plugin install cite-resolve@cite-resolve
```

Other agents that read `SKILL.md` (Codex, etc.): copy `skills/cite-resolve/` into the agent's
skills folder.

Or use the script directly:

```bash
python3 skills/cite-resolve/scripts/resolve.py --url https://arxiv.org/abs/1706.03762
python3 skills/cite-resolve/scripts/resolve.py --title "Attention Is All You Need" --s2
python3 skills/cite-resolve/scripts/resolve.py refs.json --s2 --bibtex > resolved.json
```

`refs.json` is a list of `{title?, url?, doi?, arxiv?, authors?, year?}`. Give the year and first
author when you have them: they are what separate different papers with the same title.

Optional environment variables: `CROSSREF_MAILTO` (your address, for Crossref's polite pool),
`S2_API_KEY` (higher Semantic Scholar rate limit).

## How well it works

On 40 scholarly results taken from real Exa searches (titles as the search engine returned them,
with "[PDF]" prefixes, "..." truncation, "N/A" and LaTeX left in), 38 were verified. The other two
were OpenReview pages: OpenReview's API sits behind a bot check, so they are only found when
Semantic Scholar has them.

## Limits

- Coverage follows the registries. Many domestic conference proceedings have no DOI.
- Matching is by title. A mistyped title gives `not_found`; fix it from the source page.
- Books, theses and web pages are out of scope.

## Tests

```bash
python3 tests/test_offline.py   # no network
```

## License

MIT. Made at the TML Laboratory, Nagaoka University of Technology.
