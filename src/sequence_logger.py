"""Landmark 시퀀스 로깅: 세션당 JSONL 파일 1개. 실시간 파이프라인을 막지 않도록 별도 스레드가 쓴다.

영상은 저장하지 않는다. 프레임마다 landmark(정규화 33개 + world 33개), 각도, 전신 유효 여부,
시점 신호, 잠금 상태, 라벨을 남긴다. 기본은 꺼져 있다(config.settings.SEQUENCE_LOGGING_ENABLED).

파일 형식(한 줄에 JSON 하나): 첫 줄 `session`(메타데이터, 설정 스냅샷), 이어서 `frame` 여러 줄(그 프레임에서 일어난
일은 바로 뒤에 `event` 줄), 정상 종료 시 마지막 줄 `end`. 중간에 프로세스가 죽어도 이미 flush된 줄은 읽을 수 있다.

format_version 2(RepTracker 진단): `frame`에 `rep`(RepTracker 상태·안내 사유)와 `lock.detail`이 생기고 `event` 줄이 생겼다.
event의 kind: `rep_end`(반복 후보가 끝날 때: 측정값·기준값·탈락 사유), `rep_merge_suspect`(반복 중 올라왔다가 복귀 각도에 닿지
못하고 다시 내려감), `lock`(BodyLock 획득·갱신·해제와 해제 사유·지속 시간). 버전 1 로그는 `rep`와 `event`가 없을 뿐 같은 형식이라
읽는 쪽이 둘 다 읽는다.
시간 값은 모두 로깅 시작 시점을 0으로 하는 time.perf_counter() 초다.
"""

import json
import platform
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import config.settings as settings
from src.geometry_tracker import GeometryTracker, LockState, TrackedFrame
from src.pose_classifier import LANDMARK_NAMES


FORMAT_VERSION = 2
SUPPORTED_FORMAT_VERSIONS = (1, 2)  # 읽는 쪽(분석·그래프 스크립트)이 받아들이는 버전
# event 안에서 RepTracker가 time.perf_counter() 값으로 넣은 시각 키. 기록할 때 세션 시작 기준 초로 바꾼다.
EVENT_TIME_KEYS = ("t", "t_start", "t_bottom", "t_end", "t_min", "t_peak", "rep_t_start")
INTENDED_POSTURES = ("normal", "shallow", "torso_lean", "heel_lift")
CAMERA_VIEWS = ("side", "oblique", "front")
# MediaPipe landmark 0~10번은 얼굴(코, 눈, 귀, 입)이다. 기본으로 좌표를 저장하지 않는다.
NOSE_INDEX = LANDMARK_NAMES.index("nose")
FACE_LANDMARK_COUNT = LANDMARK_NAMES.index("mouth_right") + 1
_FLOAT_DIGITS = 5
_STOP = object()


# ---------------------------------------------------------------- 메타데이터


def settings_snapshot() -> dict[str, Any]:
    """로그를 만든 시점의 임계값 스냅샷. JSON으로 쓸 수 없는 값(경로 등)은 제외한다."""
    snapshot: dict[str, Any] = {}
    for name, value in vars(settings).items():
        if not name.isupper() or name.startswith("_"):
            continue
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            continue
        snapshot[name] = value
    return dict(sorted(snapshot.items()))


def session_metadata(
    intended_posture: str | None = None,
    camera_view: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    if intended_posture is not None and intended_posture not in INTENDED_POSTURES:
        raise ValueError(f"intended_posture must be one of {INTENDED_POSTURES}: {intended_posture}")
    if camera_view is not None and camera_view not in CAMERA_VIEWS:
        raise ValueError(f"camera_view must be one of {CAMERA_VIEWS}: {camera_view}")
    return {"intended_posture": intended_posture, "camera_view": camera_view, "note": note}


# ---------------------------------------------------------------- 프레임 기록 만들기


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), _FLOAT_DIGITS)


def landmark_rows(
    landmarks: Sequence[Any] | None,
    *,
    include_face: bool = False,
    keep_nose_visibility: bool = False,
) -> list[list[float | None]] | None:
    """landmark를 [x, y, z, visibility] 목록으로 바꾼다. world landmark처럼 visibility가 없으면 None.

    얼굴 landmark(0~10번)는 기본으로 좌표를 저장하지 않는다. 인덱스가 landmark_names와 맞도록 행은
    33개를 유지하고 얼굴 행의 값은 모두 None으로 둔다. keep_nose_visibility이면 코(0번)의 visibility만
    남긴다(시점 신호 (c)용, 좌표는 아님).
    """
    if landmarks is None:
        return None
    rows: list[list[float | None]] = []
    for index, landmark in enumerate(landmarks):
        visibility = _round(getattr(landmark, "visibility", None))
        if index < FACE_LANDMARK_COUNT and not include_face:
            keep = keep_nose_visibility and index == NOSE_INDEX
            rows.append([None, None, None, visibility if keep else None])
            continue
        rows.append([_round(landmark.x), _round(landmark.y), _round(landmark.z), visibility])
    return rows


def build_labels(
    raw_prediction: dict[str, Any] | None,
    smoothing_state: dict[str, Any],
    display_pose: str,
    display_confidence: float,
) -> dict[str, Any]:
    """원래(표시 필터 전) 라벨과 표시 라벨을 함께 남긴다."""
    return {
        "raw": raw_prediction["label"] if raw_prediction else None,
        "raw_confidence": _round(raw_prediction["confidence"]) if raw_prediction else None,
        "stable": smoothing_state["stable_label"],
        "stable_confidence": _round(smoothing_state["stable_confidence"]),
        "candidate": smoothing_state["candidate_label"],
        "candidate_count": smoothing_state["candidate_count"],
        "missing_count": smoothing_state["missing_count"],
        "display": display_pose,
        "display_confidence": _round(display_confidence),
    }


def lock_record(lock: LockState) -> dict[str, Any]:
    return {
        "locked": lock.locked,
        "leg": lock.leg,
        "facing": lock.facing,
        "view_is_side": lock.view.is_side if lock.view is not None else None,
        "view_reasons": list(lock.view.reasons) if lock.view is not None else None,
        "event": lock.event,
        "detail": lock.detail,  # v2: 해제 사유·지속 시간, 해제 뒤 재잠금까지 걸린 시간
    }


def build_frame_record(
    *,
    t: float,
    t_logic: float,
    frame_size: tuple[int, int],
    person_confidence: float | None,
    yolo_bbox: Sequence[int] | None,
    crop_bbox: Sequence[int] | None,
    landmarks: Sequence[Any] | None,
    world_landmarks: Sequence[Any] | None,
    tracked: TrackedFrame | None,
    lock: LockState,
    labels: dict[str, Any],
    include_face_landmarks: bool = False,
    rep: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """프레임 한 줄의 내용. t는 프레임을 읽은 직후, t_logic은 운동 로직이 실행된 시각(세션 시간, 초).

    include_face_landmarks가 False(기본)이면 얼굴 landmark(0~10번)의 좌표는 정규화·world 모두 기록하지
    않고, 코의 visibility만 정규화 landmark 행에 남는다.
    """
    geometry = full_body = view = None
    if tracked is not None:
        current = tracked.geometry
        signals = current.view_signals
        geometry = {
            "leg": current.leg,
            "facing": current.facing,
            "knee": _round(current.knee_angle),
            "torso": _round(current.torso_angle),
            "shin": _round(current.shin_angle),
            "torso_signed": _round(current.torso_angle_signed),
            "shin_signed": _round(current.shin_angle_signed),
            "knee_smoothed": _round(tracked.knee_angle_smoothed),
            "standing": tracked.standing,
            "leg_now": tracked.geometry_now.leg,
            "facing_now": tracked.geometry_now.facing,
        }
        full_body = {
            "valid": current.full_body.valid,
            "reasons": list(current.full_body.reasons),
            "notes": list(current.full_body.notes),
        }
        view = {
            "shoulder_ratio": _round(signals.shoulder_ratio),
            "hip_yaw_deg": _round(signals.hip_yaw_deg),
            "nose_visibility": _round(signals.nose_visibility),
            "is_side": current.view.is_side,
            "reasons": list(current.view.reasons),
        }

    return {
        "t": _round(t),
        "t_logic": _round(t_logic),
        "frame_size": list(frame_size),
        "person": yolo_bbox is not None,
        "person_confidence": _round(person_confidence),
        "yolo_bbox": list(yolo_bbox) if yolo_bbox is not None else None,
        "crop_bbox": list(crop_bbox) if crop_bbox is not None else None,
        "landmarks": landmark_rows(
            landmarks, include_face=include_face_landmarks, keep_nose_visibility=True
        ),
        "world_landmarks": landmark_rows(world_landmarks, include_face=include_face_landmarks),
        "geometry": geometry,
        "full_body": full_body,
        "view": view,
        "lock": lock_record(lock),
        "labels": labels,
        # v2: RepTracker 상태(WAITING_LOCK / STANDING / IN_REP)와 안내 사유. RepTracker를 안 쓰면 None.
        "rep": {"state": rep["state"], "notice": rep["notice"]} if rep is not None else None,
    }


# ---------------------------------------------------------------- 파일 기록


class SequenceLogger:
    """프레임 기록을 큐에 넣고 별도 스레드가 파일에 쓴다. 큐가 가득 차면 프레임을 버린다.

    파이프라인 쪽(log_frame)은 절대 블록되지 않는다. 버린 프레임은 frame 번호(i)의 공백과
    마지막 줄(end)의 frames_dropped로 알 수 있다.
    """

    def __init__(
        self,
        directory: Path,
        *,
        metadata: dict[str, Any],
        runtime: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        flush_interval: float = settings.SEQUENCE_LOG_FLUSH_INTERVAL_SECONDS,
        queue_size: int = settings.SEQUENCE_LOG_QUEUE_SIZE,
    ) -> None:
        self._directory = Path(directory)
        self._metadata = metadata
        self._runtime = runtime or {}
        self._options = options or {}
        self._flush_interval = flush_interval
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._thread: threading.Thread | None = None
        self._file = None
        self._path: Path | None = None
        self._start_perf = 0.0
        self._index = 0
        self._written = 0
        self._dropped = 0
        self._events_written = 0
        self._events_dropped = 0
        self._invalid = 0
        self._error: str | None = None
        self._closed = False

    @property
    def path(self) -> Path:
        if self._path is None:
            raise RuntimeError("SequenceLogger is not started.")
        return self._path

    @property
    def frames_dropped(self) -> int:
        return self._dropped

    @property
    def write_error(self) -> str | None:
        return self._error

    def to_session_time(self, perf_timestamp: float) -> float:
        """time.perf_counter() 값을 로깅 시작 기준 초로 바꾼다."""
        return perf_timestamp - self._start_perf

    def _open_file(self, started_at: datetime) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        parts = ["session", started_at.strftime("%Y%m%d_%H%M%S")]
        for key in ("intended_posture", "camera_view"):
            if self._metadata.get(key):
                parts.append(str(self._metadata[key]))
        stem = "_".join(parts)
        for attempt in range(100):
            suffix = "" if attempt == 0 else f"_{attempt}"
            path = self._directory / f"{stem}{suffix}.jsonl"
            try:
                self._file = path.open("x", encoding="utf-8", newline="\n")
            except FileExistsError:
                continue
            self._path = path
            return
        raise FileExistsError(f"Could not create a unique session file for {stem}")

    def start(self) -> Path:
        """파일을 만들고 헤더를 쓴 뒤 기록 스레드를 시작한다. 헤더는 즉시 flush되어 남는다."""
        started_at = datetime.now().astimezone()
        self._open_file(started_at)
        self._start_perf = time.perf_counter()
        header = {
            "type": "session",
            "format_version": FORMAT_VERSION,
            "started_at": started_at.isoformat(timespec="milliseconds"),
            "time_base": "seconds since logging start (time.perf_counter)",
            "metadata": self._metadata,
            # 이 로그가 어떤 옵션으로 만들어졌는지(예: face_landmarks = 얼굴 좌표 저장 여부)
            "options": self._options,
            "settings": settings_snapshot(),
            "runtime": {
                **self._runtime,
                "python": sys.version.split()[0],
                "platform": platform.platform(),
            },
            "landmark_names": list(LANDMARK_NAMES),
        }
        self._file.write(json.dumps(header, separators=(",", ":"), allow_nan=False) + "\n")
        self._file.flush()
        self._thread = threading.Thread(target=self._run, name="sequence-logger", daemon=True)
        self._thread.start()
        return self._path

    def log_frame(self, record: dict[str, Any]) -> bool:
        """프레임 기록을 큐에 넣는다. 가득 찼거나 기록이 중단된 상태면 버리고 False."""
        if self._closed:
            return False
        self._index += 1
        if self._error is not None:
            self._dropped += 1
            return False
        try:
            self._queue.put_nowait({"type": "frame", "i": self._index, **record})
        except queue.Full:
            self._dropped += 1
            return False
        return True

    def log_event(self, event: dict[str, Any]) -> bool:
        """직전 프레임에서 일어난 진단 이벤트를 큐에 넣는다. log_frame()과 같이 절대 블록되지 않고, 가득 차면 버린다.
        frame 번호 i는 마지막으로 넘긴 프레임의 번호다(그래서 log_frame 직후에 부른다)."""
        if self._closed or self._error is not None:
            self._events_dropped += 1
            return False
        try:
            self._queue.put_nowait({"type": "event", "i": self._index, **event})
        except queue.Full:
            self._events_dropped += 1
            return False
        return True

    def _run(self) -> None:
        last_flush = time.monotonic()
        try:
            while True:
                try:
                    item = self._queue.get(timeout=self._flush_interval)
                except queue.Empty:
                    item = None
                if item is _STOP:
                    break
                if item is not None:
                    try:
                        line = json.dumps(item, separators=(",", ":"), allow_nan=False)
                    except (TypeError, ValueError):
                        self._invalid += 1  # 직렬화할 수 없는 프레임 하나만 건너뛴다
                        continue
                    self._file.write(line + "\n")
                    if item.get("type") == "event":
                        self._events_written += 1
                    else:
                        self._written += 1
                if time.monotonic() - last_flush >= self._flush_interval:
                    self._file.flush()
                    last_flush = time.monotonic()
        except Exception as exc:  # 디스크 오류 등. 파이프라인에는 영향을 주지 않고 기록만 멈춘다.
            self._error = repr(exc)

    def close(self) -> None:
        """남은 기록을 쓰고 마지막 줄(end)을 남긴 뒤 파일을 닫는다. 여러 번 호출해도 안전하다."""
        if self._closed or self._thread is None:
            return
        self._closed = True
        if self._thread.is_alive():  # 오류로 이미 멈춘 스레드에는 종료 신호를 보내 기다릴 필요가 없다
            try:
                self._queue.put(_STOP, timeout=5.0)
            except queue.Full:
                pass
        self._thread.join(timeout=10.0)
        if self._thread.is_alive():
            return  # 기록 스레드가 멈추지 않으면 파일을 건드리지 않는다.
        try:
            end = {
                "type": "end",
                "ended_at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
                "frames_offered": self._index,
                "frames_written": self._written,
                "frames_dropped": self._dropped,
                "frames_invalid": self._invalid,
                "events_written": self._events_written,
                "events_dropped": self._events_dropped,
                "write_error": self._error,
            }
            self._file.write(json.dumps(end, separators=(",", ":"), allow_nan=False) + "\n")
            self._file.flush()
        except Exception as exc:  # noqa: BLE001 - 기록이 이미 실패한 경우에도 종료는 막지 않는다
            self._error = self._error or repr(exc)
        finally:
            try:
                self._file.close()
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------- 파이프라인 연결


class SequenceRecorder:
    """한 프레임의 기하 분석과 기록을 묶는다. 로깅 문제로 운동 파이프라인이 멈추지 않도록 예외는 삼킨다."""

    def __init__(
        self,
        logger: SequenceLogger,
        tracker: GeometryTracker,
        *,
        include_face_landmarks: bool = False,
    ) -> None:
        self.logger = logger
        self.tracker = tracker
        self.include_face_landmarks = include_face_landmarks
        self._error_reported = False

    def record(
        self,
        *,
        frame_size: tuple[int, int],
        primary_person: dict[str, Any] | None,
        smoothing_state: dict[str, Any],
        display_pose: str,
        display_confidence: float,
        capture_time: float,
        logic_time: float,
        geometry: tuple[TrackedFrame | None, LockState] | None = None,
        rep: dict[str, Any] | None = None,
    ) -> None:
        """capture_time은 프레임을 읽은 직후, logic_time은 운동 로직 실행 시각(둘 다 time.perf_counter()).

        rep은 ExerciseCounter.rep_diagnostics()의 값(RepTracker 상태, 안내 사유, 이벤트 목록)이다. 없으면 v1처럼 기록한다.

        geometry는 같은 프레임에 이미 계산한 (TrackedFrame 또는 None, LockState)다. RepTracker가 같은
        GeometryTracker를 쓸 때 프레임당 한 번만 갱신하도록 넘긴다. 없으면 이 기록기가 직접 계산한다.
        """
        try:
            self._record(
                frame_size,
                primary_person,
                smoothing_state,
                display_pose,
                display_confidence,
                capture_time,
                logic_time,
                geometry,
                rep,
            )
        except Exception as exc:  # noqa: BLE001 - 진단용 로깅이 운동 기록을 막으면 안 된다
            if not self._error_reported:
                self._error_reported = True
                print(f"[Sequence] Logging error ignored (workout continues): {exc!r}")

    def _record(
        self,
        frame_size: tuple[int, int],
        primary_person: dict[str, Any] | None,
        smoothing_state: dict[str, Any],
        display_pose: str,
        display_confidence: float,
        capture_time: float,
        logic_time: float,
        geometry: tuple[TrackedFrame | None, LockState] | None = None,
        rep: dict[str, Any] | None = None,
    ) -> None:
        raw_prediction = primary_person["prediction"] if primary_person is not None else None
        labels = build_labels(raw_prediction, smoothing_state, display_pose, display_confidence)
        times = {
            "t": self.logger.to_session_time(capture_time),
            "t_logic": self.logger.to_session_time(logic_time),
        }

        tracked = None
        if geometry is not None:
            tracked, lock = geometry
        elif primary_person is not None and primary_person["landmarks"] is not None:
            tracked = self.tracker.update(
                primary_person["landmarks"],
                crop_bbox=primary_person["padded_bbox"],
                person_bbox=primary_person["bbox"],
                frame_size=frame_size,
                world_landmarks=primary_person.get("world_landmarks"),
                timestamp=capture_time,
            )
            lock = tracked.lock
        else:
            lock = self.tracker.update_missing(capture_time)

        record = build_frame_record(
            **times,
            frame_size=frame_size,
            person_confidence=primary_person["person_confidence"] if primary_person else None,
            yolo_bbox=primary_person["bbox"] if primary_person else None,
            crop_bbox=primary_person["padded_bbox"] if primary_person else None,
            landmarks=primary_person["landmarks"] if primary_person else None,
            world_landmarks=primary_person.get("world_landmarks") if primary_person else None,
            tracked=tracked,
            lock=lock,
            labels=labels,
            include_face_landmarks=self.include_face_landmarks,
            rep=rep,
        )
        self.logger.log_frame(record)
        for event in self._events(lock, rep, times["t"]):
            self.logger.log_event(event)

    def _events(self, lock: LockState, rep: dict[str, Any] | None, session_time: float) -> list[dict[str, Any]]:
        """이 프레임에서 일어난 진단 이벤트: BodyLock 변화와 RepTracker 이벤트(시각을 세션 기준 초로 바꾼다)."""
        events: list[dict[str, Any]] = []
        if lock.event is not None:
            events.append(
                {
                    "kind": "lock", "event": lock.event, "t": _round(session_time), "leg": lock.leg,
                    "facing": lock.facing, "detail": lock.detail,
                }
            )
        for source in (rep or {}).get("events", ()):
            converted = dict(source)
            for key in EVENT_TIME_KEYS:
                if converted.get(key) is not None:
                    converted[key] = _round(self.logger.to_session_time(converted[key]))
            events.append(converted)
        return events

    def close(self) -> None:
        self.logger.close()
