# cite-resolve

[English](README.md)

引用文献の書誌を、AI の記憶ではなく、論文の登録先から取ってくるためのスキルです。

検索の道具（Exa や Claude のウェブ検索など）が返すのは、題名と URL だけです。AI がそれを参考文献にするとき、DOI・誌名・巻号・ページ・著者を記憶で補うので、もっともらしい間違いが入ります。`cite-resolve` は、これらを登録先で引いて確かめます。

| status | 意味 |
|---|---|
| `verified` | 登録先の記録が1つに決まった（題名が一致、または渡した DOI・arXiv の番号で引けた）。そのまま使う |
| `ambiguous` | 同じ題名の別の論文がある、副題だけ違う、DOI が別の題名を指している。どれか選ばずに聞く |
| `not_found` | 登録先にない。題名と URL だけで「未確認」として書き、記憶で補わない |

引く先は Crossref、DataCite、arXiv の API、ACL Anthology、ScienceDirect の論文番号（Crossref 経由）です。DOI のない情報系の国際会議の論文には、Semantic Scholar を予備に使えます。BibTeX は doi.org から取ってきます。

Python 3.8 以上の標準ライブラリだけで動きます。API キーは要りません。

## 入れ方

Claude Code の場合：

```text
/plugin marketplace add TMLlaboratory/cite-resolve
/plugin install cite-resolve@cite-resolve
```

`SKILL.md` を読めるほかの AI の道具（Codex など）では、`skills/cite-resolve/` をその道具のスキルのフォルダに置きます。

スクリプトを直接使うこともできます。

```bash
python3 skills/cite-resolve/scripts/resolve.py --url https://arxiv.org/abs/1706.03762
python3 skills/cite-resolve/scripts/resolve.py --title "Attention Is All You Need" --s2
python3 skills/cite-resolve/scripts/resolve.py refs.json --s2 --bibtex > resolved.json
```

`refs.json` は `{title?, url?, doi?, arxiv?, authors?, year?}` の並びです。分かっていれば、年と第一著者も渡してください。同じ題名の別の論文を見分けるのに使います。

環境変数（なくても動きます）：`CROSSREF_MAILTO`（Crossref の polite pool 用に、自分の連絡先）、`S2_API_KEY`（Semantic Scholar の回数の上限を上げる）。

## どのくらい使えるか

実際の Exa の検索結果から論文サイトのもの40件を、検索が返した題名のまま（「[PDF]」、「...」での省略、「N/A」、LaTeX の命令が混じったまま）通したところ、38件を確かめられました。残りの2件は OpenReview の論文です。OpenReview の API はボット対策の確認画面の後ろにあるので、Semantic Scholar に入っているときだけ見つかります。

## できないこと

- 引けるのは登録先にあるものだけです。国内学会の予稿の多くは DOI がありません。
- 題名で照合します。題名を打ち間違えると `not_found` になるので、元のページを見て直してください。
- 本、学位論文、ウェブページは対象外です。

## テスト

```bash
python3 tests/test_offline.py   # ネットにつながずに動く
```

## ライセンス

MIT。長岡技術科学大学 TML 研究室で作りました。
