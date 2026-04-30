# parabolic-antenna

パラボラアンテナ(望遠鏡)の台座傾きを 3 観測点(9時 / 12時 / 15時の太陽撮影)から推定し、
計算した太陽位置を像中央に持ってくるための指令補正を行うツール。

詳細な数式・導出・解答は **[REPORT.md](./REPORT.md)** を参照。

## ファイル構成

```
parabolic-antenna/
├── REPORT.md                       # 数式・導出・解答・コード解説
├── 3D補正.xlsx                     # 元の問題ファイル
├── pedestal_tilt/
│   ├── __init__.py
│   ├── geometry.py                 # 順問題・像ずれ・補正(numpy 不要)
│   └── solver.py                   # 最小二乗で (θ_t, φ_t) 推定
├── examples/
│   └── demo.py                     # 本問題のサンプル実行
└── tests/
    └── test_pedestal_tilt.py       # 単体テスト(stdlib unittest)
```

## 動作環境

- Python 3.10+
- 標準ライブラリ(`math`, `dataclasses`, `unittest`)のみ。外部依存なし。

## 使い方

### デモ実行

```bash
python3 examples/demo.py
```

出力例:
```
=========================================================
 台座傾き推定
=========================================================
  θ_t = 0.7071°  (傾きの大きさ)
  φ_t = 315.00°  (傾きの方位 — 北=0, 東=90, 南=180, 西=270)
  → 台座は NW 方向に約 0.71° 倒れている

=========================================================
 補正値(各時刻の太陽を像中央に置くための指令値)
=========================================================
    9時 | ( 90.000°, 30.000°) | ( 90.289°, 29.500°)
   12時 | (180.000°, 70.000°) | (178.626°, 69.500°)
   15時 | (270.000°, 30.000°) | (269.711°, 30.500°)
```

### テスト実行

```bash
python3 -m unittest tests.test_pedestal_tilt -v
```

### ライブラリとして使う

```python
from pedestal_tilt import Observation, fit_tilt, correction

# 観測データ:太陽の真位置と像でのずれ
observations = [
    Observation(a_sun_deg=90.0,  h_sun_deg=30.0, dh_image_deg=-0.5),
    Observation(a_sun_deg=180.0, h_sun_deg=70.0, dh_image_deg=-0.5),
    Observation(a_sun_deg=270.0, h_sun_deg=30.0, dh_image_deg=+0.5),
]

# 台座傾きを推定
theta, phi, residuals = fit_tilt(observations)
print(f"傾き: θ={theta:.3f}°, 方位 φ={phi:.1f}°")

# 任意の真位置に対する指令補正
a_cmd, h_cmd = correction(a_calc_deg=180.0, h_calc_deg=70.0,
                          theta_t_deg=theta, phi_t_deg=phi)
print(f"指令値: ({a_cmd:.3f}°, {h_cmd:.3f}°)")
```

## 物理モデル(要約)

台座傾きを (θ_t, φ_t) と置くと、太陽の真位置 (a_sun, h_sun) を指令したときの像ずれは線形近似で:

```
Δh_image       = +θ_t · cos(a_sun − φ_t)
Δa·cos(h)_image = +θ_t · sin(a_sun − φ_t) · sin(h_sun)
```

像中央に太陽を置くための指令補正:

```
h_cmd = h_calc + θ_t · cos(a_calc − φ_t)
a_cmd = a_calc + θ_t · sin(a_calc − φ_t) · tan(h_calc)
```

導出と検証は [REPORT.md](./REPORT.md) を参照。

## ライセンス

未指定(問題課題のため)。
