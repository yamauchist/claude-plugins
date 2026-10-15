# サーバーのセットアップと起動

[Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) をそのまま使う（ラッパーは不要）。
`irodori-tts` 本体は依存として git から入るので、**Irodori-TTS 本体を別途 clone する必要はない。**

動作確認済みの上流コミット: `841fb7c`。

## インストール

```bash
git clone https://github.com/Aratako/Irodori-TTS-Server.git
cd Irodori-TTS-Server
uv sync --extra cu128        # NVIDIA。AMD は --extra rocm、CPU は --extra cpu
```

## 起動

GPU の場合:

```bash
IRODORI_MODEL_PRECISION=bf16 IRODORI_CODEC_PRECISION=bf16 \
IRODORI_MODEL_DEVICE=cuda IRODORI_CODEC_DEVICE=cuda IRODORI_PRELOAD=true \
uv run --no-sync python -m irodori_openai_tts --host 127.0.0.1 --port 8000
```

PowerShell の場合:

```powershell
Set-Location "<Irodori-TTS-Server のパス>"
$env:IRODORI_MODEL_PRECISION = "bf16"
$env:IRODORI_CODEC_PRECISION = "bf16"
$env:IRODORI_MODEL_DEVICE = "cuda"
$env:IRODORI_CODEC_DEVICE = "cuda"
$env:IRODORI_PRELOAD = "true"
& uv run --no-sync python -m irodori_openai_tts --host 127.0.0.1 --port 8000
```

CPU の場合は `IRODORI_MODEL_DEVICE` / `IRODORI_CODEC_DEVICE` を `cpu` にし、
精度の環境変数は指定しない（既定の fp32 のまま）。

| 指定 | 理由 |
|---|---|
| `--port 8000` | **既定は 8088。** このスキルの例はすべて 8000 を前提にしている |
| `IRODORI_MODEL_PRECISION=bf16` | **既定は fp32。** GPU では bf16 にするとメモリが減り速くなる |
| `IRODORI_PRELOAD=true` | 起動時にモデルを読む。読み込みの失敗を最初の合成ではなく起動時に知れる |

Claude Code から起動する場合は、起動コマンドを `run_in_background: true` で直接実行するのが確実。
止めるときはそのバックグラウンドタスクを止める。

起動には数分かかる（初回はモデルのダウンロードを含む。2回目からは Hugging Face のキャッシュを使う）。

## 状態確認

```bash
curl -s http://127.0.0.1:8000/health      # 応答 JSON の runtime.loaded が true か見る
```

```powershell
try { (Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 3).runtime.loaded } catch { "down" }
```

`/health` はモデルを読まずに答えるので、起動途中でも 200 が返る。
ステータスコードではなく、応答 JSON の `runtime.loaded` が `true` になっているかで合成できるかを判断する。
読み込んだモデル名も返る。

動作確認は参照なしで1本合成する:

```powershell
$body = @{
  model = "irodori-tts"; voice = "none"; response_format = "wav"
  input = "テストです。"
  irodori = @{ caption = "落ち着いた若い女性の声。"; seed = 42 }
} | ConvertTo-Json -Compress -Depth 4
Invoke-WebRequest "http://127.0.0.1:8000/v1/audio/speech" -Method POST `
  -ContentType "application/json" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  -OutFile "test.wav" -UseBasicParsing
```

## エンドポイント

| | 内容 |
|---|---|
| `GET /health` | 状態と設定。モデルは読まない |
| `POST /v1/audio/speech` | 合成。音声をバイト列で返す |
| `GET/POST /v1/audio/voices` | サーバーの `voices/` に置いた参照音声の一覧・登録 |

## 呼び出し側の注意

- 合成は同期で、応答が来るまで何も届かない。HTTP クライアントのタイムアウトを短くしすぎない
  （無通信5分程度にする）
- まとめて合成する前に `/health` を1回叩き、起動していなければそこで中止する。
  起動していないまま流すと、全本ぶんの接続エラーが並ぶだけになる
- 後段で ffmpeg などの外部ツールを使うなら、**合成を始める前に**存在を確認する（数十本作ってから失敗しないように）

## よく出るもの

- **`VIRTUAL_ENV does not match the project environment path` の警告は無害。**
  別の仮想環境が有効なままだと出る。uv は `.venv` を正しく使う（気になるなら `VIRTUAL_ENV` を空にしてから起動する）
- **`text became empty after normalization`（400）** — 記号だけの本文を送った。
  [SKILL.md](../SKILL.md) の「短い文・記号だけの文」を参照
- 繋がらない — ポートが 8088（既定）のまま起動していないか確認する
