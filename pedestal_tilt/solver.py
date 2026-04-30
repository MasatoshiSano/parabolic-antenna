"""観測ずれデータから台座傾き (θ_t, φ_t) を推定する。"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass
class Observation:
    """1観測:太陽の真位置と像で測ったずれ。"""
    a_sun_deg: float          # 太陽の真方位 [deg]
    h_sun_deg: float          # 太陽の真高度 [deg]
    dh_image_deg: float       # 像でのたて方向ずれ Δh [deg]
    dac_image_deg: Optional[float] = None  # 像でのよこ方向ずれ Δa·cosh [deg](任意)


def _solve_2x2(AtA, Atb):
    """2x2 線形系の逆計算。"""
    a, b = AtA[0]
    c, d = AtA[1]
    det = a * d - b * c
    if abs(det) < 1e-15:
        raise ValueError(f"Singular normal-equation matrix (det={det})")
    inv = ((d / det, -b / det), (-c / det, a / det))
    p = inv[0][0] * Atb[0] + inv[0][1] * Atb[1]
    q = inv[1][0] * Atb[0] + inv[1][1] * Atb[1]
    return p, q


def fit_tilt(
    observations: Sequence[Observation],
) -> Tuple[float, float, List[float]]:
    """最小二乗で (θ_t, φ_t) を推定。

    線形パラメータ p = θ cos φ, q = θ sin φ で解く:
        Δh         = p cos(a) + q sin(a)
        Δa·cosh    = (p sin(a) − q cos(a)) · sin(h)

    Returns
    -------
    theta_t_deg : float
    phi_t_deg   : float (0–360°)
    residuals   : list[float]  予測値 − 実測値(各方程式ごと)
    """
    rows: List[List[float]] = []
    rhs: List[float] = []
    for obs in observations:
        a = math.radians(obs.a_sun_deg)
        rows.append([math.cos(a), math.sin(a)])
        rhs.append(obs.dh_image_deg)
        if obs.dac_image_deg is not None:
            h = math.radians(obs.h_sun_deg)
            rows.append([math.sin(a) * math.sin(h), -math.cos(a) * math.sin(h)])
            rhs.append(obs.dac_image_deg)

    AtA = [[0.0, 0.0], [0.0, 0.0]]
    Atb = [0.0, 0.0]
    for r, y in zip(rows, rhs):
        for i in range(2):
            for j in range(2):
                AtA[i][j] += r[i] * r[j]
            Atb[i] += r[i] * y
    p, q = _solve_2x2(AtA, Atb)

    theta = math.hypot(p, q)
    phi = math.degrees(math.atan2(q, p)) % 360.0
    residuals = [r[0] * p + r[1] * q - y for r, y in zip(rows, rhs)]
    return theta, phi, residuals
