# yamauchist-plugins

[yamauchist](https://github.com/yamauchist) が公開している Claude Code 用プラグイン（スキル）のマーケットプレイスです。

## 使い方

Claude Code でマーケットプレイスを追加します。

```
/plugin marketplace add yamauchist/claude-plugins
```

プラグインをインストールします。

```
/plugin install <plugin-name>@yamauchist-plugins
```

更新を取り込むには次を実行します。

```
/plugin marketplace update yamauchist-plugins
```

## 収録プラグイン

| プラグイン | 内容 |
| --- | --- |
| _(準備中)_ | |

## リポジトリ構成

```
.claude-plugin/
  marketplace.json        # マーケットプレイス定義
plugins/
  <plugin-name>/
    .claude-plugin/
      plugin.json         # プラグインのメタデータ
    skills/
      <skill-name>/
        SKILL.md          # スキル本体
templates/
  plugin-template/        # 新規プラグイン用の雛形（マーケットプレイス対象外）
```

## プラグインの追加手順

1. `templates/plugin-template` を `plugins/<plugin-name>` にコピーする
2. `plugin.json` と `SKILL.md` を書く
3. `.claude-plugin/marketplace.json` の `plugins` に以下のようなエントリを追加する

```json
{
  "name": "<plugin-name>",
  "source": "./plugins/<plugin-name>",
  "description": "プラグインの説明",
  "version": "0.1.0",
  "author": { "name": "yamauchist" },
  "category": "productivity",
  "keywords": []
}
```

4. ローカルで動作確認する

```
/plugin marketplace add ./
/plugin install <plugin-name>@yamauchist-plugins
```

`plugin.json` と `marketplace.json` の両方に `version` がある場合は `plugin.json` 側が優先されるため、バージョンを上げるときは両方を揃えること。

## ライセンス

[MIT](LICENSE)
