"""観測地・日時から太陽位置を厳密計算し、台座傾き推定パイプラインに渡すデモ。

`demo.py` は太陽位置をハードコードしていたが、ここでは `sun_altaz` で
緯度・経度・日時から求める(標準ライブラリのみ・大気差込み)。

実行:
    python3 examples/demo_sun.py
"""

from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import (
    Observation,
    correction,
    fit_tilt,
    image_offset,
    sun_altaz,
)

LAT, LON = 35.681, 139.767  # 東京駅
JST = timezone(timedelta(hours=9))
Y, M, D = 2024, 3, 20  # 春分


def main() -> None:
    times = [datetime(Y, M, D, hh, 0, 0, tzinfo=JST) for hh in (9, 12, 15)]

    print("=" * 60)
    print(" 太陽位置(厳密計算・見かけ) — 東京, 2024-03-20")
    print("=" * 60)
    suns = []
    for t in times:
        az, el = sun_altaz(LAT, LON, t)  # 大気差込みの見かけ位置
        suns.append((az, el))
        print(f"  {t.strftime('%H:%M JST')}  →  方位 {az:6.2f}°,  高度 {el:5.2f}°")

    # 既知の台座傾きで像ずれを合成 → 厳密太陽位置を使って fit_tilt で復元(検証)
    theta_true, phi_true = 0.7, 300.0
    obs = [
        Observation(az, el, *image_offset(az, el, theta_true, phi_true))
        for az, el in suns
    ]
    theta, phi, residuals = fit_tilt(obs)

    print()
    print("=" * 60)
    print(" 厳密太陽位置で台座傾きを推定(合成データで検証)")
    print("=" * 60)
    print(f"  真値:   θ_t = {theta_true}°,  φ_t = {phi_true}°")
    print(f"  推定値: θ_t = {theta:.4f}°,  φ_t = {phi:.2f}°")
    print(f"  残差max = {max(abs(r) for r in residuals):.2e}")

    print()
    print("  各時刻の指向補正(推定傾きで太陽を像中央へ):")
    for (az, el), t in zip(suns, times):
        a_cmd, h_cmd = correction(az, el, theta, phi)
        print(
            f"    {t.strftime('%H:%M')} 太陽({az:6.2f},{el:5.2f}) → 指令({a_cmd:7.3f},{h_cmd:6.3f})"
        )


if __name__ == "__main__":
    main()
