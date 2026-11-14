# cite-resolve

[English](README.md)

AI に参考文献を書かせると、DOI や巻号、ページ番号がそれらしく間違っていることがあります。検索ツール（Exa や Claude のウェブ検索など）が返すのは題名と URL くらいなので、残りの書誌情報は AI が記憶で埋めてしまうためです。

cite-resolve は、この書誌情報を Crossref などの登録機関から引いてくるスキルです。AI には書誌を書かせず、引いた結果だけを使わせます。

結果は次の3通りで返ります。

| status | 意味と扱い |
|---|---|
| `verified` | 登録機関の記録と一致した（題名が同じ、または DOI・arXiv ID で引けた）。そのまま使ってよい |
| `ambiguous` | 同じ題名の論文が複数ある、副題だけ違う、DOI と題名が別の論文を指している、など。勝手に選ばず、利用者に確認する |
| `not_found` | 登録機関に見つからなかった。題名と URL だけを書いて「未確認」とし、記憶で補わない |

問い合わせ先は Crossref、DataCite、arXiv API、ACL Anthology、ScienceDirect（PII から Crossref を引く）です。DOI のない情報系の国際会議論文に備えて、Semantic Scholar も補助的に使えます。BibTeX は doi.org から取得します。

Python 3.8 以上の標準ライブラリだけで動き、API キーも要りません。

## インストール

Claude Code では次の2行で入ります。

```text
/plugin marketplace add TMLlaboratory/cite-resolve
/plugin install cite-resolve@cite-resolve
```

Codex など `SKILL.md` を読めるエージェントでは、`skills/cite-resolve/` をスキル用のフォルダにコピーしてください。

スクリプトを直接実行することもできます。

```bash
python3 skills/cite-resolve/scripts/resolve.py --url https://arxiv.org/abs/1706.03762
python3 skills/cite-resolve/scripts/resolve.py --title "Attention Is All You Need" --s2
python3 skills/cite-resolve/scripts/resolve.py refs.json --s2 --bibtex > resolved.json
```

`refs.json` には `{title?, url?, doi?, arxiv?, authors?, year?}` のリストを書きます。同じ題名の別論文を見分けるのに使うので、年と第一著者が分かっていれば入れておいてください。

環境変数は任意です。`CROSSREF_MAILTO` に自分のメールアドレスを入れると Crossref の polite pool が使えます。`S2_API_KEY` を入れると Semantic Scholar の回数制限が緩くなります。

## 精度の目安

実際の Exa の検索結果から論文ページを40件取り出し、題名を手直しせずに（「[PDF]」や「...」での省略、「N/A」、LaTeX のコマンドが混じったまま）試したところ、38件で書誌を確定できました。確定できなかった2件はどちらも OpenReview の論文です。OpenReview の API にはボット対策がかかっているため直接は引かず、Semantic Scholar に収録されていれば見つかります。

## 制限

- 登録機関にないものは引けません。国内学会の予稿集などは DOI がないことが多いです。
- 照合は題名で行います。題名が間違っていると `not_found` になるので、元のページで題名を確かめてから再実行してください。
- 書籍、学位論文、ウェブページは対象外です。

## テスト

```bash
python3 tests/test_offline.py   # ネットワーク不要
```

## ライセンス

MIT ライセンスです。長岡技術科学大学 TML 研究室で開発しました。
