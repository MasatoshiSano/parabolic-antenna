<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-05 | Updated: 2026-05-05 -->

# pedestal_tilt

## Purpose
台座傾きの順問題(指令 → 実指向)、逆問題(観測ずれ → 傾きパラメータ推定)、
補正計算(真位置 → 指令値)を提供するコアパッケージ。
すべて純 Python 実装で、numpy 等の外部依存を持たない。

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 公開 API のバレル(2軸: `Observation`, `fit_tilt`, `correction`, `forward_pointing`, `image_offset`, `tilt_rotation_matrix` / 3軸: `forward_3axis`, `ik_3axis`, `ik_3axis_hold`, `plan_pass`, `max_azimuth_step` / 可動域: `JointLimits`, `within_limits`, `pass_fits_limits`, `peak_abs_xel`) |
| `geometry.py` | 順問題・像ずれ・補正計算。`tilt_rotation_matrix`(Rodrigues 公式による厳密 3D 回転)、`forward_pointing`、`image_offset`(線形近似)、`correction`(線形近似) |
| `solver.py` | 観測データから (θ_t, φ_t) を最小二乗推定。`Observation` データクラス、`fit_tilt`、内部 `_solve_2x2` |
| `three_axis.py` | 3軸(Az–El–XEl)マウントの運動学。`forward_3axis`(順, ξ=0 で `forward_pointing` に一致)、`ik_3axis`/`ik_3axis_hold`(逆, 方位保持で冗長性解決)、`plan_pass`(パスの関節指令列)、`max_azimuth_step`。天頂キーホール除去。関節可動域: `JointLimits`(XEl既定[-45,45]=中立中央), `within_limits`/`pass_fits_limits`/`peak_abs_xel`。 |

## For AI Agents

### Working In This Directory
- 角度はすべて degrees 単位で外部 API に出し、内部計算でのみ radians に変換する(`_deg2rad` / `_rad2deg`)。
- 行列・ベクトルは tuple of tuples / tuple で持つ(numpy 不使用)。型エイリアス `Vec3`, `Mat3` は `geometry.py` で定義。
- `forward_pointing` は厳密 3D 回転、`image_offset`/`correction` は線形近似(θ ≪ 1 rad、h < 70° で誤差 < 0.05° 程度)。新しい関数を追加する際もこの区別を踏襲する。
- `three_axis.py` の運動学(`forward_3axis`/`ik_*`)はすべて**厳密 3D 回転**で、線形近似は使わない。順運動学は `u = Rz(a)·Ey(h)·Rz(ξ)·x̂` を `R_tilt` に通す合成。`three_axis` は `geometry` の `tilt_rotation_matrix`/`_altaz_to_unit`/`_unit_to_altaz`/`_matvec` を再利用し、座標規約の単一情報源を保つ(数式を変えるときは両モジュールで整合させる)。
- 不変条件:`forward_3axis(a, h, 0, θ, φ) == forward_pointing(a, h, θ, φ)`(XEl=0 で 2軸に厳密一致)。XEl 軸は body-z まわり(天頂で水平軸になり横倒し)。
- 線形パラメータ化:`p = θ cosφ`, `q = θ sinφ` で線形最小二乗 → `θ = hypot(p,q)`, `φ = atan2(q,p) mod 360`。
- `Observation.dac_image_deg` は任意(`None` の場合は alt 方程式のみ追加)。3 観測点で alt のみでも 2 未知数を解ける。
- 公開 API を増やす場合は `__init__.py` の `__all__` にも追加する。

### Testing Requirements
- `python3 -m unittest tests.test_pedestal_tilt -v` で全テストが通ること。
- 数式変更時は `tests/test_pedestal_tilt.py` の以下を特に確認:
  - `TestGeometry::test_rotation_matrix_orthogonal`(R·Rᵀ = I)
  - `TestSolver::test_round_trip_recovers_known_tilt`(順 → 逆の往復)
  - `TestSolver::test_alt_only_three_obs`(既知解 θ=√0.5°, φ=315°)

### Common Patterns
- 純粋関数。モジュール状態・副作用なし。
- 方位の正規化:`a % 360.0`。差分の対称化:`((x - y + 540) % 360) - 180`。
- 数値安定性:`asin` の引数は `max(-1, min(1, ...))` でクリップ。`_solve_2x2` で `|det| < 1e-15` を特異と判定。

## Dependencies

### Internal
- `solver.py` は `Observation` のみを公開し、像ずれ予測式の係数生成は内部でハードコード(`geometry.image_offset` の式と一致している必要がある)。

### External
- Python 標準ライブラリのみ(`math`, `dataclasses`, `typing`, `__future__`)。

<!-- MANUAL: -->
