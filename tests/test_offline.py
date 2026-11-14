"""Offline checks of title cleaning and matching (no network): python3 tests/test_offline.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "cite-resolve" / "scripts"))
from resolve import TRUNC, clean_title, from_crossref, overlap, surname_ok, title_match  # noqa: E402


def test_clean_title():
    assert clean_title("[1706.03762] Attention Is All You Need") == "Attention Is All You Need"
    assert clean_title("[PDF] Deep Residual Learning for Image Recognition") == "Deep Residual Learning for Image Recognition"
    assert clean_title("Review article The factorial structure of X") == "The factorial structure of X"
    assert clean_title("N/A") == ""
    assert clean_title("Computational Argumentation Quality Assessment in Natural La...").endswith(TRUNC)


def test_title_match():
    assert title_match("Attention is all you need", "Attention Is All You Need.") == 2
    # a subtitle added on one side is not an exact match
    assert title_match("Deep Residual Learning for Image Recognition",
                       "Deep Residual Learning for Image Recognition: A Survey") == 1
    # short titles never match by prefix
    assert title_match("Deep learning", "Deep learning for everyone") == 0
    # a title truncated by a search engine matches by prefix
    t = clean_title("Computational Argumentation Quality Assessment in Natural La...")
    assert title_match(t, "Computational Argumentation Quality Assessment in Natural Language") == 2


def test_filters():
    rec = {"authors": ["Yann LeCun", "Yoshua Bengio"], "year": 2015}
    assert surname_ok("LeCun, Y.", rec) and surname_ok(["Yann LeCun"], rec) and not surname_ok(["Hinton"], rec)
    assert overlap("Attention is all you need", "Attention Is All You Need") == 1.0


def test_crossref_unescape():
    rec = from_crossref({"title": ["A &amp; B"], "container-title": ["Anesthesia &amp; Analgesia"], "DOI": "10.1/x"})
    assert rec["title"] == "A & B" and rec["venue"] == "Anesthesia & Analgesia"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
