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
]
