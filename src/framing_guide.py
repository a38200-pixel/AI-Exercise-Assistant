"""구도 안내: YOLO 사용자 bbox만으로 "너무 가깝다 / 가장자리에 걸렸다"를 판단해 한 줄 안내 코드를 낸다. 랜드마크 유무와 무관하다.

공백 분석(analysis/landmark_gaps/report.md)에서 PoseLandmarker가 포즈를 못 찾는 프레임은 거의 전부 bbox가 프레임 가장자리에 걸린 때였다
(crop이 안 잘리면 0.1%, 발 아래 여유 20px 이하 59~73%, 좌우로 잘리면 76%, bbox 높이 95% 이상 65%). 그 조건을 그대로 쓴다.

- 뒤로 물러서 주세요(NOTICE_MOVE_BACK): bbox 아래쪽(발)이 프레임 아래 경계에 닿거나 발 아래 여유가 프레임 높이의 FRAMING_FEET_MARGIN_RATIO 이하이거나,
  bbox 높이가 프레임 높이의 FRAMING_MAX_HEIGHT_RATIO 이상.
- 화면 가운데로 이동해 주세요(NOTICE_MOVE_CENTER): bbox가 왼쪽 또는 오른쪽 경계에 닿음. (아래·높이 조건이 함께면 뒤로 물러서기가 먼저다.)
- 위쪽(머리) 경계 접촉은 조건이 아니다(머리가 잘린 것만으로는 공백이 거의 늘지 않았다).
- 상태가 FRAMING_NOTICE_DELAY_SECONDS 이상 이어질 때만 안내한다. 가장자리 근처의 깜빡임으로 타이머가 리셋되지 않도록, 조건이 풀려도
  FRAMING_NOTICE_CLEAR_SECONDS 이상 이어져야 해제한다. 사람을 놓친 프레임은 상태를 바꾸지 않고(FRAMING_ABSENT_RESET_SECONDS를 넘기면 처음부터),
  반복 중(in_rep)에는 안내를 보이지 않는다(상태는 그대로 이어져 반복이 끝난 뒤 조건이 계속되면 곧바로 다시 보인다).
"""

from __future__ import annotations

from typing import Sequence

from config.settings import (
    BBOX_PADDING,
    FRAMING_ABSENT_RESET_SECONDS,
    FRAMING_EDGE_TOUCH_PX,
    FRAMING_FEET_MARGIN_RATIO,
    FRAMING_MAX_HEIGHT_RATIO,
    FRAMING_NOTICE_CLEAR_SECONDS,
    FRAMING_NOTICE_DELAY_SECONDS,
    FRAMING_SIDE_CROP_CUT_RATIO,
)

NOTICE_MOVE_BACK = "move_back"
NOTICE_MOVE_CENTER = "move_center"


def side_crop_cut(bbox: Sequence[float], frame_size: tuple[int, int]) -> float:
    """판정용 crop(bbox 양옆 BBOX_PADDING 만큼 여유)이 왼쪽·오른쪽 경계에서 잘린 정도: 여유 중 프레임 밖으로 나간 비율의 큰 쪽(0 = 여유가 다 있음, 1 = bbox가 경계에 닿음)."""
    width, _ = frame_size
    x1, _, x2, _ = bbox
    margin = BBOX_PADDING * (x2 - x1)
    if margin <= 0:
        return 0.0
    left = (margin - x1) / margin
    right = (x2 + margin - width) / margin
    return min(1.0, max(0.0, left, right))


def classify_framing(
    bbox: Sequence[float],
    frame_size: tuple[int, int],
    *,
    side_cut_ratio: float = FRAMING_SIDE_CROP_CUT_RATIO,
    vertical: bool = True,
) -> str | None:
    """bbox 한 개의 구도 문제. 없으면 None. 반환: NOTICE_MOVE_BACK / NOTICE_MOVE_CENTER.
    vertical=False면 아래·높이 조건을 보지 않는다(좌우 기준만 따로 검증할 때)."""
    width, height = frame_size
    x1, y1, x2, y2 = bbox
    feet_margin = height - y2
    if vertical and (
        feet_margin <= max(FRAMING_EDGE_TOUCH_PX, FRAMING_FEET_MARGIN_RATIO * height) or (y2 - y1) >= FRAMING_MAX_HEIGHT_RATIO * height
    ):
        return NOTICE_MOVE_BACK
    if side_crop_cut(bbox, frame_size) >= side_cut_ratio:
        return NOTICE_MOVE_CENTER
    return None


class FramingGuide:
    def __init__(
        self,
        *,
        delay_seconds: float = FRAMING_NOTICE_DELAY_SECONDS,
        clear_seconds: float = FRAMING_NOTICE_CLEAR_SECONDS,
        absent_reset_seconds: float = FRAMING_ABSENT_RESET_SECONDS,
        side_cut_ratio: float = FRAMING_SIDE_CROP_CUT_RATIO,
        vertical: bool = True,
    ) -> None:
        self._side_cut_ratio = side_cut_ratio
        self._vertical = vertical
        self._delay = delay_seconds
        self._clear = clear_seconds
        self._absent_reset = absent_reset_seconds
        self.reset()

    def reset(self) -> None:
        self._kind: str | None = None  # 지금 이어지고 있는 구도 문제
        self._since = 0.0  # 그 문제가 시작된 시각
        self._good_since: float | None = None  # 문제가 풀린 채로 이어진 시작 시각(해제 대기)
        self._absent_since: float | None = None

    def update(
        self,
        bbox: Sequence[float] | None,
        frame_size: tuple[int, int],
        timestamp: float,
        *,
        in_rep: bool = False,
    ) -> str | None:
        """프레임마다 부른다. bbox는 YOLO 주 사용자 bbox(없으면 None). 지금 보일 안내 코드(없으면 None)를 돌려준다."""
        if bbox is None:
            # 사람을 놓친 프레임은 상태를 바꾸지 않고 안내도 그대로 이어서 보인다(YOLO가 한두 프레임 놓칠 때 안내가 깜빡이지 않게).
            # 오래(FRAMING_ABSENT_RESET_SECONDS 초과) 안 보이면 처음부터.
            if self._absent_since is None:
                self._absent_since = timestamp
            if timestamp - self._absent_since > self._absent_reset:
                self.reset()
                self._absent_since = timestamp
                return None
            return None if in_rep else self._shown(timestamp)
        self._absent_since = None

        problem = classify_framing(bbox, frame_size, side_cut_ratio=self._side_cut_ratio, vertical=self._vertical)
        if problem is not None:
            if self._kind is None:
                self._since = timestamp
            self._kind = problem  # 종류만 바뀌면 타이머는 이어 간다(둘 다 구도 문제)
            self._good_since = None
        elif self._kind is not None:
            if self._good_since is None:
                self._good_since = timestamp
            if timestamp - self._good_since >= self._clear:
                self.reset()

        return None if in_rep else self._shown(timestamp)

    def _shown(self, timestamp: float) -> str | None:
        if self._kind is None or timestamp - self._since < self._delay:
            return None
        return self._kind
