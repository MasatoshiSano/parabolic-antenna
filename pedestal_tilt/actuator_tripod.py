"""3本リニアアクチュエータ(トライポッド/パラレル機構)の運動学。

写真の実機は Az–El–XEl の回転ジンバル(three_axis.py)ではなく、中央支点まわりに
張った **3本の可変長アクチュエータ(蛇腹シリンダ)** の伸縮で皿の向きを作る
パラレル機構である。本モジュールは皿の指向 (a, h) から各脚長 Lᵢ を求める
逆運動学を提供する。

- home(中立, 全脚同長)で皿は **天頂** を向く。
- 指向 (a, h) は「天頂から θ=90−h を方位 a へ傾けた姿勢」で表し、回転は
  geometry.tilt_rotation_matrix を流用する(中央支点まわりの 2 自由度の傾き)。
- 各脚長はストローク [Lmin, Lmax] 内でのみ実現でき、到達範囲は **天頂まわりの
  円錐(cap)** になる(回転ジンバルの天頂キーホールとは別種の制約)。
- 全方位 360° は脚長の配分で到達できるが、低仰角はストロークで頭打ちになる。

単位は任意(長さは相対値)。角度は degrees。標準ライブラリのみ。
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Sequence, Tuple

from .geometry import _matvec, tilt_rotation_matrix

Triple = Tuple[float, float, float]


@dataclass(frozen=True)
class TripodGeometry:
    """3本アクチュエータの取付・寸法(代表値)。"""

    pivot_height: float = 1.0  # 中央支点の高さ(基台面から)
    base_radius: float = 0.6  # 基台側取付円の半径
    platform_radius: float = 0.35  # 皿側取付円の半径
    base_z: float = 0.0  # 基台側取付点の高さ
    platform_offset: float = 0.0  # 皿側取付点の支点からの高さ(皿フレーム)
    mount_azimuths_deg: Triple = (90.0, 210.0, 330.0)
    stroke: Tuple[float, float] = (0.80, 1.30)  # (Lmin, Lmax)


DEFAULT = TripodGeometry()


def base_point(phi_deg: float, geom: TripodGeometry = DEFAULT) -> Triple:
    """基台側取付点 Bᵢ(固定)。"""
    r = math.radians(phi_deg)
    return (geom.base_radius * math.cos(r), geom.base_radius * math.sin(r), geom.base_z)


def platform_point(
    phi_deg: float, a_deg: float, h_deg: float, geom: TripodGeometry = DEFAULT
) -> Triple:
    """皿側取付点 Pᵢ = O + R(a,h)·pᵢ(指向に応じて支点まわりに動く)。"""
    R = tilt_rotation_matrix(90.0 - h_deg, a_deg)
    r = math.radians(phi_deg)
    p = (
        geom.platform_radius * math.cos(r),
        geom.platform_radius * math.sin(r),
        geom.platform_offset,
    )
    Rp = _matvec(R, p)
    return (Rp[0], Rp[1], geom.pivot_height + Rp[2])


def leg_lengths(a_deg: float, h_deg: float, geom: TripodGeometry = DEFAULT) -> Triple:
    """皿の指向 (a, h) を実現する3本のアクチュエータ長 (L1, L2, L3)。逆運動学(閉形式)。"""
    out = []
    for phi in geom.mount_azimuths_deg:
        P = platform_point(phi, a_deg, h_deg, geom)
        B = base_point(phi, geom)
        out.append(math.dist(P, B))
    return tuple(out)


def legs_within_stroke(
    lengths: Sequence[float], geom: TripodGeometry = DEFAULT
) -> bool:
    """3脚すべてがストローク [Lmin, Lmax] 内か。"""
    lo, hi = geom.stroke
    return all(lo - 1e-9 <= L <= hi + 1e-9 for L in lengths)


def reachable(a_deg: float, h_deg: float, geom: TripodGeometry = DEFAULT) -> bool:
    """指向 (a, h) がストローク内で実現可能か(=機構の到達範囲内か)。"""
    return legs_within_stroke(leg_lengths(a_deg, h_deg, geom), geom)


def home_length(geom: TripodGeometry = DEFAULT) -> float:
    """home(天頂指向)での脚長(全脚同じ)。"""
    return leg_lengths(0.0, 90.0, geom)[0]


def max_zenith_distance(geom: TripodGeometry = DEFAULT) -> float:
    """全方位で到達できる最大の天頂距離 β [deg](=到達円錐の半角)。

    仰角 90−β 以上・全方位に届く。これがパラレル機構の「ワークスペース」制約で、
    回転ジンバルの天頂キーホールに相当する別種の限界。
    """
    best = 0.0
    for b in range(0, 90):
        if all(reachable(g, 90.0 - b, geom) for g in range(0, 360, 5)):
            best = float(b)
    return best
