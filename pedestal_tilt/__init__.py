"""パラボラアンテナ台座傾き推定・補正パッケージ。"""

from .geometry import (
    correction,
    forward_pointing,
    image_offset,
    tilt_rotation_matrix,
)
from .solver import Observation, fit_tilt
from .three_axis import (
    JointLimits,
    forward_3axis,
    ik_3axis,
    ik_3axis_hold,
    max_azimuth_step,
    pass_fits_limits,
    peak_abs_xel,
    plan_pass,
    within_limits,
)
from .actuator_tripod import (
    DEFAULT as TRIPOD_DEFAULT,
    TripodGeometry,
    base_point,
    home_length,
    leg_lengths,
    legs_within_stroke,
    max_zenith_distance,
    platform_point,
    reachable,
)
from .sun import delta_t_seconds, refraction_deg, sun_altaz

__all__ = [
    "Observation",
    "correction",
    "fit_tilt",
    "forward_pointing",
    "image_offset",
    "tilt_rotation_matrix",
    # 3軸(Az–El–XEl)マウント
    "forward_3axis",
    "ik_3axis",
    "ik_3axis_hold",
    "plan_pass",
    "max_azimuth_step",
    # 関節可動域
    "JointLimits",
    "within_limits",
    "pass_fits_limits",
    "peak_abs_xel",
    # 3本アクチュエータ(パラレル機構)
    "TripodGeometry",
    "TRIPOD_DEFAULT",
    "leg_lengths",
    "base_point",
    "platform_point",
    "legs_within_stroke",
    "reachable",
    "home_length",
    "max_zenith_distance",
    # 太陽位置(観測地・日時 → 方位/高度)
    "sun_altaz",
    "refraction_deg",
    "delta_t_seconds",
]
