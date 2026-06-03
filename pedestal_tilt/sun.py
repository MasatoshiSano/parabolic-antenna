"""観測地・日時から太陽の地平座標 (方位, 高度) を計算する(標準ライブラリのみ)。

`examples/demo.py` のように太陽位置をハードコードする代わりに、緯度・経度・UTC
日時から厳密に求める。アルゴリズムは NOAA Solar Calculator / Jean Meeus
"Astronomical Algorithms" に基づく低次近似で、誤差は概ね 0.01° 級(本問題の
台座傾き推定には十分)。

規約は本パッケージに合わせる:
  方位 a: 北 = 0°, 東 = 90°(時計回り)
  高度 h: 地平 = 0°, 天頂 = 90°

時刻系: 太陽の視位置は TT(地球時)で、地球自転(恒星時)は UT で評価し、両者の差
ΔT を考慮する(既定はモデル値、`delta_t_s` で上書き可)。大気差は既定で含める
(`refraction=False` で幾何学的な真位置)。
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Optional, Tuple

_RAD = math.pi / 180.0


def _to_utc_naive(dt: datetime) -> datetime:
    """tz 付きなら UTC へ変換、naive なら UTC とみなす。"""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _julian_day(dt: datetime) -> float:
    """naive UTC datetime → ユリウス日(グレゴリオ暦, Meeus)。"""
    year, month = dt.year, dt.month
    day = (
        dt.day
        + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60.0) / 60.0)
        / 24.0
    )
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def delta_t_seconds(year_fraction: float) -> float:
    """ΔT = TT − UT [秒] の近似(Espenak & Meeus, 2005–2050 で良好)。

    範囲外の年でも破綻はしないが精度は落ちる(現代の利用を想定)。
    """
    t = year_fraction - 2000.0
    return 62.92 + 0.32217 * t + 0.005589 * t * t


def refraction_deg(true_elevation_deg: float) -> float:
    """幾何学的高度 → 大気差 [deg](Sæmundsson, 標準大気)。地平下は 0。"""
    h = true_elevation_deg
    if h < -1.0:
        return 0.0
    r_arcmin = 1.02 / math.tan((h + 10.3 / (h + 5.11)) * _RAD)
    return r_arcmin / 60.0


def _sun_ra_dec(jd_tt: float) -> Tuple[float, float]:
    """ユリウス日(TT) → 太陽の視赤経・赤緯 (α, δ) [deg]。"""
    t = (jd_tt - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360.0  # 平均黄経
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)  # 平均近点角
    mr = m * _RAD
    c = (
        math.sin(mr) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * mr) * (0.019993 - 0.000101 * t)
        + math.sin(3 * mr) * 0.000289
    )  # 中心差
    true_long = l0 + c
    omega = (125.04 - 1934.136 * t) * _RAD
    lam = (true_long - 0.00569 - 0.00478 * math.sin(omega)) * _RAD  # 視黄経
    eps0 = (
        23.0
        + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    )
    eps = (eps0 + 0.00256 * math.cos(omega)) * _RAD  # 黄道傾斜(補正)
    dec = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))) % 360.0
    return ra, dec


def _gmst_deg(jd_ut: float) -> float:
    """ユリウス日(UT) → グリニッジ平均恒星時 [deg]。"""
    d = jd_ut - 2451545.0
    t = d / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * d
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )
    return gmst % 360.0


def sun_altaz(
    lat_deg: float,
    lon_deg: float,
    when_utc: datetime,
    *,
    refraction: bool = True,
    delta_t_s: Optional[float] = None,
) -> Tuple[float, float]:
    """観測地 (lat, lon) ・UTC 日時 when_utc における太陽の (方位, 高度) [deg]。

    Parameters
    ----------
    lat_deg : 緯度(北が +)
    lon_deg : 経度(東が +)
    when_utc : datetime(tz 付きは UTC へ変換、naive は UTC とみなす)
    refraction : True なら大気差込みの「見かけの高度」、False なら幾何学的真高度
    delta_t_s : ΔT=TT−UT [秒]。None ならモデル値(delta_t_seconds)

    Returns
    -------
    (azimuth_deg, elevation_deg) : 方位(北=0,東=90)・高度(地平=0,天頂=90)
    """
    dt = _to_utc_naive(when_utc)
    jd_ut = _julian_day(dt)
    if delta_t_s is None:
        delta_t_s = delta_t_seconds(dt.year + (dt.month - 0.5) / 12.0)
    jd_tt = jd_ut + delta_t_s / 86400.0

    ra, dec = _sun_ra_dec(jd_tt)
    lst = (_gmst_deg(jd_ut) + lon_deg) % 360.0
    hour_angle = ((lst - ra + 180.0) % 360.0) - 180.0  # [-180,180]

    phi = lat_deg * _RAD
    dec_r = dec * _RAD
    h_r = hour_angle * _RAD
    elevation = math.degrees(
        math.asin(
            math.sin(phi) * math.sin(dec_r)
            + math.cos(phi) * math.cos(dec_r) * math.cos(h_r)
        )
    )
    # 南を 0・西を + で測った方位 → 北=0/東=90 へ変換
    a_south = math.atan2(
        math.sin(h_r), math.cos(h_r) * math.sin(phi) - math.tan(dec_r) * math.cos(phi)
    )
    azimuth = (math.degrees(a_south) + 180.0) % 360.0

    if refraction:
        elevation += refraction_deg(elevation)
    return azimuth, elevation
