<!-- Generated: 2026-05-05 | Updated: 2026-05-05 -->

# parabolic-antenna

## Purpose
パラボラアンテナ(望遠鏡)の台座傾きを 3 観測点(9時 / 12時 / 15時の太陽撮影)から推定し、
計算した太陽位置を像中央に持ってくるための指令補正を行う Python ツール。
標準ライブラリのみで動作する純数学的実装で、外部依存は持たない。

## Key Files
| File | Description |
|------|-------------|
| `README.md` | ユーザー向け概要・使い方・物理モデル要約 |
| `REPORT.md` | 数式導出・解答・コード解説の詳細レポート |
| `3D補正.xlsx` | 元の問題ファイル(参考資料、コードからは未参照) |
| `.gitignore` | `__pycache__/` 等の除外指定 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `pedestal_tilt/` | コアパッケージ。順問題・逆問題・補正計算(see `pedestal_tilt/AGENTS.md`) |
| `examples/` | デモ実行スクリプト(see `examples/AGENTS.md`) |
| `tests/` | stdlib unittest による単体テスト(see `tests/AGENTS.md`) |

## For AI Agents

### Working In This Directory
- 外部依存(numpy, scipy 等)を追加しない。標準ライブラリ(`math`, `dataclasses`, `unittest`)のみで構成する設計方針。
- すべての角度は degrees 単位で扱う。座標系は方位 a(北=0°, 東=90°)・高度 h(地平=0°, 天頂=90°)。
- 数式変更時は必ず `REPORT.md` の対応箇所も更新する。
- Python 3.10+ を前提(`from __future__ import annotations`、PEP 604 `Optional[X]` 等)。

### Testing Requirements
- ルートから `python3 -m unittest tests.test_pedestal_tilt -v` を実行。
- デモ動作確認は `python3 examples/demo.py`。
- 物理モデル変更時は `tests/test_pedestal_tilt.py::TestSolver::test_alt_only_three_obs` で θ=√0.5°, φ=315° の既知解が出ることを確認。

### Common Patterns
- 関数は純粋関数として書き、グローバル状態を持たない。
- 行列・ベクトルは tuple of tuples / tuple で表現(numpy 不使用のため)。
- 角度の正規化は `% 360.0`、対称差は `((x + 540) % 360) - 180` のイディオム。

## Dependencies

### External
- Python 3.10+ 標準ライブラリのみ(`math`, `dataclasses`, `typing`, `unittest`)。

<!-- MANUAL: 手動メモはこの行以下に追加 -->
