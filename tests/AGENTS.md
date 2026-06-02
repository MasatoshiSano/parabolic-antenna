<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-05 | Updated: 2026-05-05 -->

# tests

## Purpose
`pedestal_tilt` パッケージの単体テスト。標準ライブラリの `unittest` のみを使用し、
順問題・逆問題・補正計算・物理直観のスポットチェックをカバーする。

## Key Files
| File | Description |
|------|-------------|
| `test_pedestal_tilt.py` | 5 つの TestCase: `TestGeometry`(回転行列・順問題・補正の往復)、`TestSolver`(既知解復元・本問題データ・優決定系)、`TestPhysicalIntuition`(北傾き南中で alt が下にずれる等)、`TestThreeAxis`(3軸: 2軸への帰着・方位保持 IK 往復・天頂有限・パスで方位凍結・中立中央の可動域)、`TestActuatorTripod`(3本アクチュエータ: 脚長 golden・home対称・到達円錐) |

## For AI Agents

### Working In This Directory
- pytest 等を導入しない。stdlib `unittest` のみ。
- 新規テストもリポジトリルートを `sys.path` に追加するイディオムを踏襲。
- 浮動小数点比較は `assertAlmostEqual(places=...)` を使用。回転行列直交性などの数学的恒等式は `places=10` 以上を目安に。
- 線形近似(`correction` / `image_offset`)に対するテストは θ < 1°、h < 70° の範囲で誤差 < 0.05° を許容。
- 方位差は `((a - b + 540) % 360) - 180` で対称化してから比較。

### Testing Requirements
- 実行:`python3 -m unittest tests.test_pedestal_tilt -v`(リポジトリルートから)。
- 全テストがパスすること。失敗時は数式と `geometry.py` / `solver.py` を必ず照合する(テスト側ではなくロジック側を疑う)。

### Common Patterns
- 「既知パラメータで観測生成 → ソルバで復元」のラウンドトリップ検証(`test_round_trip_recovers_known_tilt`)。
- 「ゼロ傾きで恒等」「直交性」「特定方位での消滅」の代表ケースで物理を pin。

## Dependencies

### Internal
- `pedestal_tilt` パッケージ全公開 API。

### External
- Python 標準ライブラリのみ(`unittest`, `math`)。

<!-- MANUAL: -->
