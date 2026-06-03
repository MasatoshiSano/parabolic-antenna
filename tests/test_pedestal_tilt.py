"""pedestal_tilt パッケージの単体テスト(stdlib unittest)。"""

from __future__ import annotations
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import (
    JointLimits,
    Observation,
    correction,
    fit_tilt,
    forward_3axis,
    forward_pointing,
    ik_3axis,
    ik_3axis_hold,
    image_offset,
    max_azimuth_step,
    pass_fits_limits,
    peak_abs_xel,
    plan_pass,
    tilt_rotation_matrix,
    within_limits,
)
from pedestal_tilt.geometry import _altaz_to_unit, _unit_to_altaz
from pedestal_tilt import (
    TripodGeometry,
    home_length,
    leg_lengths,
    max_zenith_distance,
    reachable,
    refraction_deg,
    sun_altaz,
)
from pedestal_tilt.sun import _julian_day, _sun_ra_dec
from datetime import datetime, timedelta, timezone


class TestGeometry(unittest.TestCase):
    def test_zero_tilt_no_offset(self):
        for a, h in [(90, 30), (180, 70), (270, 30), (0, 45), (123, 60)]:
            dh, dac = image_offset(a, h, 0.0, 123.0)
            self.assertAlmostEqual(dh, 0.0, places=12)
            self.assertAlmostEqual(dac, 0.0, places=12)

    def test_zero_tilt_forward_identity(self):
        for a, h in [(90, 30), (180, 70), (270, 30)]:
            a2, h2 = forward_pointing(a, h, 0.0, 50.0)
            self.assertAlmostEqual(a, a2, places=10)
            self.assertAlmostEqual(h, h2, places=10)

    def test_rotation_matrix_orthogonal(self):
        R = tilt_rotation_matrix(0.5, 80.0)
        # R · R^T = I
        for i in range(3):
            for j in range(3):
                dot = sum(R[i][k] * R[j][k] for k in range(3))
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(dot, expected, places=10)

    def test_rotation_maps_z_to_tilted_zenith(self):
        theta_t, phi_t = 0.7, 315.0
        R = tilt_rotation_matrix(theta_t, phi_t)
        # マウントの "上" (0,0,1) を真フレームに変換
        z_prime = (R[0][2], R[1][2], R[2][2])
        expected = (
            math.sin(math.radians(theta_t)) * math.cos(math.radians(phi_t)),
            math.sin(math.radians(theta_t)) * math.sin(math.radians(phi_t)),
            math.cos(math.radians(theta_t)),
        )
        for got, exp in zip(z_prime, expected):
            self.assertAlmostEqual(got, exp, places=10)

    def test_correction_brings_calc_to_actual(self):
        # 線形近似なので、典型的な θ < 1°、h < 70° 程度では誤差 < 0.05°
        theta, phi = 0.707, 315.0
        for a_calc, h_calc in [
            (90.0, 30.0),
            (180.0, 70.0),
            (270.0, 30.0),
            (45.0, 50.0),
        ]:
            a_cmd, h_cmd = correction(a_calc, h_calc, theta, phi)
            a_act, h_act = forward_pointing(a_cmd, h_cmd, theta, phi)
            err_a = ((a_act - a_calc + 540) % 360) - 180
            err_h = h_act - h_calc
            self.assertLess(
                abs(err_a), 0.05, f"az error too large at ({a_calc}, {h_calc}): {err_a}"
            )
            self.assertLess(
                abs(err_h),
                0.05,
                f"alt error too large at ({a_calc}, {h_calc}): {err_h}",
            )


class TestSolver(unittest.TestCase):
    def test_round_trip_recovers_known_tilt(self):
        """既知 (θ, φ) で観測を生成 → ソルバで復元できるか。"""
        for theta_true, phi_true in [(0.5, 80.0), (0.71, 315.0), (1.2, 200.0)]:
            sun_positions = [(90.0, 30.0), (180.0, 70.0), (270.0, 30.0)]
            obs = []
            for a, h in sun_positions:
                dh, dac = image_offset(a, h, theta_true, phi_true)
                obs.append(Observation(a, h, dh_image_deg=dh, dac_image_deg=dac))
            theta, phi, _ = fit_tilt(obs)
            self.assertAlmostEqual(theta, theta_true, places=8)
            phi_diff = ((phi - phi_true + 540) % 360) - 180
            self.assertLess(abs(phi_diff), 1e-6)

    def test_alt_only_three_obs(self):
        """ご提示のデータ(alt 方向のみ)で θ=√0.5°, φ=315° が出るか。"""
        obs = [
            Observation(90.0, 30.0, dh_image_deg=-0.5),
            Observation(180.0, 70.0, dh_image_deg=-0.5),
            Observation(270.0, 30.0, dh_image_deg=+0.5),
        ]
        theta, phi, residuals = fit_tilt(obs)
        self.assertAlmostEqual(theta, math.sqrt(0.5), places=10)
        self.assertAlmostEqual(phi, 315.0, places=8)
        for r in residuals:
            self.assertLess(abs(r), 1e-12)

    def test_overdetermined_with_noise(self):
        """6方程式(alt+az 各3点)で残差が小さく出るか。"""
        theta_true, phi_true = 0.6, 100.0
        sun_positions = [(90, 30), (180, 70), (270, 30), (135, 50)]
        obs = []
        for a, h in sun_positions:
            dh, dac = image_offset(a, h, theta_true, phi_true)
            obs.append(Observation(a, h, dh_image_deg=dh, dac_image_deg=dac))
        theta, phi, residuals = fit_tilt(obs)
        self.assertAlmostEqual(theta, theta_true, places=8)
        phi_diff = ((phi - phi_true + 540) % 360) - 180
        self.assertLess(abs(phi_diff), 1e-6)
        for r in residuals:
            self.assertLess(abs(r), 1e-10)


class TestPhysicalIntuition(unittest.TestCase):
    """物理直観のスポットチェック。"""

    def test_north_tilt_shifts_noon_sun_low(self):
        """φ_t=0 (北傾き) のとき 12時(南中)に像で sun は -alt 側にずれる。"""
        dh, dac = image_offset(180.0, 70.0, 0.5, 0.0)
        # cos(180 - 0) = -1, so dh = 0.5 · (-1) = -0.5
        self.assertAlmostEqual(dh, -0.5, places=10)
        # sin(180 - 0) = 0, so dac = 0
        self.assertAlmostEqual(dac, 0.0, places=10)

    def test_east_tilt_at_noon_no_alt_shift(self):
        """φ_t=90 (東傾き) のとき 12時(南中)に alt 方向のずれは 0。"""
        dh, _ = image_offset(180.0, 70.0, 0.5, 90.0)
        # cos(180 - 90) = 0
        self.assertAlmostEqual(dh, 0.0, places=10)


def _angdiff(a, b):
    return ((a - b + 540.0) % 360.0) - 180.0


def _az_travel(commands, mask):
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


def _make_zenith_pass(d_min, a_culm, s_list):
    """天頂距離 d_min で最接近する大円パス(真地平の (a, h) 列)。"""
    u0 = _altaz_to_unit(a_culm, 90.0 - d_min)
    q = _altaz_to_unit((a_culm + 90.0) % 360.0, 0.0)
    pts = []
    for s in s_list:
        sr = math.radians(s)
        u = tuple(math.cos(sr) * u0[i] + math.sin(sr) * q[i] for i in range(3))
        pts.append(_unit_to_altaz(u))
    return pts


class TestThreeAxis(unittest.TestCase):
    """3軸(Az–El–XEl)マウントの運動学。"""

    def test_forward_reduces_to_two_axis(self):
        """XEl=0 のとき forward_3axis は forward_pointing に厳密一致。"""
        for a, h in [(90, 30), (180, 70), (33, 12), (300, 80), (0, 5)]:
            for th, ph in [(0.0, 0.0), (0.7, 315.0), (1.2, 200.0)]:
                a2, h2 = forward_pointing(a, h, th, ph)
                a3, h3 = forward_3axis(a, h, 0.0, th, ph)
                self.assertAlmostEqual(_angdiff(a2, a3), 0.0, places=9)
                self.assertAlmostEqual(h2, h3, places=9)

    def test_xel_tips_boresight_sideways_at_zenith(self):
        """天頂(h=90)で XEl は視軸を横へ倒す(高度を 90−|ξ| に下げる)。"""
        for xel in [3.0, 10.0, -7.0]:
            _, h = forward_3axis(0.0, 90.0, xel, 0.0, 0.0)
            self.assertAlmostEqual(h, 90.0 - abs(xel), places=9)

    def test_ik_hold_round_trip(self):
        """方位保持 IK の解を順問題に通すと目標へ戻る。"""
        max_err = 0.0
        for a, h in [(120, 89.5), (200, 88), (10, 85), (90, 30), (180, 70)]:
            for a_hold in [a - 30, a + 45, a, a - 90]:
                for th, ph in [(0.0, 0.0), (0.7, 315.0)]:
                    ja, jh, jx = ik_3axis_hold(a, h, a_hold, th, ph)
                    self.assertAlmostEqual(_angdiff(ja, a_hold), 0.0, places=9)
                    aa, hh = forward_3axis(ja, jh, jx, th, ph)
                    max_err = max(max_err, abs(_angdiff(aa, a)), abs(hh - h))
        self.assertLess(max_err, 1e-7)

    def test_ik_auto_outside_keyhole_is_two_axis(self):
        """キーホール外では ξ=0 で標準2軸に一致。"""
        for a, h in [(90, 30), (180, 60), (270, 45)]:
            ja, jh, jx = ik_3axis(a, h, 0.0, 0.0, keyhole_deg=10.0)
            self.assertAlmostEqual(jx, 0.0, places=12)
            self.assertAlmostEqual(_angdiff(ja, a), 0.0, places=9)
            self.assertAlmostEqual(jh, h, places=9)

    def test_exact_zenith_is_finite_and_points(self):
        """厳密天頂でも IK は有限解を返し、順問題で天頂へ戻る。"""
        j = ik_3axis(123.0, 90.0, 0.0, 0.0)
        for v in j:
            self.assertTrue(math.isfinite(v))
        _, hh = forward_3axis(j[0], j[1], j[2], 0.0, 0.0)
        self.assertAlmostEqual(hh, 90.0, places=9)

    def test_pass_freezes_azimuth_in_keyhole(self):
        """天頂近傍パスで、3軸はキーホール内の方位移動を 2軸より桁違いに抑える。"""
        s_list = [i * 0.5 for i in range(-160, 161)]
        samples = _make_zenith_pass(d_min=1.0, a_culm=90.0, s_list=s_list)
        in_cone = [(90.0 - h) < 20.0 for (_, h) in samples]
        cmd2 = plan_pass(samples, 0.0, 0.0, strategy="2axis")
        cmd3 = plan_pass(samples, 0.0, 0.0, keyhole_deg=20.0, strategy="3axis")

        # キーホール内の方位「総移動量」で比較(サンプリング非依存)。
        # 2軸はほぼ 180° 振る(キーホール)、3軸は凍結。
        travel2 = _az_travel(cmd2, in_cone)
        travel3 = _az_travel(cmd3, in_cone)
        self.assertGreater(travel2, 150.0)
        self.assertLess(travel3, 1.0)

        # 3軸指令はすべて目標を正しく指向する
        max_err = 0.0
        for (a, h), c in zip(samples, cmd3):
            aa, hh = forward_3axis(c[0], c[1], c[2], 0.0, 0.0)
            max_err = max(max_err, abs(_angdiff(aa, a)), abs(hh - h))
        self.assertLess(max_err, 1e-7)

        # XEl は物理範囲内
        for c in cmd3:
            self.assertLessEqual(abs(c[2]), 90.0)

    def test_centered_xel_realizes_keyhole_under_limits(self):
        """第3軸の中立を範囲中央に置けば、90°幅でも天頂越えが可動域に収まる。

        端中立 [0,90] では ξ が負側へ振れて収まらない(=制約下で破綻)。
        """
        s_list = [i * 0.5 for i in range(-160, 161)]
        samples = _make_zenith_pass(d_min=1.0, a_culm=90.0, s_list=s_list)
        cmds = plan_pass(samples, 0.0, 0.0, keyhole_deg=20.0, strategy="3axis")

        # ξ は両振り(負側が必要) → 端中立 [0,90] では不可
        xs = [c[2] for c in cmds]
        self.assertLess(min(xs), -1e-6)
        # 必要な XEl 半ストロークはキーホール半径ぶん程度(< 45°)
        self.assertLess(peak_abs_xel(cmds), 45.0)

        # 中立中央 [-45,45](90°幅)なら全点収まる / 端 [0,90] では収まらない
        self.assertTrue(pass_fits_limits(cmds, JointLimits(xel=(-45.0, 45.0))))
        self.assertFalse(pass_fits_limits(cmds, JointLimits(xel=(0.0, 90.0))))

    def test_within_limits_basics(self):
        """within_limits の境界・周期方位・XElレンジ。"""
        self.assertTrue(within_limits((0.0, 45.0, 0.0), JointLimits()))
        # El 90 超は不可
        self.assertFalse(within_limits((0.0, 91.0, 0.0), JointLimits()))
        # 中央±45 では ξ=40 可 / ξ=50 不可
        self.assertTrue(
            within_limits((0.0, 80.0, 40.0), JointLimits(xel=(-45.0, 45.0)))
        )
        self.assertFalse(
            within_limits((0.0, 80.0, 50.0), JointLimits(xel=(-45.0, 45.0)))
        )
        # 端 [0,90] では負の ξ は不可
        self.assertFalse(
            within_limits((0.0, 80.0, -10.0), JointLimits(xel=(0.0, 90.0)))
        )
        # 方位の周期性: 限定レンジ [350,360]∪ラップで 5° は範囲外、355° は範囲内
        lim = JointLimits(az=(350.0, 360.0))
        self.assertTrue(within_limits((355.0, 45.0, 0.0), lim))
        self.assertFalse(within_limits((5.0, 45.0, 0.0), lim))


class TestActuatorTripod(unittest.TestCase):
    """3本リニアアクチュエータ(パラレル機構)の運動学。"""

    def test_home_is_symmetric(self):
        """home(天頂指向)では3脚が同長。"""
        L = leg_lengths(0.0, 90.0)
        self.assertAlmostEqual(L[0], L[1], places=9)
        self.assertAlmostEqual(L[1], L[2], places=9)
        self.assertAlmostEqual(L[0], home_length(), places=12)

    def test_leg_lengths_golden(self):
        """既知寸法での脚長(Python実装の回帰固定・JSシムとの突き合わせ元)。"""
        golden = {
            (0.0, 90.0): (1.030776, 1.030776, 1.030776),
            (0.0, 70.0): (1.030776, 1.135269, 0.934964),
            (90.0, 75.0): (0.946381, 1.075483, 1.075483),
            (180.0, 60.0): (1.030776, 0.895317, 1.186512),
            (270.0, 80.0): (1.091070, 1.001658, 1.001658),
        }
        for (a, h), g in golden.items():
            L = leg_lengths(a, h)
            for got, exp in zip(L, g):
                self.assertAlmostEqual(got, exp, places=5, msg=f"({a},{h})")

    def test_tilt_azimuth_symmetry(self):
        """方位を変えても傾き量が同じなら脚長は巡回(全方位対称)。"""
        # a=0 と a=120 は取付方位(120°間隔)ぶん巡回した脚長になる
        l0 = leg_lengths(90.0, 70.0)  # φ=90 の脚へ向けて傾ける
        l1 = leg_lengths(210.0, 70.0)  # φ=210 の脚へ
        self.assertAlmostEqual(sorted(l0)[0], sorted(l1)[0], places=6)
        self.assertAlmostEqual(sorted(l0)[2], sorted(l1)[2], places=6)

    def test_workspace_is_zenith_cap(self):
        """到達範囲は天頂まわりの円錐。天頂は可、低仰角は不可。"""
        self.assertTrue(reachable(0.0, 90.0))  # 天頂
        self.assertTrue(reachable(123.0, 80.0))  # 高仰角・全方位可
        self.assertFalse(reachable(0.0, 20.0))  # 低仰角はストローク外
        beta = max_zenith_distance()
        self.assertGreaterEqual(beta, 40.0)  # 代表寸法で ~45°(仰角45°以上)
        self.assertLessEqual(beta, 60.0)

    def test_custom_geometry(self):
        """寸法を変えると到達円錐が変わる(スライダー化の妥当性)。"""
        wide = TripodGeometry(stroke=(0.5, 1.6))
        narrow = TripodGeometry(stroke=(1.0, 1.1))
        self.assertGreater(max_zenith_distance(wide), max_zenith_distance(narrow))


class TestSun(unittest.TestCase):
    """太陽位置(NOAA/Meeus 系)— 標準ライブラリのみ。"""

    def test_meeus_example_25a(self):
        """Meeus 例25.a(1992-10-13 0h TD)の赤経・赤緯と一致(NOAA低次法)。"""
        ra, dec = _sun_ra_dec(_julian_day(datetime(1992, 10, 13, 0, 0, 0)))
        self.assertAlmostEqual(ra, 198.3808, places=2)  # Meeus低次法 198.38083°
        self.assertAlmostEqual(dec, -7.7851, places=3)  # Meeus -7.78507°

    def test_solstice_transit_elevation(self):
        """夏至・東京の南中高度 = 90 − |緯度 − 赤緯| ≈ 77.76°、方位 ≈ 南。"""
        lat, lon = 35.681, 139.767
        t0 = datetime(2024, 6, 21, 0, 0, 0, tzinfo=timezone.utc)
        best_el, best_az = -99.0, None
        for m in range(0, 1440, 1):
            az, el = sun_altaz(lat, lon, t0 + timedelta(minutes=m), refraction=False)
            if el > best_el:
                best_el, best_az = el, az
        self.assertAlmostEqual(best_el, 90.0 - abs(lat - 23.44), delta=0.2)
        self.assertAlmostEqual(best_az, 180.0, delta=1.0)

    def test_equinox_declination_near_zero(self):
        """春分の頃は太陽赤緯がほぼ 0。"""
        _, dec = _sun_ra_dec(_julian_day(datetime(2024, 3, 20, 3, 6, 0)))
        self.assertLess(abs(dec), 0.2)

    def test_refraction_monotone_and_bounds(self):
        """大気差は地平で最大(~0.5°)、高仰角でほぼ 0、単調減少。"""
        self.assertAlmostEqual(refraction_deg(0.0), 0.483, delta=0.02)
        self.assertLess(refraction_deg(80.0), 0.01)
        self.assertGreater(refraction_deg(10.0), refraction_deg(40.0))

    def test_refraction_toggle_raises_apparent_elevation(self):
        """refraction=True の高度は False(幾何学)より大気差ぶん高い。"""
        lat, lon = 35.681, 139.767
        t = datetime(2024, 3, 20, 6, 0, 0, tzinfo=timezone(timedelta(hours=9)))
        _, el_geom = sun_altaz(lat, lon, t, refraction=False)
        _, el_app = sun_altaz(lat, lon, t, refraction=True)
        self.assertAlmostEqual(el_app - el_geom, refraction_deg(el_geom), places=6)
        self.assertGreater(el_app, el_geom)

    def test_timezone_aware_equals_utc(self):
        """tz 付き入力は UTC 換算され、同一時刻なら結果が一致。"""
        lat, lon = 35.681, 139.767
        jst = datetime(2024, 3, 20, 21, 0, 0, tzinfo=timezone(timedelta(hours=9)))
        utc = datetime(2024, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(sun_altaz(lat, lon, jst), sun_altaz(lat, lon, utc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
