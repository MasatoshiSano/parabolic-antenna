<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-05 | Updated: 2026-05-05 -->

# examples

## Purpose
本問題(東京・春分頃の 9時/12時/15時の太陽撮影、像で alt 方向に ±0.5° のずれを観測)
に対して `pedestal_tilt` パッケージで台座傾きを推定し、補正値・検算を表形式で表示する
デモスクリプト置き場。

## Key Files
| File | Description |
|------|-------------|
| `demo.py` | 既定観測データで `fit_tilt` → `correction` → `forward_pointing` の往復検算を出力。期待値は θ ≈ 0.7071°(=√0.5°), φ = 315° (NW) |

## For AI Agents

### Working In This Directory
- リポジトリルートを `sys.path` に追加してから `pedestal_tilt` を import する形式(`pip install` を不要にするため)。新しいスクリプトでも同じ pattern を踏襲する。
- 観測データは仕様変更があれば `SUN_POSITIONS` と `OBSERVATIONS` を更新する。
- 出力フォーマット(セクション見出しの `=` 区切り、表組み)は `REPORT.md` の出力例と同期させる。
- ユーザー向け文字列は日本語(README/REPORT に揃える)。

### Testing Requirements
- 実行確認:`python3 examples/demo.py`(リポジトリルートから)。
- ロジック検証は `tests/` 側で行う。`demo.py` 自体には assert を書かない。

### Common Patterns
- `_compass_label(phi)` のような表示用ヘルパは module-private(`_` プレフィックス)。
- 数値フォーマットは `f"{x:7.3f}°"` のように桁幅・小数点を固定して表を整える。

## Dependencies

### Internal
- `pedestal_tilt`(`Observation`, `fit_tilt`, `correction`, `forward_pointing`, `image_offset`)。

### External
- なし(標準ライブラリのみ)。

<!-- MANUAL: -->
