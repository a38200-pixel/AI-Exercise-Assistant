"""프레임별 기하 추적: 무릎각 평활화와 BodyLock 정책(측면 판정이 유지될 때만 잠그고, 서 있는 동안 측면이 아니면 푼다).

정책(field_test_1 실측으로 정한 초기값, 2차 실측 전까지 확정 아님):
- 획득: STANDING(평활 무릎각이 STANDING_KNEE_ANGLE 이상)이고 전신이 유효하며 facing이 정해지고, **측면 판정이
  BODY_LOCK_ACQUIRE_SIDE_SECONDS 연속** 유지될 때만 잠근다. 측면이 아니면(정면·사선) 잠그지 않는다.
- 갱신: 잠긴 채 STANDING이면 측면으로 판정된 프레임에서만 다리·방향을 갱신한다. 비측면 프레임의 다리·방향은 버린다
  (정면에서는 발끝 방향이 불안정해 프레임마다 뒤집힌다).
- 해제: 잠긴 채 STANDING일 때 비측면 판정이 BODY_LOCK_RELEASE_NONSIDE_SECONDS 연속되면 푼다.
- 반복 중(STANDING이 아닐 때): 시점이 바뀌어도 다리·방향·시점을 고정한다. Pose를 BODY_LOCK_MISSING_RELEASE_SECONDS
  넘게 놓치면 푼다.
"""

from dataclasses import dataclass
from typing import Any, Sequence

from config.settings import (
    BODY_LOCK_ACQUIRE_SIDE_SECONDS,
    BODY_LOCK_MISSING_RELEASE_SECONDS,
    BODY_LOCK_RELEASE_GRACE_SECONDS,
    BODY_LOCK_RELEASE_NONSIDE_SECONDS,
    ONE_EURO_BETA,
    ONE_EURO_D_CUTOFF,
    REP_BOUNDARY_LIGHT_MIN_CUTOFF,
    REP_BOUNDARY_SIGNAL,
    STANDING_KNEE_ANGLE,
)
from src.pose_geometry import (
    BBox,
    BodyLock,
    Facing,
    FrameGeometry,
    Leg,
    OneEuroFilter,
    ViewClassifier,
    ViewJudgement,
    analyze_frame,
)


BOUNDARY_SIGNALS = ("smoothed", "light", "raw")  # REP_BOUNDARY_SIGNAL로 고를 수 있는 반복 경계용 무릎각 신호


@dataclass(frozen=True)
class LockState:
    """BodyLock의 현재 상태. event는 이 프레임에서 일어난 변화(없으면 None)다."""

    locked: bool
    leg: Leg | None = None
    facing: Facing | None = None
    view: ViewJudgement | None = None
    event: str | None = None  # "acquired" | "changed" | "released_view" | "released_missing"
    # 이벤트 상세(로그용): 해제면 {"reason", "seconds"}(비측면·놓침이 이어진 시간), 해제 뒤 다시 잠기면
    # {"unlocked_seconds", "previous_release_reason"}. 이벤트가 없으면 None.
    detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class TrackedFrame:
    geometry: FrameGeometry  # 잠금이 있으면 잠근 다리와 facing 기준
    geometry_now: FrameGeometry  # 이 프레임만 보고 계산한 값(잠금 무시). 잠금 정책 검증용
    knee_angle_smoothed: float | None  # 전신이 유효한 프레임의 무릎각만 평활화한다
    standing: bool
    lock: LockState
    # 반복 경계 판정용 무릎각(REP_BOUNDARY_SIGNAL). 기본("smoothed")은 knee_angle_smoothed와 같다. 무효 프레임은 둘 다 None.
    knee_angle_boundary: float | None = None


class BodyLockPolicy:
    """잠금을 걸고 푸는 시점만 정한다(기하 계산과 분리: 신호만 받으므로 로그의 신호로 그대로 재생할 수 있다).

    step()은 프레임마다 (STANDING 여부, 이 프레임의 측면 판정, 잠글 수 있는 프레임인지)를 받아 결정을 돌려준다.
    "acquire"(새로 잠금), "refresh"(잠긴 채 STANDING + 측면 프레임이라 다리·방향 갱신), "release_view"(비측면이
    이어져 해제), None(변화 없음). 사람을 놓친 프레임은 missing()으로 알린다.
    """

    def __init__(
        self,
        *,
        acquire_side_seconds: float = BODY_LOCK_ACQUIRE_SIDE_SECONDS,
        release_nonside_seconds: float = BODY_LOCK_RELEASE_NONSIDE_SECONDS,
        missing_release_seconds: float = BODY_LOCK_MISSING_RELEASE_SECONDS,
        release_grace_seconds: float = BODY_LOCK_RELEASE_GRACE_SECONDS,
    ) -> None:
        self._acquire_side_seconds = acquire_side_seconds
        self._release_nonside_seconds = release_nonside_seconds + release_grace_seconds  # 유예는 해제 기준에 더한다
        self._missing_release_seconds = missing_release_seconds
        self.reset()

    def reset(self) -> None:
        self.locked = False
        self.last_release: dict[str, Any] | None = None  # 마지막 해제의 사유·지속 시간(진단용)
        self.last_acquire: dict[str, Any] | None = None  # 마지막 획득이 이전 해제 뒤 몇 초 만인지(진단용)
        self._released_at: float | None = None
        self._side_since: float | None = None  # 측면 판정이 연속된 시작 시각
        self._nonside_since: float | None = None  # 비측면 판정이 연속된 시작 시각
        self._missing_since: float | None = None

    def step(self, timestamp: float, *, standing: bool, side_now: bool, lockable: bool) -> str | None:
        self._missing_since = None
        # 연속 시작 시각: 판정이 바뀌면 처음부터 다시 센다.
        self._side_since = (timestamp if self._side_since is None else self._side_since) if side_now else None
        self._nonside_since = None if side_now else (timestamp if self._nonside_since is None else self._nonside_since)
        if self.locked:
            if not standing:
                return None  # 반복 중에는 시점이 바뀌어도 고정한다
            if self._nonside_since is not None and timestamp - self._nonside_since >= self._release_nonside_seconds:
                self.locked = False
                self.last_release = {"reason": "non_side", "seconds": round(timestamp - self._nonside_since, 4)}
                self._released_at = timestamp
                return "release_view"
            if side_now and lockable:
                return "refresh"
            return None
        if standing and side_now and lockable and self._side_since is not None:
            if timestamp - self._side_since >= self._acquire_side_seconds:
                self.locked = True
                if self._released_at is not None and self.last_release is not None:
                    self.last_acquire = {
                        "unlocked_seconds": round(timestamp - self._released_at, 4),
                        "previous_release_reason": self.last_release["reason"],
                    }
                else:
                    self.last_acquire = None
                self._released_at = None
                return "acquire"
        return None

    def missing(self, timestamp: float) -> str | None:
        """사람·Pose를 놓친 프레임. 연속성이 끊기고, 오래 놓치면 "release_missing"으로 푼다(그 뒤에도 계속 알려 준다)."""
        self._side_since = None
        self._nonside_since = None
        if self._missing_since is None:
            self._missing_since = timestamp
        if timestamp - self._missing_since >= self._missing_release_seconds and self.locked:
            self.locked = False
            self.last_release = {"reason": "person_missing", "seconds": round(timestamp - self._missing_since, 4)}
            self._released_at = timestamp
            return "release_missing"
        return None

    def missing_long_enough(self, timestamp: float) -> bool:
        return self._missing_since is not None and timestamp - self._missing_since >= self._missing_release_seconds


class GeometryTracker:
    def __init__(
        self,
        *,
        standing_knee_angle: float = STANDING_KNEE_ANGLE,
        missing_release_seconds: float = BODY_LOCK_MISSING_RELEASE_SECONDS,
        acquire_side_seconds: float = BODY_LOCK_ACQUIRE_SIDE_SECONDS,
        release_nonside_seconds: float = BODY_LOCK_RELEASE_NONSIDE_SECONDS,
        release_grace_seconds: float = BODY_LOCK_RELEASE_GRACE_SECONDS,
        boundary_signal: str = REP_BOUNDARY_SIGNAL,
        boundary_light_min_cutoff: float = REP_BOUNDARY_LIGHT_MIN_CUTOFF,
        view_classifier: ViewClassifier | None = None,
        knee_filter: OneEuroFilter | None = None,
    ) -> None:
        if boundary_signal not in BOUNDARY_SIGNALS:
            raise ValueError(f"boundary_signal must be one of {BOUNDARY_SIGNALS}.")
        self._boundary_signal = boundary_signal
        self._boundary_filter = OneEuroFilter(min_cutoff=boundary_light_min_cutoff, beta=ONE_EURO_BETA, d_cutoff=ONE_EURO_D_CUTOFF)
        self._standing_knee_angle = standing_knee_angle
        self._missing_release_seconds = missing_release_seconds
        self._view_classifier = view_classifier
        self._knee_filter = knee_filter if knee_filter is not None else OneEuroFilter()
        self._lock = BodyLock()
        self._policy = BodyLockPolicy(
            acquire_side_seconds=acquire_side_seconds,
            release_nonside_seconds=release_nonside_seconds,
            missing_release_seconds=missing_release_seconds,
            release_grace_seconds=release_grace_seconds,
        )

    def reset(self) -> None:
        """운동 모드를 바꾸거나 새 세션을 시작할 때 잠금과 평활화 상태를 모두 버린다."""
        self._knee_filter.reset()
        self._boundary_filter.reset()
        self._lock.release()
        self._policy.reset()

    def lock_state(self, event: str | None = None, detail: dict[str, Any] | None = None) -> LockState:
        if not self._lock.is_locked:
            return LockState(locked=False, event=event, detail=detail)
        return LockState(
            locked=True,
            leg=self._lock.leg,
            facing=self._lock.facing,
            view=self._lock.view,
            event=event,
            detail=detail,
        )

    def update(
        self,
        landmarks: Sequence[Any],
        *,
        crop_bbox: BBox,
        person_bbox: BBox,
        frame_size: tuple[int, int],
        world_landmarks: Sequence[Any] | None,
        timestamp: float,
    ) -> TrackedFrame:
        """한 프레임을 분석하고 평활화와 잠금 정책을 적용한다. timestamp는 초 단위."""
        common = {
            "crop_bbox": crop_bbox,
            "person_bbox": person_bbox,
            "frame_size": frame_size,
            "world_landmarks": world_landmarks,
            "view_classifier": self._view_classifier,
        }
        geometry_now = analyze_frame(landmarks, **common)
        if self._lock.is_locked:
            geometry = analyze_frame(landmarks, leg=self._lock.leg, facing=self._lock.facing, **common)
        else:
            geometry = geometry_now

        smoothed = boundary = None
        if geometry.knee_angle is not None and geometry.full_body.valid:
            smoothed = self._knee_filter(geometry.knee_angle, timestamp)
            if self._boundary_signal == "light":
                boundary = self._boundary_filter(geometry.knee_angle, timestamp)
            elif self._boundary_signal == "raw":
                boundary = float(geometry.knee_angle)
            else:
                boundary = smoothed
        standing = smoothed is not None and smoothed >= self._standing_knee_angle

        lockable = geometry_now.full_body.valid and geometry_now.facing is not None
        decision = self._policy.step(
            timestamp, standing=standing, side_now=geometry_now.view.is_side, lockable=lockable
        )

        event = None
        detail = None
        if decision == "acquire":
            self._lock.acquire(geometry_now)  # 전신 유효, facing 확인됨이므로 항상 성공한다
            event = "acquired"
            detail = dict(self._policy.last_acquire) if self._policy.last_acquire else None
        elif decision == "refresh":
            before = (self._lock.leg, self._lock.facing)
            self._lock.release()
            self._lock.acquire(geometry_now)
            if before != (self._lock.leg, self._lock.facing):
                event = "changed"
        elif decision == "release_view":
            self._lock.release()
            event = "released_view"
            detail = dict(self._policy.last_release)

        return TrackedFrame(
            geometry=geometry,
            geometry_now=geometry_now,
            knee_angle_smoothed=smoothed,
            standing=standing,
            lock=self.lock_state(event, detail),
            knee_angle_boundary=boundary,
        )

    def update_missing(self, timestamp: float) -> LockState:
        """사람이나 Pose를 놓친 프레임. 연속성이 끊기므로 시점 연속 시간을 지우고, 오래 놓치면 잠금을 풀고 평활화를 초기화한다."""
        event = None
        detail = None
        if self._policy.missing(timestamp) == "release_missing":
            self._lock.release()
            event = "released_missing"
            detail = dict(self._policy.last_release)
        if self._policy.missing_long_enough(timestamp):
            self._knee_filter.reset()
            self._boundary_filter.reset()
        return self.lock_state(event, detail)
