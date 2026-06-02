"""antenna3d.html の自己テスト用 golden 値を再生成する。

`pedestal_tilt/three_axis.py` の運動学を変更したら、本スクリプトを実行して
標準出力の `GOLD_FWD` / `GOLD_HOLD` リテラルとパス総移動量コメントを
`sim/antenna3d.html` の対応箇所に貼り替える(HTML の JS 実装が Python と
一致していることを保証する突き合わせデータ)。

    python3 sim/gen_golden.py      # リポジトリルートから

外部依存なし(標準ライブラリのみ)。HTML 自体は Three.js のみを CDN から読む。
"""

from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import forward_3axis, ik_3axis_hold, plan_pass
from pedestal_tilt.geometry import _altaz_to_unit, _unit_to_altaz


def main() -> None:
    fwd_cases = [
        (0, 0, 0, 0, 0),
        (90, 30, 0, 0, 0),
        (180, 70, 0, 0, 0),
        (0, 90, 10, 0, 0),
        (0, 90, -25, 0, 0),
        (123, 90, 0, 0, 0),
        (90, 30, 0, 0.7, 315),
        (180, 70, 5, 0.7, 315),
        (270, 30, -3, 1.2, 200),
        (45, 89, 15, 0.5, 80),
        (300, 80, 20, 0, 0),
        (60, 45, -30, 1.0, 150),
    ]
    print("const GOLD_FWD = [")
    for a, h, x, th, ph in fwd_cases:
        ap, hp = forward_3axis(a, h, x, th, ph)
        print(f"  [{a},{h},{x},{th},{ph}, {ap:.9f},{hp:.9f}],")
    print("];")

    hold_cases = [(120, 89.5, 90, 0, 0), (200, 88, 170, 0.7, 315), (10, 85, 300, 0, 0)]
    print("const GOLD_HOLD = [")
    for a, h, ah, th, ph in hold_cases:
        ja, jh, jx = ik_3axis_hold(a, h, ah, th, ph)
        print(f"  [{a},{h},{ah},{th},{ph}, {ja:.9f},{jh:.9f},{jx:.9f}],")
    print("];")

    # パス総移動量(キーホール内, 0.5°刻み, d_min=1°): 2軸 ≈ 174.36, 3軸 = 0
    s_list = [i * 0.5 for i in range(-160, 161)]
    u0 = _altaz_to_unit(90.0, 90.0 - 1.0)
    q = _altaz_to_unit((90.0 + 90.0) % 360.0, 0.0)
    samples = [
        _unit_to_altaz(
            tuple(
                math.cos(math.radians(s)) * u0[i] + math.sin(math.radians(s)) * q[i]
                for i in range(3)
            )
        )
        for s in s_list
    ]
    in_cone = [(90.0 - h) < 20.0 for _, h in samples]

    def travel(cmd):
        total, prev = 0.0, None
        for c, m in zip(cmd, in_cone):
            if not m:
                prev = None
                continue
            if prev is not None:
                total += abs(((c[0] - prev + 540.0) % 360.0) - 180.0)
            prev = c[0]
        return total

    t2 = travel(plan_pass(samples, 0.0, 0.0, strategy="2axis"))
    t3 = travel(plan_pass(samples, 0.0, 0.0, keyhole_deg=20.0, strategy="3axis"))
    print(f"// GOLD pass travel in-cone: 2axis={t2:.4f}  3axis={t3:.4f}")

    # 軌道生成 parity(makeOrbit + 3軸プラン): culmEl=88.5, culmAz=120, n=177, 錐内 idx
    def make_orbit(culm_el, culm_az, n=177):
        u0 = _altaz_to_unit(culm_az, culm_el)
        qq = _altaz_to_unit((culm_az + 90.0) % 360.0, 0.0)
        out = []
        for i in range(n):
            s = math.radians(-88.0 + 176.0 * i / (n - 1))
            out.append(
                _unit_to_altaz(
                    tuple(math.cos(s) * u0[k] + math.sin(s) * qq[k] for k in range(3))
                )
            )
        return out

    idx = [72, 80, 88, 96, 104]
    plan = plan_pass(
        make_orbit(88.5, 120.0), 0.0, 0.0, keyhole_deg=20.0, strategy="3axis"
    )
    print(
        "const GOLD_ORBIT = {culmEl:88.5,culmAz:120,n:177,idx:["
        + ",".join(map(str, idx))
        + "],joints:["
    )
    for i in idx:
        a, h, x = plan[i]
        print(f"  [{a:.6f},{h:.6f},{x:.6f}],")
    print("]};")

    # 第3軸 中立中央の実現: 既定パス(culmEl=88.5,culmAz=90,keyhole20)の |ξ| ピークと符号
    pc = [
        c[2]
        for c in plan_pass(
            make_orbit(88.5, 90.0), 0.0, 0.0, keyhole_deg=20.0, strategy="3axis"
        )
    ]
    peak = max(abs(min(pc)), abs(max(pc)))
    print(
        f"// GOLD_XEL default-pass: peakAbs={peak:.4f} minXel={min(pc):.4f} maxXel={max(pc):.4f}"
        f"  → 中央[-45,45]可:{peak < 45}  端[0,90]不可:{min(pc) < 0}"
    )


if __name__ == "__main__":
    main()
