"""ご提示のデータ(9時=E, 12時=S, 15時=E に 0.5°)から台座傾きを推定。

実行例:
    python -m examples.demo
または
    python examples/demo.py
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import (
    Observation,
    correction,
    fit_tilt,
    forward_pointing,
    image_offset,
)

# 太陽の真位置(東京・春分頃の概算値。実用では astropy 等で厳密計算)
SUN_POSITIONS = {
    9:  (90.0,  30.0),
    12: (180.0, 70.0),
    15: (270.0, 30.0),
}

# 像でのたて方向ずれ Δh:
#   下からのぞいた像で
#   - 9時:  E方向 (=東を見上げ、E は alt の負側) → Δh = -0.5°
#   - 12時: S方向 (=南を見上げ、S は alt の負側) → Δh = -0.5°
#   - 15時: E方向 (=西を見上げ、E は alt の正側) → Δh = +0.5°
OBSERVATIONS = [
    Observation(*SUN_POSITIONS[9],  dh_image_deg=-0.5),
    Observation(*SUN_POSITIONS[12], dh_image_deg=-0.5),
    Observation(*SUN_POSITIONS[15], dh_image_deg=+0.5),
]


def main() -> None:
    theta, phi, residuals = fit_tilt(OBSERVATIONS)

    print("=" * 60)
    print(" 台座傾き推定")
    print("=" * 60)
    print(f"  θ_t = {theta:.4f}°  (傾きの大きさ)")
    print(f"  φ_t = {phi:.2f}°  (傾きの方位 — 北=0, 東=90, 南=180, 西=270)")
    direction = _compass_label(phi)
    print(f"  → 台座は {direction} 方向に約 {theta:.2f}° 倒れている")
    print(f"  最小二乗の残差: {[round(r, 6) for r in residuals]}")

    print()
    print("=" * 60)
    print(" 補正値(各時刻の太陽を像中央に置くための指令値)")
    print("=" * 60)
    print(f"  {'時刻':>5} | {'真の太陽位置':^22} | {'指令値':^22}")
    print(f"  {'-'*5}-+-{'-'*22}-+-{'-'*22}")
    for t, (a_sun, h_sun) in SUN_POSITIONS.items():
        a_cmd, h_cmd = correction(a_sun, h_sun, theta, phi)
        print(f"  {t:>3}時 | "
              f"({a_sun:7.3f}°, {h_sun:6.3f}°) | "
              f"({a_cmd:7.3f}°, {h_cmd:6.3f}°)")

    print()
    print("=" * 60)
    print(" 検算 1:指令値を順問題に通したときの実指向(目標値に戻るか)")
    print("=" * 60)
    for t, (a_sun, h_sun) in SUN_POSITIONS.items():
        a_cmd, h_cmd = correction(a_sun, h_sun, theta, phi)
        a_act, h_act = forward_pointing(a_cmd, h_cmd, theta, phi)
        err_a = ((a_act - a_sun + 540) % 360) - 180
        err_h = h_act - h_sun
        print(f"  {t:>3}時:  指令 → 実指向 ({a_act:7.3f}°, {h_act:6.3f}°)  "
              f"目標 ({a_sun:7.3f}°, {h_sun:6.3f}°)  誤差 ({err_a:+.4f}°, {err_h:+.4f}°)")

    print()
    print("=" * 60)
    print(" 検算 2:推定パラメータで像ずれを再計算")
    print("=" * 60)
    for t, (a_sun, h_sun) in SUN_POSITIONS.items():
        dh, dac = image_offset(a_sun, h_sun, theta, phi)
        print(f"  {t:>3}時:  Δh = {dh:+.4f}°,  Δa·cosh = {dac:+.4f}°")


def _compass_label(phi_deg: float) -> str:
    """方位角を 8 方位ラベルに変換。"""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    idx = int(round((phi_deg % 360) / 45)) % 8
    return labels[idx]


if __name__ == "__main__":
    main()
