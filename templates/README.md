# テンプレート

新しいプラグインを追加するときの雛形。マーケットプレイスには含まれない。

```bash
cp -r templates/plugin-template plugins/<plugin-name>
```

コピー後に以下を更新する。

1. `plugins/<plugin-name>/.claude-plugin/plugin.json` の `name` / `description` / `license`
2. `skills/example-skill/` をスキル名にリネームし、`SKILL.md` の frontmatter と本文を書く
3. ルートの `.claude-plugin/marketplace.json` の `plugins` 配列にエントリを追加する
