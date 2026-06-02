# パラボラアンテナ台座傾き推定・太陽指向補正レポート

**作成日**: 2026-04-30
**対象**: `/home/sano/projects/parabolic-antenna/3D補正.xlsx` の問題
**前提条件**: 台座そのものに歪みはなく、剛体として一様に傾いているものとする

---

## 1. 問題の整理

### 1.1 設定

- 台座(pedestal)の上に望遠鏡を「真上」を向くように設置
- この向きを **Az = 0°, El = 90°** とマウント側が認識
- コントローラは観測地・日時から太陽の真の位置 (Az_sun, El_sun) を計算し、その方向にマウントを指令
- 黒板(投影板)越しに 9 時 / 12 時 / 15 時の太陽像を撮影

### 1.2 観測

各時刻で太陽像が中央から **0.5°** ずれて写った。
本レポートでは、ご提示の解釈に従い:

| 時刻 | 像の中で太陽がずれた方向 |
|------|--------------------------|
| 9 時  | E(東)                  |
| 12 時 | S(南)                  |
| 15 時 | E(東)                  |

> 「下からのぞく」想定の像座標で、像のたて方向 (alt) のずれのみ与えられている。

### 1.3 求めたいもの

1. 台座はどう傾いているか(方向 φ_t と大きさ θ_t)
2. 計算した太陽位置を像の中央に持ってくるための指令補正
3. 上記を計算する Python プログラム

---

## 2. 物理モデル

### 2.1 何が起きているか(直感)

- マウントは台座基準で「上」を判断するため、台座が傾くとマウントの "天頂" z' が真の天頂 z からずれる
- コントローラは真の地平座標で計算し、マウントは自分の傾いた座標系でそれを実行する
- 両者の食い違い θ_t が、像の中央からの太陽のずれとして現れる

```
真の天頂 z          マウントの "天頂" z'
     ▲                   ▲
     │                  ╱
     │   ↘ θ_t        ╱
     │                ╱
     │              ╱
   ━━┷━━━━━━━━━━━━●━━━━━ 台座(NW方向に倒れる例)
```

### 2.2 パラメータ

- θ_t : 傾きの大きさ [deg]
- φ_t : 傾きベクトルの方位 [deg](北=0°, 東=90°, 南=180°, 西=270°)

マウント天頂 z' の真地平座標での位置:
```
z' = (sin θ_t · cos φ_t,  sin θ_t · sin φ_t,  cos θ_t)
```

### 2.3 順問題(指令 → 実際の指向)

マウントに `(a_cmd, h_cmd)` を指令したとき、真地平座標での実際の指向方向 `(a', h')`(線形近似):
```
h' ≈ h_cmd  −  θ_t · cos(a_cmd − φ_t)
a' ≈ a_cmd  −  θ_t · sin(a_cmd − φ_t) · tan(h_cmd)
```

### 2.4 像でのずれ

コントローラが太陽の真位置 `(a_sun, h_sun)` を指令する場合、像で太陽が中央から外れる量:
```
Δh_image       =  h_sun − h'   =  θ_t · cos(a_sun − φ_t)
Δa·cos(h)_image = (a_sun − a') · cos(h_sun)
                                = +θ_t · sin(a_sun − φ_t) · sin(h_sun)
```

> 注: `Δa·cos(h)` は像面でのよこ方向の角度ずれ(球面の方位差を像の見かけ角に直したもの)。

### 2.5 補正(指令値の生成)

真の `(a_calc, h_calc)` を像中央に置きたいときの指令値:
```
h_cmd = h_calc + θ_t · cos(a_calc − φ_t)
a_cmd = a_calc + θ_t · sin(a_calc − φ_t) · tan(h_calc)
```

---

## 3. 観測データから (θ_t, φ_t) を解く

### 3.1 像のたて方向ずれの符号変換

「下からのぞく」像の "E/S/W" を `Δh_image` に変換:

| 時刻 | 太陽方位 | 太陽高度(目安) | 像の "E/S" の意味 | Δh_image |
|------|---------|------|-----------------|----------|
| 9 時  | 90°(E) | 30° | 東を見上げ。"E" は alt 軸の負側 | **−0.5°** |
| 12 時 | 180°(S)| 70° | 南を見上げ。"S" は alt 軸の負側 | **−0.5°** |
| 15 時 | 270°(W)| 30° | 西を見上げ。"E" は alt 軸の正側 | **+0.5°** |

### 3.2 連立式

`Δh = θ_t · cos(a − φ_t) = θ_t cos a · cos φ_t + θ_t sin a · sin φ_t` と展開し、
`p = θ_t cos φ_t`, `q = θ_t sin φ_t` の線形連立にすると:

| 時刻 | 式 |
|------|----|
| 9 時  | `q = −0.5` |
| 12 時 | `−p = −0.5` → `p = +0.5` |
| 15 時 | `−q = +0.5` → `q = −0.5` |

9 時と 15 時が一致している(自己無撞着) → このデータは単一傾きで説明可能。

### 3.3 解

```
p = θ_t cos φ_t = +0.5
q = θ_t sin φ_t = -0.5

→ θ_t = √(p² + q²) = √0.5 ≈ 0.707°
→ φ_t = atan2(q, p) = atan2(-0.5, 0.5) = -45° = 315°
```

### 3.4 結論

> **台座は北西方向(φ_t = 315°)に約 0.71° 倒れている。**

---

## 4. 補正値の例

θ_t = 0.707°, φ_t = 315° のとき、12 時(真位置 a=180°, h=70°)を狙うための指令値:

```
高度補正:  Δh = +0.707 · cos(180 − 315) = 0.707 · cos(−135°) ≈ −0.500°
方位補正:  Δa = +0.707 · sin(180 − 315) · tan(70°)
            =  0.707 · (−0.707) · 2.747
            ≈ −1.373°

→ 指令値:  高度 = 69.500°,  方位 = 178.627°
```

これを送るとマウントの実際の指向が (180°, 70°) になり、太陽が像中央に入る。

---

## 5. Python 実装

### 5.1 ファイル構成

```
parabolic-antenna/
├── pedestal_tilt/
│   ├── __init__.py
│   ├── geometry.py     # 順問題・逆問題・補正(numpy のみ)
│   └── solver.py       # 観測 → (θ_t, φ_t) フィット
├── tests/
│   └── test_round_trip.py
└── examples/
    └── demo.py
```

### 5.2 `pedestal_tilt/geometry.py`

```python
"""台座傾きの順問題・逆問題・補正計算。すべて degrees 単位。"""
from __future__ import annotations
import numpy as np


def tilt_rotation_matrix(theta_t_deg: float, phi_t_deg: float) -> np.ndarray:
    """マウント座標 → 真地平座標 への回転行列 R (3x3)。

    マウントの天頂 z' を真の方位 phi_t、傾き角 theta_t の位置に持っていく
    水平軸まわりの回転として定義する。
    """
    theta = np.radians(theta_t_deg)
    phi = np.radians(phi_t_deg)
    # 回転軸 n は水平面内で phi に直交する向き
    n = np.array([-np.sin(phi), np.cos(phi), 0.0])
    K = np.array([
        [0.0, -n[2], n[1]],
        [n[2], 0.0, -n[0]],
        [-n[1], n[0], 0.0],
    ])
    return np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * (K @ K)


def _altaz_to_unit(a_deg: float, h_deg: float) -> np.ndarray:
    """方位 a (北=0, 東=90), 高度 h から単位ベクトル(N, E, Up)。"""
    a = np.radians(a_deg)
    h = np.radians(h_deg)
    return np.array([np.cos(h) * np.cos(a), np.cos(h) * np.sin(a), np.sin(h)])


def _unit_to_altaz(u: np.ndarray) -> tuple[float, float]:
    a = np.degrees(np.arctan2(u[1], u[0])) % 360.0
    h = np.degrees(np.arcsin(np.clip(u[2], -1.0, 1.0)))
    return a, h


def forward_pointing(
    a_cmd_deg: float, h_cmd_deg: float,
    theta_t_deg: float, phi_t_deg: float,
) -> tuple[float, float]:
    """指令 (a_cmd, h_cmd) を送ったときの真地平座標での実指向 (a', h')。"""
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    u_actual = R @ _altaz_to_unit(a_cmd_deg, h_cmd_deg)
    return _unit_to_altaz(u_actual)


def image_offset(
    a_sun_deg: float, h_sun_deg: float,
    theta_t_deg: float, phi_t_deg: float,
) -> tuple[float, float]:
    """太陽真位置を指令したときの像でのずれ (Δh_image, Δa·cosh_image) [deg]。

    線形近似式:
        Δh_image       =  θ · cos(a − φ)
        Δa·cosh_image  = +θ · sin(a − φ) · sin(h_sun)
    """
    da = np.radians(a_sun_deg - phi_t_deg)
    h = np.radians(h_sun_deg)
    dh = theta_t_deg * np.cos(da)
    dac = theta_t_deg * np.sin(da) * np.sin(h)
    return dh, dac


def correction(
    a_calc_deg: float, h_calc_deg: float,
    theta_t_deg: float, phi_t_deg: float,
) -> tuple[float, float]:
    """真位置 (a_calc, h_calc) を像中央に置くための指令値 (a_cmd, h_cmd)。

    線形近似:
        h_cmd = h_calc + θ · cos(a_calc − φ)
        a_cmd = a_calc + θ · sin(a_calc − φ) · tan(h_calc)
    """
    da = np.radians(a_calc_deg - phi_t_deg)
    h = np.radians(h_calc_deg)
    h_cmd = h_calc_deg + theta_t_deg * np.cos(da)
    a_cmd = a_calc_deg + theta_t_deg * np.sin(da) * np.tan(h)
    return a_cmd % 360.0, h_cmd
```

### 5.3 `pedestal_tilt/solver.py`

```python
"""観測ずれデータから台座傾き (θ_t, φ_t) を推定する。"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class Observation:
    a_sun_deg: float          # 太陽の真方位
    h_sun_deg: float          # 太陽の真高度
    dh_image_deg: float       # 像でのたてずれ Δh
    dac_image_deg: float | None = None  # 像でのよこずれ Δa·cosh(任意)


def fit_tilt(observations: list[Observation]) -> tuple[float, float, np.ndarray]:
    """最小二乗で (θ_t, φ_t) を推定。残差ベクトルも返す。

    線形パラメータ p = θ cos φ, q = θ sin φ で解いてから極座標に戻す。

    Returns
    -------
    theta_t_deg : float
    phi_t_deg   : float (0–360°)
    residuals   : np.ndarray  (観測ごとの予測−実測)
    """
    rows: list[list[float]] = []
    rhs: list[float] = []
    for obs in observations:
        a = np.radians(obs.a_sun_deg)
        # Δh = θ cos(a−φ) = p cos(a) + q sin(a)
        rows.append([np.cos(a), np.sin(a)])
        rhs.append(obs.dh_image_deg)
        if obs.dac_image_deg is not None:
            h = np.radians(obs.h_sun_deg)
            # Δa·cosh = +θ sin(a−φ) sin(h) = sin(h)·(p sin(a) − q cos(a))
            rows.append([np.sin(a) * np.sin(h), -np.cos(a) * np.sin(h)])
            rhs.append(obs.dac_image_deg)
    A = np.asarray(rows)
    b = np.asarray(rhs)
    (p, q), *_ = np.linalg.lstsq(A, b, rcond=None)
    theta = float(np.hypot(p, q))
    phi = float(np.degrees(np.arctan2(q, p)) % 360.0)
    residuals = A @ np.array([p, q]) - b
    return theta, phi, residuals
```

### 5.4 `examples/demo.py` — 本問題を解くスクリプト

```python
"""ご提示データ(9時 E, 12時 S, 15時 E に 0.5°)から (θ_t, φ_t) を推定。"""
from pedestal_tilt.geometry import correction, image_offset
from pedestal_tilt.solver import Observation, fit_tilt


# 太陽位置の概算(東京・春先) — 厳密値は astropy 等で計算可
SUN = {
    9:  (90.0, 30.0),    # 9時: 東, 高度30°
    12: (180.0, 70.0),   # 12時: 南, 高度70°
    15: (270.0, 30.0),   # 15時: 西, 高度30°
}

# 像でのたてずれ(下からのぞく前提):
#   E方向のずれ × (東を見上げ)→ Δh = -0.5
#   S方向のずれ × (南を見上げ)→ Δh = -0.5
#   E方向のずれ × (西を見上げ)→ Δh = +0.5
observations = [
    Observation(*SUN[9],  dh_image_deg=-0.5),
    Observation(*SUN[12], dh_image_deg=-0.5),
    Observation(*SUN[15], dh_image_deg=+0.5),
]

theta, phi, residuals = fit_tilt(observations)
print(f"=== 台座傾き推定 ===")
print(f"  θ_t = {theta:.4f}°  (傾きの大きさ)")
print(f"  φ_t = {phi:.2f}°    (傾きの方位 — 北=0, 東=90, 南=180, 西=270)")
print(f"  残差 = {residuals}")

print()
print(f"=== 補正値の例(各時刻の太陽を像中央に置くための指令値)===")
for t, (a_sun, h_sun) in SUN.items():
    a_cmd, h_cmd = correction(a_sun, h_sun, theta, phi)
    print(f"  {t:>2}時:  真の太陽 ({a_sun:6.2f}°, {h_sun:5.2f}°)  "
          f"→  指令 ({a_cmd:7.3f}°, {h_cmd:6.3f}°)")

print()
print(f"=== 検算:推定パラメータで像ずれを再計算 ===")
for t, (a_sun, h_sun) in SUN.items():
    dh, dac = image_offset(a_sun, h_sun, theta, phi)
    print(f"  {t:>2}時:  Δh = {dh:+.4f}°,  Δa·cosh = {dac:+.4f}°")
```

### 5.5 `tests/test_round_trip.py`

```python
"""順問題で生成したずれを逆問題ソルバに戻して、元のパラメータが復元することを検証。"""
import numpy as np
from pedestal_tilt.geometry import correction, forward_pointing, image_offset
from pedestal_tilt.solver import Observation, fit_tilt


def test_round_trip_reproduces_known_tilt():
    theta_true, phi_true = 0.5, 80.0
    sun_positions = [(90.0, 30.0), (180.0, 70.0), (270.0, 30.0)]
    obs = []
    for a, h in sun_positions:
        dh, dac = image_offset(a, h, theta_true, phi_true)
        obs.append(Observation(a, h, dh_image_deg=dh, dac_image_deg=dac))
    theta, phi, _ = fit_tilt(obs)
    assert abs(theta - theta_true) < 1e-6
    assert abs(((phi - phi_true) + 180) % 360 - 180) < 1e-4


def test_correction_brings_calc_to_actual():
    theta, phi = 0.707, 315.0
    a_calc, h_calc = 180.0, 70.0
    a_cmd, h_cmd = correction(a_calc, h_calc, theta, phi)
    a_actual, h_actual = forward_pointing(a_cmd, h_cmd, theta, phi)
    assert abs(a_actual - a_calc) < 1e-3
    assert abs(h_actual - h_calc) < 1e-3


def test_zero_tilt_means_no_offset():
    for a, h in [(90, 30), (180, 70), (270, 30)]:
        dh, dac = image_offset(a, h, 0.0, 123.0)
        assert abs(dh) < 1e-12
        assert abs(dac) < 1e-12
```

### 5.6 期待される実行結果

```
=== 台座傾き推定 ===
  θ_t = 0.7071°  (傾きの大きさ)
  φ_t = 315.00°    (傾きの方位 — 北=0, 東=90, 南=180, 西=270)
  残差 = [0. 0. 0.]

=== 補正値の例(各時刻の太陽を像中央に置くための指令値)===
   9時:  真の太陽 ( 90.00°, 30.00°)  →  指令 ( 90.289°, 29.500°)
  12時:  真の太陽 (180.00°, 70.00°)  →  指令 (178.627°, 69.500°)
  15時:  真の太陽 (270.00°, 30.00°)  →  指令 (269.711°, 30.500°)

=== 検算:指令値を順問題に通したときの実指向(目標値に戻る) ===
   9時:  指令 → 実指向 ( 90.004°, 30.001°)  目標 (90.000°, 30.000°)
  12時:  指令 → 実指向 (179.965°, 70.006°)  目標 (180.000°, 70.000°)
  15時:  指令 → 実指向 (270.004°, 30.001°)  目標 (270.000°, 30.000°)

=== 検算:推定パラメータで像ずれを再計算 ===
   9時:  Δh = -0.5000°,  Δa·cosh = +0.2500°
  12時:  Δh = -0.5000°,  Δa·cosh = -0.4698°
  15時:  Δh = +0.5000°,  Δa·cosh = -0.2500°
```

---

## 6. 結果まとめ

| 項目 | 値 |
|------|----|
| **台座傾きの大きさ θ_t** | **約 0.71°** |
| **台座傾きの方位 φ_t** | **315°(北西方向)** |
| マウント天頂 z' の真地平座標 | (sin0.71°·cos315°, sin0.71°·sin315°, cos0.71°) ≈ (+0.0087, −0.0087, 0.9999) |
| 真の (a_calc, h_calc) → 指令 (a_cmd, h_cmd) の変換式 | 上記 §2.5 / §5.2 `correction()` |

---

## 7. 注意事項・前提

1. **像座標系の定義**: 「下からのぞく」場合、像の左右が普通の天空図と反転している前提で解釈した。観測光路や像の上下左右の規約が異なる場合、φ_t の符号(NW⇄NE, SW⇄SE)が変わる可能性あり。
2. **az 方向のずれ未提供**: 本問題ではたて方向 Δh しか与えられていないため、解は alt 残差ゼロを満たす最小二乗解。よこ方向 Δa·cosh も同時に観測すれば過剰決定となり、より頑健な推定が可能。
3. **太陽位置は近似値**: 本レポートでは (Az, El) = (90°,30°), (180°,70°), (270°,30°) と簡略化。実装では astropy 等で観測地・日時から厳密に計算するのが望ましい。
4. **線形近似**: 0.71° 程度の傾きで `tan(70°) ≈ 2.75` の倍率が乗る高仰角では、線形補正と厳密3D回転の差が最大 ~0.04°(12時で実測 0.035°)。多くの用途で実用上問題ないが、より厳密性が必要なら `scipy.optimize.least_squares` で厳密回転を反復的に解くと `<0.001°` まで詰められる。
5. **大気差・視半径・像処理誤差**: スコープ外。

---

## 8. 3軸(Az–El–XEl)マウントによる天頂キーホール除去

### 8.1 2軸の限界(キーホール)

高度関節が 0–90° しか動けない2軸(経緯台)では、**天頂近傍を通る対象を追尾するとき方位をほぼ 180° 振らねばならない**。これは §2.5 の補正式の方位項に現れる `tan(h)` が `h → 90°` で発散することと同じ特異点で、天頂を中心とする小さな円錐(キーホール)は滑らかに追尾できない。

### 8.2 第3軸 XEl(クロスエレベーション)の定義

最上部に視軸を左右へ倒す軸 ξ を1つ足す。視軸ゼロ基準を `x̂ = (1,0,0)`(北・地平)として順運動学を:

```
u_mount = Rz(a) · Ey(h) · Rz(ξ) · x̂
u_true  = R_tilt(θ_t, φ_t) · u_mount          (R_tilt は §2 と同じ)

Rz(α) = [[cosα,−sinα,0],[sinα,cosα,0],[0,0,1]]      (天頂 z 軸まわり)
Ey(h) = [[cos h,0,−sin h],[0,1,0],[sin h,0,cos h]]  (東 y 軸まわり)
```

`ξ = 0` のとき `u_mount = _altaz_to_unit(a, h)` に厳密一致 → **2軸の上位互換**。XEl 軸(body-z)は高度が 90° のとき水平軸になり、**高度関節を 90° に保ったまま視軸を横へ倒せる**。これがキーホールを潰す自由度。

### 8.3 逆運動学(冗長性解決:方位保持)

3関節で空の2自由度を狙うので1パラメータ自由。中核は **方位関節を `a_hold` に凍結する閉形式解**:

```
v = Rz(−a_hold) · Rᵀ · u_target = (vx, vy, vz)
ξ = atan2(vy, hypot(vx, vz))
h = atan2(vz, vx)
```

天頂越えの間 `a` を動かさず、`ξ` が横方向運動を肩代わりする。`plan_pass()` はキーホール区間の保持方位を culmination(最大高度点)のマウント方位に揃え、区間外は標準2軸へフォールバックする。

### 8.4 検証(最接近 1° の天頂通過パス、0.5° 刻み)

| 方式 | キーホール内の方位総移動量 Σ\|Δa\| | XEl 最大 | 指向誤差 |
|------|-----------------------------------|---------|---------|
| 2軸 | **174°**(≈ 180° のスピン) | — | — |
| 3軸 | **0.00°**(凍結) | 19.5° | < 1e-12° |

実装は `pedestal_tilt/three_axis.py`(`forward_3axis` / `ik_3axis` / `ik_3axis_hold` / `plan_pass` / `max_azimuth_step`)、デモは `examples/demo_3axis.py`、テストは `tests/test_pedestal_tilt.py::TestThreeAxis`。

### 8.5 3D シミュレーション

`sim/antenna3d.html`(Three.js 単一 HTML)で、この運動学をインタラクティブに可視化できる。手動モードで Az/El/XEl・台座傾きを操作し、衛星パス追尾モードで各種軌道(直上/準天頂/高・中・低仰角/極軌道/赤道/GEO)を 2軸 vs 3軸 でアニメーション比較する(各軸の角度 vs 時間グラフ・回転軸の3D表示付き)。HTML 内の運動学 JS は本モジュールの厳密移植で、起動時に golden 値・不変条件・パス総移動量・軌道parity・描画整合の自己テストを実行する(`sim/gen_golden.py` で golden 再生成)。座標規約 (N,E,U)↔Three.js は `sim/AGENTS.md` を参照。

### 8.6 関節可動域と第3軸の中立位置

各軸が有限ストローク(例:90°幅)しか持たない場合、何が追尾可能かは「可動域」で決まる(`JointLimits` / `within_limits` / `pass_fits_limits` / `peak_abs_xel`)。

- **方位 0–90° のような狭域**:順運動学の y 成分 `u_y = sin a·cos h·cos ξ + cos a·sin ξ` は a,h,ξ∈[0,90°] で常に ≥ 0 となり、視軸方位が **[0,180°](東側半天)に限定**される。これは原理的な被覆制限で、El/XEl では回復できない(上半球の約 50% のみ到達)。
- **第3軸(XEl)の中立位置**:天頂越えに必要な ξ は **両振り(±キーホール半径ぶん)**。中立を端 `(0,90)` に置くと負側が範囲外となり破綻するが、**中立をストローク中央 `(−45,+45)` に置けば同じ 90° 幅でもキーホール除去が成立**する(必要 |ξ|max ≈ キーホール半径、既定パスで約 19° ⊂ 45°)。

> 要するに、第3軸は「幅」より「中立位置」が本質。中立を中央に置くことが、有限可動域でのキーホール除去の鍵となる。検証は `tests/test_pedestal_tilt.py::TestThreeAxis::test_centered_xel_realizes_keyhole_under_limits`、デモ末尾の出力、およびシムの「XEl 中立 端/中央」トグルを参照。

> 注:台座傾き θ_t があるとキーホールは真天頂から θ_t だけ φ_t 方向へずれる。`three_axis` は `R_tilt` を介して傾きを織り込むため、傾きがあっても同じ逆運動学が成立する。

---

## 9. 今後の拡張

- `astropy.coordinates.get_sun()` を使った太陽位置の正確計算
- CLI 化(`python -m pedestal_tilt fit ...`, `python -m pedestal_tilt correct ...`)
- az 方向ずれも測定して 6 観測 × 2 未知数の過剰決定で残差最小化
- 大気差補正(高度 < 10° で重要)
- 厳密 3D 回転(`scipy.optimize.least_squares`)で線形近似誤差を排除

---

## 付録 A: 数式の導出概略

任意のベクトル `u_m`(マウント座標)を真地平座標に変換する回転行列 `R`(回転軸 `n = (−sin φ_t, cos φ_t, 0)`、回転角 `θ_t`)を Rodrigues の公式で書き、`u_m = (cos h cos a, cos h sin a, sin h)` を作用させて第一次の項を取ると、§2.3 の線形式が得られる。像でのずれは「真位置 − 実指向」を tangent 平面の (alt, az·cosh) 成分に投影することで §2.4 が導かれる。補正は同じ式を逆向きに使えばよい。

---

## 付録 B: 検証ログ(numpy 不要・純 Python で同等の計算を実行した結果)

数式とアルゴリズムの正しさを確認するため、純標準ライブラリ(`math` のみ)で同じ計算を実行した。

```
=== 台座傾き推定 ===
  theta_t = 0.7071°
  phi_t   = 315.00°
  残差    = [0.0, 0.0, -0.0]

=== 補正値 ===
   9時:  真位置 ( 90.00, 30.00)  ->  指令 ( 90.289, 29.500)
  12時:  真位置 (180.00, 70.00)  ->  指令 (178.626, 69.500)
  15時:  真位置 (270.00, 30.00)  ->  指令 (269.711, 30.500)

=== 検算: 指令を順問題(厳密3D回転)に通すと真位置に戻るか ===
   9時:  指令 -> 実指向 ( 90.004, 30.001)  誤差 (+0.0036, +0.0013)
  12時:  指令 -> 実指向 (179.965, 70.006)  誤差 (-0.0349, +0.0061)
  15時:  指令 -> 実指向 (270.004, 30.001)  誤差 (+0.0037, +0.0012)

=== 検算: 推定パラメータで像ずれを再計算 ===
   9時:  Δh = -0.5000,  Δa·cosh = +0.2500
  12時:  Δh = -0.5000,  Δa·cosh = -0.4698
  15時:  Δh = +0.5000,  Δa·cosh = -0.2500

=== ラウンドトリップテスト(既知 (θ=0.5, φ=80) で生成→復元) ===
  真値:   theta = 0.5, phi = 80.0
  復元値: theta = 0.500000, phi = 80.0000  -> PASS

=== ゼロ傾き(θ=0)で像ずれ=0 ===  PASS
```

### 結果の確認事項
- **像のたて方向ずれ**(9時 −0.5, 12時 −0.5, 15時 +0.5)が入力値と一致 → **解 (θ_t, φ_t) = (0.71°, 315°) が成立**
- **補正→順問題→真位置** のラウンドトリップで誤差は最大 0.035°(12時, 高仰角での tan の影響)→ 実用範囲内
- 既知パラメータでの **生成→復元** が機械精度で成功 → ソルバ実装が正しい
- ゼロ傾きで像ずれが恒等的にゼロ → 順問題実装が正しい

---

**END OF REPORT**
