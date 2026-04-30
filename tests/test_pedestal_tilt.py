"""pedestal_tilt パッケージの単体テスト(stdlib unittest)。"""
from __future__ import annotations
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pedestal_tilt import (
    Observation,
    correction,
    fit_tilt,
    forward_pointing,
    image_offset,
    tilt_rotation_matrix,
)


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
        for a_calc, h_calc in [(90.0, 30.0), (180.0, 70.0), (270.0, 30.0), (45.0, 50.0)]:
            a_cmd, h_cmd = correction(a_calc, h_calc, theta, phi)
            a_act, h_act = forward_pointing(a_cmd, h_cmd, theta, phi)
            err_a = ((a_act - a_calc + 540) % 360) - 180
            err_h = h_act - h_calc
            self.assertLess(abs(err_a), 0.05, f"az error too large at ({a_calc}, {h_calc}): {err_a}")
            self.assertLess(abs(err_h), 0.05, f"alt error too large at ({a_calc}, {h_calc}): {err_h}")


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
            Observation(90.0,  30.0, dh_image_deg=-0.5),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
