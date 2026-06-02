"""3軸(Az–El–XEl)マウントで天頂キーホールが消えることを数値で示すデモ。

天頂の近く(最接近 d_min)を通る太陽/衛星パスを作り、
  2軸: 方位がほぼ 180° 振られる(キーホール)
  3軸: 方位を凍結したまま XEl が天頂越えを引き受ける
を比較する。

実行:
    python -m examples.demo_3axis
または
    python examples/demo_3axis.py
"""

from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import forward_3axis, max_azimuth_step, plan_pass
from pedestal_tilt.geometry import _altaz_to_unit, _unit_to_altaz

# このデモでは台座傾きを 0 にしてキーホール(運動学)だけを見る。
# (傾き θ_t があるとキーホールは真天頂から θ_t だけずれる。)
THETA_T, PHI_T = 0.0, 0.0
D_MIN = 1.0  # 天頂への最接近 [deg](=culmination の天頂距離)
A_CULM = 90.0  # 最接近の方位(東の空で南中)
KEYHOLE = 20.0  # キーホール錐の半径 [deg]


def make_zenith_pass(d_min, a_culm, s_list):
    """天頂距離 d_min で最接近する大円パス(真地平の (a, h) 列)。"""
    u0 = _altaz_to_unit(a_culm, 90.0 - d_min)  # 最接近点
    q = _altaz_to_unit((a_culm + 90.0) % 360.0, 0.0)  # 進行方向(直交・水平)
    pts = []
    for s in s_list:
        sr = math.radians(s)
        u = tuple(math.cos(sr) * u0[i] + math.sin(sr) * q[i] for i in range(3))
        pts.append(_unit_to_altaz(u))
    return pts


def az_travel(commands, mask):
    """mask=True の連続区間における方位の総移動量 Σ|Δa| [deg]。"""
    total = 0.0
    prev = None
    for c, m in zip(commands, mask):
        if not m:
            prev = None
            continue
        if prev is not None:
            total += abs(((c[0] - prev + 540.0) % 360.0) - 180.0)
        prev = c[0]
    return total


def main() -> None:
    s_list = [i * 0.5 for i in range(-160, 161)]  # 0.5° 刻み
    samples = make_zenith_pass(D_MIN, A_CULM, s_list)
    in_cone = [(90.0 - h) < KEYHOLE for (_, h) in samples]

    cmd2 = plan_pass(samples, THETA_T, PHI_T, strategy="2axis")
    cmd3 = plan_pass(samples, THETA_T, PHI_T, keyhole_deg=KEYHOLE, strategy="3axis")

    print("=" * 64)
    print(f" 天頂キーホール比較(最接近 d_min = {D_MIN}°, キーホール半径 {KEYHOLE}°)")
    print("=" * 64)
    print("  最接近点付近の指令(高度の高い順に数点):")
    print(f"    {'真位置(a,h)':^20} | {'2軸 (a,h,ξ)':^22} | {'3軸 (a,h,ξ)':^22}")
    print(f"    {'-' * 20}-+-{'-' * 22}-+-{'-' * 22}")
    order = sorted(range(len(samples)), key=lambda i: -samples[i][1])
    for i in sorted(order[:7]):
        a, h = samples[i]
        c2, c3 = cmd2[i], cmd3[i]
        print(
            f"    ({a:6.2f}, {h:5.2f})     | "
            f"({c2[0]:6.2f},{c2[1]:5.2f},{c2[2]:5.1f}) | "
            f"({c3[0]:6.2f},{c3[1]:5.2f},{c3[2]:5.1f})"
        )

    print()
    print("=" * 64)
    print(" キーホール内(高度 > {:.0f}°)での方位の動き".format(90.0 - KEYHOLE))
    print("=" * 64)
    print(
        f"  2軸: 方位 最大ステップ = {max_azimuth_step([c for c, m in zip(cmd2, in_cone) if m]):7.2f}°"
        f" / 総移動量 = {az_travel(cmd2, in_cone):7.2f}°  ← キーホール"
    )
    print(
        f"  3軸: 方位 最大ステップ = {max_azimuth_step([c for c, m in zip(cmd3, in_cone) if m]):7.2f}°"
        f" / 総移動量 = {az_travel(cmd3, in_cone):7.2f}°  ← 凍結"
    )
    max_xel = max(abs(c[2]) for c, m in zip(cmd3, in_cone) if m)
    print(f"       (XEl が肩代わり: 最大 |ξ| = {max_xel:.2f}°)")

    print()
    print("=" * 64)
    print(" 検算:3軸指令を順問題に通すと目標へ戻るか")
    print("=" * 64)
    perr = 0.0
    for (a, h), c in zip(samples, cmd3):
        aa, hh = forward_3axis(c[0], c[1], c[2], THETA_T, PHI_T)
        da = abs(((aa - a + 540.0) % 360.0) - 180.0)
        perr = max(perr, max(da, abs(hh - h)))
    print(f"  全 {len(samples)} 点の最大指向誤差 = {perr:.2e}°")

    print()
    print("=" * 64)
    print(" 単点での天頂特異点(2軸 tan(h) 発散 vs 3軸有限)")
    print("=" * 64)
    from pedestal_tilt import correction, ik_3axis

    for h in [80.0, 89.0, 89.9, 90.0]:
        a_cmd, h_cmd = correction(45.0, h, 0.7, 315.0)  # 線形補正(2軸)
        j = ik_3axis(45.0, h, 0.7, 315.0)  # 3軸 IK
        print(
            f"  h={h:5.1f}°  2軸補正 Δa={a_cmd - 45.0:+8.3f}°(tan(h)で増大)   "
            f"3軸 (a,h,ξ)=({j[0]:6.2f},{j[1]:5.2f},{j[2]:5.2f})"
        )

    print()
    print("=" * 64)
    print(" 関節可動域:第3軸(XEl)の中立位置で追尾可否が変わる")
    print("=" * 64)
    from pedestal_tilt import JointLimits, pass_fits_limits, peak_abs_xel

    xs = [c[2] for c in cmd3]
    print(f"  天頂越えに必要な ξ: [{min(xs):+.1f}, {max(xs):+.1f}]°  (両振り)")
    print(
        f"  必要な XEl 半ストローク |ξ|max = {peak_abs_xel(cmd3):.1f}°  (≈ キーホール半径)"
    )
    edge = JointLimits(xel=(0.0, 90.0))  # 中立=端
    center = JointLimits(xel=(-45.0, 45.0))  # 中立=中央(同じ90°幅)
    print(
        f"  端中立 [0, 90]°(90°幅): パス追尾 {'可' if pass_fits_limits(cmd3, edge) else '不可(負側はみ出し)'}"
    )
    print(
        f"  中央中立 [-45, +45]°(同90°幅): パス追尾 {'可' if pass_fits_limits(cmd3, center) else '不可'}"
    )
    print("  → 同じ 90° 幅でも、中立を中央に置けばキーホール除去が成立する。")


if __name__ == "__main__":
    main()
