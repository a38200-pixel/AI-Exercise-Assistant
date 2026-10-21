"""반복 결과를 화면에 보일 한 줄(자세 점수, 얕음 안내, 점수 범위 안내)로 바꾸고 표시 시간을 관리한다. 화면 그리기는 main.py가 한다.

규칙(v0.2.0 Phase 3):
- 확정된 반복: "N점 · [worst_item 피드백]" 한 줄과 작은 회색 "깊이·상체" 표기. 감점이 없으면 "N점"만. 점수를 계산할 수 없으면 아무것도 보이지 않는다.
- 처음 잠금이 걸려 서 있을 때(세션당 한 번): "자세 점수는 깊이와 상체 정렬만 봅니다".
- 탈락한 후보의 사유가 **엉덩이 하강 부족뿐**이면: "더 깊게 앉아야 1회로 셉니다". 다른 탈락 사유(짧음, 양발 벌어짐, 다른 운동 등)는 화면에 보이지 않고 기록만 한다.
  (걷기 같은 이동 구간의 굽힘은 짧음·ML 사유가 함께 붙으므로 '뿐'일 때만 보여, 걷다가 얕다는 안내가 뜨지 않게 한다.)
- RepTracker를 쓰지 않거나(USE_REP_TRACKER=False) squat 모드가 아니면 아무것도 보이지 않는다.
표시 시간은 config/settings.py의 REP_SCORE_DISPLAY_SECONDS, REP_SHALLOW_HINT_DISPLAY_SECONDS, POSTURE_SCORE_INTRO_DISPLAY_SECONDS다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import (
    POSTURE_SCORE_INTRO_DISPLAY_SECONDS,
    REP_SCORE_DISPLAY_SECONDS,
    REP_SHALLOW_HINT_DISPLAY_SECONDS,
)
from src.exercise_counter import SQUAT_MODE
from src.posture_score import FEEDBACK_TEXT, ITEM_DEPTH, ITEM_TORSO_SHIN, feedback_line
from src.rep_tracker import REASON_SHALLOW_HIP_DROP

KIND_SCORE = "score"
KIND_SHALLOW = "shallow"
KIND_INTRO = "intro"

SCORE_TAG = ("깊이·상체", "DEPTH+TORSO")
SHALLOW_TEXT = ("더 깊게 앉아야 1회로 셉니다", "SQUAT DEEPER TO COUNT")
INTRO_TEXT = ("자세 점수는 깊이와 상체 정렬만 봅니다", "POSTURE SCORE: DEPTH + TORSO ONLY")
# 한글 폰트를 쓸 수 없을 때의 영어 문구(worst_item별)
FEEDBACK_ENGLISH = {ITEM_DEPTH: "SQUAT DEEPER", ITEM_TORSO_SHIN: "KEEP YOUR CHEST UP"}
assert set(FEEDBACK_ENGLISH) == set(FEEDBACK_TEXT)


@dataclass(frozen=True)
class FeedbackLine:
    """화면 아래 띠에 보일 한 줄. tag_*는 오른쪽에 작은 회색으로 따로 그린다."""

    kind: str
    korean: str
    english: str
    tag_korean: str | None = None
    tag_english: str | None = None


class RepFeedback:
    def __init__(self) -> None:
        self._seen: Any = None
        self._line: FeedbackLine | None = None
        self._expires = 0.0
        self._intro_shown = False

    def reset(self) -> None:
        """새 운동 세션이 시작되면 부른다: 표시 중인 문구를 지우고 점수 범위 안내를 다시 한 번 보이게 한다."""
        self._seen = None
        self._line = None
        self._expires = 0.0
        self._intro_shown = False

    def update(self, status: dict[str, Any], now: float) -> FeedbackLine | None:
        """프레임마다 ExerciseCounter.get_status()와 현재 시각(초)을 넣고, 지금 보일 한 줄(없으면 None)을 돌려받는다."""
        if status.get("mode") != SQUAT_MODE or status.get("rep_guidance") is None:
            self._line = None
            return None

        last = status.get("last_rep")
        if last is not self._seen:
            self._seen = last
            if last is not None:
                self._on_rep(last, now)
        if self._line is None and not self._intro_shown and status["rep_guidance"] in ("ready", "in_rep"):
            self._intro_shown = True
            self._show(FeedbackLine(KIND_INTRO, *INTRO_TEXT), now, POSTURE_SCORE_INTRO_DISPLAY_SECONDS)

        if self._line is not None and now >= self._expires:
            self._line = None
        return self._line

    # ------------------------------------------------------------

    def _show(self, line: FeedbackLine, now: float, seconds: float) -> None:
        self._line = line
        self._expires = now + seconds

    def _on_rep(self, result: Any, now: float) -> None:
        self._intro_shown = True  # 이미 반복이 끝났으면 점수 범위 안내는 건너뛴다(처음 잠금 때 못 봤더라도 반복 결과 줄이 보인다)
        if result.counted:
            posture = result.posture
            text = feedback_line(posture) if posture is not None else None
            if text is None:
                return
            english = f"{round(posture.total_score)} PTS"
            if posture.worst_item is not None:
                english += f" - {FEEDBACK_ENGLISH[posture.worst_item]}"
            self._show(FeedbackLine(KIND_SCORE, text, english, *SCORE_TAG), now, REP_SCORE_DISPLAY_SECONDS)
        elif tuple(result.reasons) == (REASON_SHALLOW_HIP_DROP,):
            self._show(FeedbackLine(KIND_SHALLOW, *SHALLOW_TEXT), now, REP_SHALLOW_HINT_DISPLAY_SECONDS)
