# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## このリポジトリ

Claude Code 用プラグイン（スキル）のマーケットプレイス `yamauchist-plugins`。
ビルド・テスト・lint の仕組みは無く、成果物は `plugin.json` / `marketplace.json` と
スキル（`SKILL.md` ＋ 任意の `references/` `scripts/`）そのもの。ドキュメント類は日本語で書く。

## 公開の仕組み（重要）

- 開発は非公開リポジトリ `yamauchist/claude-plugins-dev`（`origin`）で行う。
- `main` に push されると `.github/workflows/publish-public.yml` が
  公開リポジトリ `yamauchist/claude-plugins` の `main` へそのまま push する。
  作業ブランチや PR は公開されないが、**`main` に入ったものはすべて公開される**。
- そのため、スキルの内容は特定のマシンに依存させない（ローカルの絶対パス、
  個人のフォルダ構成、手元にしか無いファイルを前提にしない）。

## プラグインの構成と追加手順

```
.claude-plugin/marketplace.json     # マーケットプレイス定義（plugins 配列に各プラグインを登録）
plugins/<plugin-name>/
  .claude-plugin/plugin.json        # プラグインのメタデータ
  skills/<skill-name>/SKILL.md      # スキル本体（frontmatter の description が起動判定に使われる）
templates/plugin-template/          # 新規プラグイン用の雛形（マーケットプレイス対象外）
```

新しいプラグインは `templates/plugin-template` を `plugins/<plugin-name>` にコピーして作り、
ルートの `marketplace.json` の `plugins` 配列にもエントリを追加する（詳細は `templates/README.md` と `README.md`）。
追加したら `README.md` の「収録プラグイン」表も更新する。

- `version` は `plugin.json` と `marketplace.json` の両方にあり、`plugin.json` 側が優先される。
  上げるときは両方を揃える。`description` / `keywords` も両者で同じ内容にしている。
- `SKILL.md` の `description` には、どういう依頼で使うかを具体的な言い回し（「〜して」「〜に繋がらない」など）で含める。

## スキルの書き方の慣習

- `SKILL.md` は要点（守ること・手順）に絞り、詳細は `references/*.md` に分けて必要時に読ませる。
- 同梱スクリプトは `$SKILL_DIR/scripts/...` の形で参照し、`$SKILL_DIR` は
  「スキル読み込み時に示される base directory」に置き換えて実行する、と `SKILL.md` に明記する。
- Python スクリプトはリポジトリ側で依存を管理しない。`uv run --with <pkg> python "$SKILL_DIR/scripts/x.py"`
  のように実行時に依存を渡し、使い方はスクリプト冒頭の docstring に書く。

## コミットメッセージ

日本語の [Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/) で書く
（例: `feat(irodori-tts): 短文の duration_scale 指定を追加`）。scope にはプラグイン名を入れる。

**スキル（`SKILL.md` / `references/` / `scripts/`）の変更は `docs` にしない。**
文章であっても Claude の挙動を変えるものなので、内容に応じて `feat`（新しい能力・手順の追加）、
`fix`（誤った指示や不具合の修正）、`perf`（同じ結果をより速く・少ない手数で得る改善）、
`refactor`（挙動を変えない整理）などから選ぶ。`docs` は `README.md` や `CLAUDE.md` のように
配布するスキルの挙動に影響しない文書の変更に使う。

## 動作確認

```
/plugin marketplace add ./
/plugin install <plugin-name>@yamauchist-plugins
```
