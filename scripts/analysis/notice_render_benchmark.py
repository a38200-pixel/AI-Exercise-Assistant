"""안내 문구 렌더링 처리 시간 비교: 매 프레임 PIL로 그리던 이전 방식 vs 문구가 바뀔 때만 그리고 프레임마다 합성하는 현재 방식.

같은 합성 프레임(640x480 + HUD)에 안내를 켠 채 N프레임을 처리한 평균·p95·최대 시간을 비교하고, 두 방식의 출력이 같은지
(픽셀 최대 차이) 확인한다. 카메라를 쓰지 않는다.

실행(저장소 루트에서): python -m scripts.analysis.notice_render_benchmark [--frames 600]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import src.main as main_module  # noqa: E402
from src.main import INK, NOTICE_COLOR, NOTICE_TEXT, _korean_font, compose_workout_ui  # noqa: E402

NOTICE = "not_side"


def legacy_draw_notice_band(canvas: np.ndarray, notice: str, left: int, right: int, bottom: int) -> None:
    """이전 구현(매 프레임 PIL 변환·폰트 렌더링). 비교 기준으로만 남겨 둔다."""
    korean, english = NOTICE_TEXT[notice]
    band_height = 44
    top = bottom - band_height - 10
    region = canvas[top:top + band_height, left:right]
    region[:] = cv2.addWeighted(region, 0.25, np.full_like(region, INK), 0.75, 0)
    font = _korean_font()
    if font is not None:
        from PIL import Image, ImageDraw

        image = Image.fromarray(region[:, :, ::-1])  # BGR -> RGB
        draw = ImageDraw.Draw(image)
        width = draw.textlength(korean, font=font)
        draw.text(((region.shape[1] - width) / 2, 9), korean, font=font, fill=NOTICE_COLOR[::-1])
        region[:] = np.asarray(image)[:, :, ::-1]
        return
    scale = 0.62
    text_width = cv2.getTextSize(english, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)[0][0]
    main_module._put_ui_text(canvas, english, (left + (right - left - text_width) // 2, top + 30), scale, NOTICE_COLOR, 2)


def synthetic_frames(count: int) -> list[np.ndarray]:
    """배경이 프레임마다 달라지는 합성 영상(캐시가 영상 내용에 기대지 않는지도 같이 본다)."""
    rng = np.random.default_rng(0)
    return [rng.integers(40, 200, size=(480, 640, 3), dtype=np.uint8) for _ in range(count)]


def hud(frame: np.ndarray, notice: str | None) -> np.ndarray:
    status = {"mode": "squat", "squat_count": 3}
    session = {"status": "ACTIVE", "elapsed_seconds": 65}
    return compose_workout_ui(frame, status, session, "READY", "STAND", 0.9, True, notice)


def timed_hud(frames: list[np.ndarray]) -> dict[str, list[float]]:
    """프레임마다 세 가지(안내 없음 / 이전 / 현재)를 순서를 돌려 가며 재서 다른 프로세스의 부하 변동이 한쪽에만 쏠리지 않게 한다."""
    current_band = main_module._draw_notice_band
    samples: dict[str, list[float]] = {"none": [], "legacy": [], "current": []}
    try:
        for index, frame in enumerate(frames):
            order = ("none", "legacy", "current")
            for name in order[index % 3:] + order[:index % 3]:
                main_module._draw_notice_band = legacy_draw_notice_band if name == "legacy" else current_band
                start = time.perf_counter()
                hud(frame, None if name == "none" else NOTICE)
                samples[name].append((time.perf_counter() - start) * 1000.0)
    finally:
        main_module._draw_notice_band = current_band
    return samples


def timed_band(frames: list[np.ndarray]) -> dict[str, list[float]]:
    """안내 띠 그리기 함수만 잰다(HUD 나머지 제외). 캔버스 복사는 시간에 넣지 않는다."""
    height, width = frames[0].shape[:2]
    canvas_shape = (height + 64 + 0, width, 3)
    samples: dict[str, list[float]] = {"legacy": [], "current": []}
    for index, frame in enumerate(frames):
        base = np.zeros(canvas_shape, dtype=np.uint8)
        base[64:64 + height, :width] = frame
        for name, fn in (("legacy", legacy_draw_notice_band), ("current", main_module._draw_notice_band))[::1 if index % 2 == 0 else -1]:
            canvas = base.copy()
            start = time.perf_counter()
            fn(canvas, NOTICE, 12, width - 12, 64 + height)
            samples[name].append((time.perf_counter() - start) * 1000.0)
    return samples


def summary(name: str, samples: list[float]) -> str:
    ordered = sorted(samples)
    p95 = ordered[int(len(ordered) * 0.95)]
    return (
        f"{name:<30} 중앙값 {statistics.median(samples):6.3f} ms   평균 {statistics.mean(samples):6.3f} ms   "
        f"p95 {p95:6.3f} ms   최대 {max(samples):6.3f} ms"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=600)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    frames = synthetic_frames(args.frames)
    font = _korean_font()
    print(f"프레임 {args.frames}개(640x480 + HUD), 한글 폰트: {'있음' if font is not None else '없음(영어 대체)'}")

    hud(frames[0], NOTICE)  # 워밍업(폰트·캐시)
    band = timed_band(frames)
    whole = timed_hud(frames)

    current_band = main_module._draw_notice_band
    main_module._draw_notice_band = legacy_draw_notice_band
    try:
        legacy_frame = hud(frames[1], NOTICE)
    finally:
        main_module._draw_notice_band = current_band
    current_frame = hud(frames[1], NOTICE)

    print("[안내 띠 그리기만]")
    print(summary("이전 방식(매 프레임 PIL)", band["legacy"]))
    print(summary("현재 방식(캐시 레이어 합성)", band["current"]))
    print("[HUD 전체 합성(프레임당)]")
    print(summary("안내 없음(기준)", whole["none"]))
    print(summary("이전 방식(매 프레임 PIL)", whole["legacy"]))
    print(summary("현재 방식(캐시 레이어 합성)", whole["current"]))
    median_none = statistics.median(whole["none"])
    print(
        "안내로 늘어난 시간(중앙값 기준): "
        f"이전 {statistics.median(whole['legacy']) - median_none:.3f} ms -> 현재 {statistics.median(whole['current']) - median_none:.3f} ms"
    )
    diff = np.abs(legacy_frame.astype(int) - current_frame.astype(int))
    print(f"두 방식 출력의 픽셀 최대 차이: {int(diff.max())} (0~255), 달라진 픽셀 비율 {np.mean(np.any(diff > 0, axis=2)) * 100:.3f}%")
    print(f"캐시: {main_module._notice_text_layer.cache_info()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
