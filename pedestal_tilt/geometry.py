"""台座傾きの順問題・逆問題・補正計算。

すべて degrees 単位。標準ライブラリ(math)のみを使用。
方位 a は北 = 0°、東 = 90° で測る。高度 h は地平 = 0°、天頂 = 90°。
"""
from __future__ import annotations
import math
from typing import Tuple

Vec3 = Tuple[float, float, float]
Mat3 = Tuple[Tuple[float, float, float], ...]


def _deg2rad(d: float) -> float:
    return d * math.pi / 180.0


def _rad2deg(r: float) -> float:
    return r * 180.0 / math.pi


def tilt_rotation_matrix(theta_t_deg: float, phi_t_deg: float) -> Mat3:
    """マウント座標 → 真地平座標 への回転行列 R (3x3)。

    マウントの天頂 z' を真の方位 phi_t、傾き角 theta_t の位置に持っていく
    水平軸回りの回転として定義する(Rodrigues の公式)。
    """
    theta = _deg2rad(theta_t_deg)
    phi = _deg2rad(phi_t_deg)
    n = (-math.sin(phi), math.cos(phi), 0.0)
    K = (
        (0.0, -n[2], n[1]),
        (n[2], 0.0, -n[0]),
        (-n[1], n[0], 0.0),
    )
    KK = tuple(
        tuple(sum(K[i][k] * K[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )
    s = math.sin(theta)
    c = 1.0 - math.cos(theta)
    R = tuple(
        tuple(
            (1.0 if i == j else 0.0) + s * K[i][j] + c * KK[i][j]
            for j in range(3)
        )
        for i in range(3)
    )
    return R


def _matvec(M: Mat3, v: Vec3) -> Vec3:
    return tuple(sum(M[i][k] * v[k] for k in range(3)) for i in range(3))


def _altaz_to_unit(a_deg: float, h_deg: float) -> Vec3:
    a = _deg2rad(a_deg)
    h = _deg2rad(h_deg)
    return (math.cos(h) * math.cos(a), math.cos(h) * math.sin(a), math.sin(h))


def _unit_to_altaz(u: Vec3) -> Tuple[float, float]:
    a = _rad2deg(math.atan2(u[1], u[0])) % 360.0
    h = _rad2deg(math.asin(max(-1.0, min(1.0, u[2]))))
    return a, h


def forward_pointing(
    a_cmd_deg: float,
    h_cmd_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
) -> Tuple[float, float]:
    """指令 (a_cmd, h_cmd) を送ったときの真地平座標での実指向 (a', h')。

    厳密3D回転を使用(線形近似ではない)。
    """
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    return _unit_to_altaz(_matvec(R, _altaz_to_unit(a_cmd_deg, h_cmd_deg)))


def image_offset(
    a_sun_deg: float,
    h_sun_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
) -> Tuple[float, float]:
    """太陽の真位置を指令したときの像でのずれ (Δh_image, Δa·cosh_image) [deg]。

    線形近似:
        Δh_image       = +θ · cos(a − φ)
        Δa·cosh_image  = +θ · sin(a − φ) · sin(h_sun)
    """
    da = _deg2rad(a_sun_deg - phi_t_deg)
    h = _deg2rad(h_sun_deg)
    dh = theta_t_deg * math.cos(da)
    dac = theta_t_deg * math.sin(da) * math.sin(h)
    return dh, dac


def correction(
    a_calc_deg: float,
    h_calc_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
) -> Tuple[float, float]:
    """真位置 (a_calc, h_calc) を像中央に置くための指令値 (a_cmd, h_cmd)。

    線形近似:
        h_cmd = h_calc + θ · cos(a_calc − φ)
        a_cmd = a_calc + θ · sin(a_calc − φ) · tan(h_calc)
    """
    da = _deg2rad(a_calc_deg - phi_t_deg)
    h = _deg2rad(h_calc_deg)
    h_cmd = h_calc_deg + theta_t_deg * math.cos(da)
    a_cmd = a_calc_deg + theta_t_deg * math.sin(da) * math.tan(h)
    return a_cmd % 360.0, h_cmd
