"""3軸(Az–El–XEl)マウントの運動学 — 天頂キーホールの除去。

2軸(方位–高度)マウントは、高度が 0–90° しか動けないため天頂付近で方位を
ほぼ 180° 振らねばならず(キーホール)、補正式の tan(h) も天頂で発散する。
最上部にクロスエレベーション軸 XEl(視軸を左右に倒す第3軸)を1つ足すと、
天頂を「またいで」追尾でき、方位の急回転を避けられる。

座標・単位の規約は geometry.py に一致:
  方位 a:北=0°, 東=90°  高度 h:地平=0°, 天頂=90°  すべて degrees。
  視軸ゼロ基準 x̂ = (1,0,0)(北・地平)。

順運動学(マウント座標 → 真地平座標):
    u_mount = Rz(a) · Ey(h) · Rz(ξ) · x̂
    u_true  = R_tilt(θ_t, φ_t) · u_mount
  ξ = 0 のとき forward_pointing(a, h, θ_t, φ_t) に厳密一致する(2軸の上位互換)。
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .geometry import (
    Mat3,
    Vec3,
    _altaz_to_unit,
    _matvec,
    _unit_to_altaz,
    tilt_rotation_matrix,
)

# 関節指令の3つ組 (a, h, ξ) [deg]
Joint = Tuple[float, float, float]
# 空の目標位置 (a, h) [deg]
SkyPoint = Tuple[float, float]


# --- 基本回転(degrees ではなく radians を受ける内部ヘルパ) ---


def _Rz(alpha: float) -> Mat3:
    """天頂(z)軸まわりの回転(北 x → 東 y)。"""
    c, s = math.cos(alpha), math.sin(alpha)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _Ey(h: float) -> Mat3:
    """東(y)軸まわりの高度回転(視軸 x を天頂 z へ持ち上げる)。

    Ey(h) · x̂ = (cos h, 0, sin h) となる向きに定義(Rz(a) と合成すると
    _altaz_to_unit(a, h) に一致)。
    """
    c, s = math.cos(h), math.sin(h)
    return ((c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c))


def _matmul(A: Mat3, B: Mat3) -> Mat3:
    return tuple(
        tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _transpose(M: Mat3) -> Mat3:
    return tuple(tuple(M[j][i] for j in range(3)) for i in range(3))


def forward_3axis(
    a_cmd_deg: float,
    h_cmd_deg: float,
    xel_cmd_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
) -> Tuple[float, float]:
    """指令 (a, h, ξ) を送ったときの真地平座標での実指向 (a', h')。

    厳密3D回転。xel_cmd_deg = 0 のとき forward_pointing と一致する。
    """
    a = math.radians(a_cmd_deg)
    h = math.radians(h_cmd_deg)
    x = math.radians(xel_cmd_deg)
    bore = (1.0, 0.0, 0.0)
    u = _matvec(_Rz(x), bore)
    u = _matvec(_Ey(h), u)
    u = _matvec(_Rz(a), u)
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    return _unit_to_altaz(_matvec(R, u))


def ik_3axis_hold(
    a_tgt_deg: float,
    h_tgt_deg: float,
    a_hold_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
) -> Joint:
    """方位関節を a_hold に固定したまま目標 (a_tgt, h_tgt) を狙う閉形式 IK。

    冗長性(3関節 vs 2自由度)を「方位を凍結する」ことで解消する戦略。
    天頂付近では方位を振らず XEl が横方向の動きを引き受けるため、
    2軸の 180° 方位スピンを回避できる(キーホール除去の中核)。

    Returns (a_hold, h, ξ) [deg]。h が [0, 90] を外れる場合、その保持方位では
    物理的に届かない(呼び出し側で判定する)。
    """
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    u_true = _altaz_to_unit(a_tgt_deg, h_tgt_deg)
    u_mount = _matvec(_transpose(R), u_true)
    # 保持方位を外す: v = Rz(-a_hold) · u_mount
    v = _matvec(_Rz(-math.radians(a_hold_deg)), u_mount)
    vx, vy, vz = v
    # Ey(h)·Rz(ξ)·x̂ = (cos h cos ξ, sin ξ, sin h cos ξ) と照合
    xel = math.degrees(math.atan2(vy, math.hypot(vx, vz)))
    h = math.degrees(math.atan2(vz, vx))
    return a_hold_deg % 360.0, h, xel


def ik_3axis(
    a_tgt_deg: float,
    h_tgt_deg: float,
    theta_t_deg: float,
    phi_t_deg: float,
    *,
    hold_azimuth_deg: Optional[float] = None,
    keyhole_deg: float = 10.0,
) -> Joint:
    """単点 IK。目標 (a_tgt, h_tgt) を狙う関節指令 (a, h, ξ)。

    - hold_azimuth_deg 指定時:その方位を固定して解く(ik_3axis_hold)。
    - 非指定 かつ キーホール外(マウント天頂距離 ≥ keyhole_deg):
      標準2軸(ξ=0)。
    - 非指定 かつ キーホール内:単点では履歴が無いため目標方位を保持軸に
      採るのみ(連続パスでの真価は plan_pass を使うこと)。
    """
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    u_mount = _matvec(_transpose(R), _altaz_to_unit(a_tgt_deg, h_tgt_deg))
    a_mount, h_mount = _unit_to_altaz(u_mount)
    if hold_azimuth_deg is not None:
        return ik_3axis_hold(
            a_tgt_deg, h_tgt_deg, hold_azimuth_deg, theta_t_deg, phi_t_deg
        )
    if (90.0 - h_mount) >= keyhole_deg:
        return a_mount % 360.0, h_mount, 0.0
    return ik_3axis_hold(a_tgt_deg, h_tgt_deg, a_mount, theta_t_deg, phi_t_deg)


def _mount_altaz(a_tgt_deg: float, h_tgt_deg: float, R_t: Mat3) -> Tuple[float, float]:
    """真地平の目標をマウント座標の (方位, 高度) に変換(R_t = Rᵀ)。"""
    return _unit_to_altaz(_matvec(R_t, _altaz_to_unit(a_tgt_deg, h_tgt_deg)))


def plan_pass(
    samples: Sequence[SkyPoint],
    theta_t_deg: float,
    phi_t_deg: float,
    *,
    keyhole_deg: float = 10.0,
    strategy: str = "3axis",
) -> List[Joint]:
    """太陽/衛星パス(真地平の (a, h) 列)に対する関節指令列を生成。

    strategy="2axis":
        常に ξ=0。天頂付近で方位が ~180° 跳ぶ様子(キーホール)を再現。
    strategy="3axis":
        キーホール外は2軸、キーホール内は「方位保持」戦略。保持方位は
        その区間の最大高度(culmination)点のマウント方位に揃え、XEl が
        天頂越えの横方向運動を引き受ける。高度関節が物理範囲 [0,90] を
        外れる点は2軸にフォールバック(縁の低高度で安全に処理)。
    """
    R = tilt_rotation_matrix(theta_t_deg, phi_t_deg)
    R_t = _transpose(R)
    mount = [_mount_altaz(a, h, R_t) for (a, h) in samples]

    if strategy == "2axis":
        return [(am % 360.0, hm, 0.0) for (am, hm) in mount]

    if strategy != "3axis":
        raise ValueError(f"unknown strategy: {strategy!r}")

    in_cone = [(90.0 - hm) < keyhole_deg for (_, hm) in mount]
    # キーホール区間の保持方位 = 最大高度点のマウント方位
    hold_az: Optional[float] = None
    best_h = -1e9
    for inside, (am, hm) in zip(in_cone, mount):
        if inside and hm > best_h:
            best_h, hold_az = hm, am

    commands: List[Joint] = []
    for (a_tgt, h_tgt), inside, (am, hm) in zip(samples, in_cone, mount):
        if not inside or hold_az is None:
            commands.append((am % 360.0, hm, 0.0))
            continue
        a, h, xel = ik_3axis_hold(a_tgt, h_tgt, hold_az, theta_t_deg, phi_t_deg)
        if h < 0.0 or h > 90.0:  # 保持方位では届かない縁 → 2軸へ
            commands.append((am % 360.0, hm, 0.0))
        else:
            commands.append((a, h, xel))
    return commands


def max_azimuth_step(commands: Sequence[Joint]) -> float:
    """連続指令間の最大方位差 [deg](±180 に正規化した絶対値)。"""
    m = 0.0
    for (a0, _, _), (a1, _, _) in zip(commands, commands[1:]):
        d = abs(((a1 - a0 + 540.0) % 360.0) - 180.0)
        if d > m:
            m = d
    return m


# --- 関節可動域(ハードウェアのストッパ範囲) ---


@dataclass(frozen=True)
class JointLimits:
    """各関節の可動域 [deg]。(min, max) で与える。

    XEl(第3軸)の既定は (-45, 45) ＝ **中立をストロークの中央に置いた 90° 幅**。
    天頂越えに必要な ξ は両振り(±キーホール半径ぶん)になるため、中立を端
    (例 (0, 90))に置くと負側が範囲外になり追尾が破綻する。中立を中央に置けば
    同じ 90° 幅でもキーホール除去が成立する。
    """

    az: Tuple[float, float] = (0.0, 360.0)
    el: Tuple[float, float] = (0.0, 90.0)
    xel: Tuple[float, float] = (-45.0, 45.0)


def _in_range(value: float, lo: float, hi: float, *, periodic: bool = False) -> bool:
    if periodic:
        span = hi - lo
        if span >= 360.0:
            return True
        return ((value - lo) % 360.0) <= span + 1e-9
    return lo - 1e-9 <= value <= hi + 1e-9


def within_limits(joint: Joint, limits: JointLimits = JointLimits()) -> bool:
    """関節指令 (a, h, ξ) が可動域に収まるか。方位は周期性を考慮。"""
    a, h, xel = joint
    return (
        _in_range(a, limits.az[0], limits.az[1], periodic=True)
        and _in_range(h, limits.el[0], limits.el[1])
        and _in_range(xel, limits.xel[0], limits.xel[1])
    )


def pass_fits_limits(
    commands: Sequence[Joint], limits: JointLimits = JointLimits()
) -> bool:
    """指令列が全点で可動域に収まるか(=その可動域でパスを追尾できるか)。"""
    return all(within_limits(c, limits) for c in commands)


def peak_abs_xel(commands: Sequence[Joint]) -> float:
    """指令列における |ξ| の最大値 [deg](必要な XEl 半ストローク)。"""
    return max((abs(c[2]) for c in commands), default=0.0)
