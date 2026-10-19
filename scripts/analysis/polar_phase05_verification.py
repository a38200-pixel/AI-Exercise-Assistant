"""Phase 0.5: 무릎각 시각 검증, 90~150° 구간 비율, stand crop 이탈 원인 확인.

polar_squat_angle_analysis.py(Phase 0)의 crop 복원과 각도 계산을 재사용한다.
원본 데이터와 FitRoute 모델 파일은 읽기 전용으로만 사용한다.

실행 예:
    python scripts/analysis/polar_phase05_verification.py --data-dir <POLAR data 폴더>
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polar_squat_angle_analysis as base  # noqa: E402


REPO_ROOT = base.REPO_ROOT
DEFAULT_OUT_DIR = base.DEFAULT_OUT_DIR
FITROUTE_MODEL_PATH = REPO_ROOT / "models" / "classifier" / "model_weights.xgb"
FITROUTE_CLASSES_PATH = REPO_ROOT / "models" / "classifier" / "classes.json"

JOINTS = ("hip", "knee", "ankle", "heel", "foot_index")
MIN_VISIBILITY = base.MIN_VISIBILITY
BORDER_TOLERANCE_PX = 1

# 0.5-1 시각 검증 구간: (이름, 클래스, 하한 포함, 상한 미포함)
OVERLAY_BINS = (
    ("squat_lt30", "squat", 0.0, 30.0),
    ("squat_30_70", "squat", 30.0, 70.0),
    ("squat_90_150", "squat", 90.0, 150.0),
    ("squat_gt150", "squat", 150.0, 180.01),
    ("stand_lt158", "stand", 0.0, 158.0),
)

# 0.5-2 XGBoost 예측 비교용 무릎각 구간
ANGLE_BINS = (0.0, 60.0, 90.0, 150.0, 165.0, 180.01)

TILE = 640
BAR = 72


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="POLAR 학습 데이터 루트. 기본값 없음.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cache", type=Path, default=None, help="crop 복원 결과 pickle 캐시(선택).")
    parser.add_argument("--per-bin", type=int, default=8, help="구간별 overlay 개수")
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


# ---------------------------------------------------------------- 기하 복원


def restore_geometry(df: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """원본 이미지 크기, YOLO bbox, padding된 crop 좌표를 복원한다 (학습 저장소와 동일한 식)."""
    names = ("img_w", "img_h", "bx1", "by1", "bx2", "by2", "px1", "py1", "px2", "py2")
    values = np.full((len(df), len(names)), np.nan)
    label_cache: dict[tuple[str, str], list[tuple[float, ...]]] = {}
    size_cache: dict[tuple[str, str], tuple[int, int]] = {}

    for position, (split, image_name, person_index) in enumerate(
        zip(df["split"], df["image_name"], df["person_index"])
    ):
        stem = Path(image_name).stem
        key = (split, stem)
        if key not in label_cache:
            boxes = []
            label_path = data_dir / "labels" / split / f"{stem}.txt"
            if label_path.is_file():
                for line in label_path.read_text(encoding="utf-8").splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        boxes.append(tuple(float(v) for v in parts[1:5]))
            label_cache[key] = boxes
            annotation_path = data_dir / "Annotations" / split / f"{stem}.json"
            if annotation_path.is_file():
                annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
                size_cache[key] = (int(annotation["width"]), int(annotation["height"]))
        boxes = label_cache[key]
        if key not in size_cache or person_index >= len(boxes):
            continue

        img_w, img_h = size_cache[key]
        cx, cy, bw, bh = boxes[person_index]
        x1 = int(round(cx * img_w - bw * img_w / 2.0))
        y1 = int(round(cy * img_h - bh * img_h / 2.0))
        x2 = int(round(cx * img_w + bw * img_w / 2.0))
        y2 = int(round(cy * img_h + bh * img_h / 2.0))
        pad_x = int(round((x2 - x1) * base.BBOX_PADDING))
        pad_y = int(round((y2 - y1) * base.BBOX_PADDING))
        values[position] = (
            img_w, img_h, x1, y1, x2, y2,
            max(0, x1 - pad_x), max(0, y1 - pad_y), min(img_w, x2 + pad_x), min(img_h, y2 + pad_y),
        )

    result = df.copy()
    for index, name in enumerate(names):
        result[name] = values[:, index]
    result["crop_w"] = result["px2"] - result["px1"]
    result["crop_h"] = result["py2"] - result["py1"]
    return result


def load_geometry(df: pd.DataFrame, data_dir: Path, cache: Path | None) -> pd.DataFrame:
    if cache is not None and cache.is_file():
        with cache.open("rb") as handle:
            cached = pickle.load(handle)
        if len(cached) == len(df) and (cached["sample_id"].to_numpy() == df["sample_id"].to_numpy()).all():
            print(f"geometry cache hit: {cache}")
            return cached
    result = restore_geometry(df, data_dir)
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("wb") as handle:
            pickle.dump(result, handle)
    return result


def check_against_phase0(df: pd.DataFrame, data_dir: Path) -> str:
    """Phase 0에서 extraction_summary와 일치가 검증된 복원 함수와 같은 결과인지 무작위 표본으로 확인."""
    sample = df.sample(min(2000, len(df)), random_state=1)
    reference = base.restore_crop_sizes(sample[["split", "image_name", "person_index"]], data_dir)
    same = bool(
        np.array_equal(reference["crop_w"].to_numpy(), sample["crop_w"].to_numpy())
        and np.array_equal(reference["crop_h"].to_numpy(), sample["crop_h"].to_numpy())
    )
    return f"Phase 0 복원 함수와 crop w,h 비교(무작위 {len(sample)}행): {'일치' if same else '불일치'}"


# ---------------------------------------------------------------- 각도 및 유효성


def near_value(df: pd.DataFrame, joint: str, suffix: str) -> np.ndarray:
    use_left = (df["near_leg"] == "left").to_numpy()
    return np.where(
        use_left,
        df[f"left_{joint}_{suffix}"].to_numpy(),
        df[f"right_{joint}_{suffix}"].to_numpy(),
    )


def angle_between(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    v1, v2 = a - b, c - b
    norm = np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.degrees(np.arccos(np.clip((v1 * v2).sum(axis=1) / norm, -1.0, 1.0)))


def angle_atan2(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """arccos 구현과 독립된 atan2 기반 계산 (버그 교차 검증용)."""
    v1, v2 = a - b, c - b
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    dot = (v1 * v2).sum(axis=1)
    return np.degrees(np.abs(np.arctan2(cross, dot)))


def near_points(df: pd.DataFrame, pixel: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scale_x = df["crop_w"].to_numpy() if pixel else 1.0
    scale_y = df["crop_h"].to_numpy() if pixel else 1.0
    result = []
    for joint in ("hip", "knee", "ankle"):
        x = near_value(df, joint, "x") * scale_x
        y = near_value(df, joint, "y") * scale_y
        result.append(np.stack([x, y], axis=1))
    return tuple(result)  # type: ignore[return-value]


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = base.compute_angles(df)

    hip, knee, ankle = near_points(out, pixel=False)
    out["knee_angle_raw"] = angle_between(hip, knee, ankle)  # 종횡비 보정 전 (정규화 좌표 그대로)

    inside = np.ones(len(out), dtype=bool)
    visible = np.ones(len(out), dtype=bool)
    for joint in JOINTS:
        x, y = near_value(out, joint, "x"), near_value(out, joint, "y")
        inside &= (x >= 0) & (x <= 1) & (y >= 0) & (y <= 1)
        visible &= near_value(out, joint, "visibility") >= MIN_VISIBILITY
    out["near_joints_inside"] = inside
    out["near_joints_visible"] = visible

    out["ankle_below_crop"] = near_value(out, "ankle", "y") > 1
    out["ankle_above_crop"] = near_value(out, "ankle", "y") < 0
    out["ankle_left_crop"] = near_value(out, "ankle", "x") < 0
    out["ankle_right_crop"] = near_value(out, "ankle", "x") > 1
    knee_x, knee_y = near_value(out, "knee", "x"), near_value(out, "knee", "y")
    ankle_x, ankle_y = near_value(out, "ankle", "x"), near_value(out, "ankle", "y")
    out["knee_or_ankle_outside"] = (
        (knee_x < 0) | (knee_x > 1) | (knee_y < 0) | (knee_y > 1)
        | (ankle_x < 0) | (ankle_x > 1) | (ankle_y < 0) | (ankle_y > 1)
    )

    tol = BORDER_TOLERANCE_PX
    out["bbox_touch_left"] = out["bx1"] <= tol
    out["bbox_touch_top"] = out["by1"] <= tol
    out["bbox_touch_right"] = out["bx2"] >= out["img_w"] - tol
    out["bbox_touch_bottom"] = out["by2"] >= out["img_h"] - tol
    out["bbox_touch_any"] = (
        out["bbox_touch_left"] | out["bbox_touch_top"] | out["bbox_touch_right"] | out["bbox_touch_bottom"]
    )
    out["padded_clamped_bottom"] = out["py2"] >= out["img_h"]
    out["padded_clamped_any"] = (
        (out["px1"] <= 0) | (out["py1"] <= 0) | (out["px2"] >= out["img_w"]) | (out["py2"] >= out["img_h"])
    )

    out["is_side"] = out["side_ratio"] <= base.SIDE_RATIO_PRIMARY
    out["valid_body"] = out["near_joints_inside"] & ~out["bbox_touch_any"] & out["near_joints_visible"]
    return out


# ---------------------------------------------------------------- 0.5-1 overlay


def render_overlay(row: pd.Series, data_dir: Path, tag: str) -> np.ndarray:
    image = cv2.imread(str(data_dir / "images" / row["split"] / row["image_name"]))
    height, width = image.shape[:2]
    margin = int(0.35 * max(width, height))
    canvas = cv2.copyMakeBorder(image, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=(70, 70, 70))

    # 사람이 있는 padded crop 주변(각 방향 +25%)만 확대해서 보여준다. 이미지 밖 외삽 landmark도 보이도록 여백 포함.
    zoom = 0.25
    win_x1 = max(0, int(row["px1"] + margin - zoom * row["crop_w"]))
    win_y1 = max(0, int(row["py1"] + margin - zoom * row["crop_h"]))
    win_x2 = min(canvas.shape[1], int(row["px2"] + margin + zoom * row["crop_w"]))
    win_y2 = min(canvas.shape[0], int(row["py2"] + margin + zoom * row["crop_h"]))
    thick = max(2, int(max(win_x2 - win_x1, win_y2 - win_y1) / 200))

    def point(name: str) -> tuple[int, int]:
        x = row["px1"] + row[f"{name}_x"] * row["crop_w"] + margin
        y = row["py1"] + row[f"{name}_y"] * row["crop_h"] + margin
        return int(round(x)), int(round(y))

    cv2.rectangle(canvas, (margin, margin), (margin + width - 1, margin + height - 1), (255, 255, 255), max(1, thick // 2))
    cv2.rectangle(
        canvas,
        (int(row["bx1"]) + margin, int(row["by1"]) + margin),
        (int(row["bx2"]) + margin, int(row["by2"]) + margin),
        (0, 255, 255),
        max(1, thick // 2),
    )
    cv2.rectangle(
        canvas,
        (int(row["px1"]) + margin, int(row["py1"]) + margin),
        (int(row["px2"]) + margin, int(row["py2"]) + margin),
        (255, 255, 0),
        max(1, thick // 2),
    )

    near, far = row["near_leg"], ("right" if row["near_leg"] == "left" else "left")
    for side, color, width_px in ((far, (0, 140, 255), max(1, thick // 2)), (near, (0, 255, 0), thick)):
        points = [point(f"{side}_{joint}") for joint in ("hip", "knee", "ankle")]
        cv2.polylines(canvas, [np.array(points, dtype=np.int32)], False, color, width_px, cv2.LINE_AA)
        for p in points:
            cv2.circle(canvas, p, thick + 2, color, -1, cv2.LINE_AA)
    for joint in ("heel", "foot_index"):
        cv2.circle(canvas, point(f"{near}_{joint}"), thick + 1, (255, 0, 255), -1, cv2.LINE_AA)
    for side in ("left", "right"):
        cv2.circle(canvas, point(f"{side}_shoulder"), thick + 1, (255, 100, 0), -1, cv2.LINE_AA)
    cv2.line(canvas, point(f"{near}_shoulder"), point(f"{near}_hip"), (255, 100, 0), max(1, thick // 2), cv2.LINE_AA)

    canvas = canvas[win_y1:win_y2, win_x1:win_x2]
    scale = TILE / max(canvas.shape[:2])
    resized = cv2.resize(canvas, (int(canvas.shape[1] * scale), int(canvas.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    tile = np.zeros((TILE + BAR, TILE, 3), dtype=np.uint8)
    y0, x0 = (TILE - resized.shape[0]) // 2, (TILE - resized.shape[1]) // 2
    tile[y0:y0 + resized.shape[0], x0:x0 + resized.shape[1]] = resized

    inside = "".join("Y" if v else "n" for v in (
        row["near_joints_inside"], not row["bbox_touch_any"], row["near_joints_visible"]
    ))
    lines = (
        f"{tag} | {row['label']} | {row['image_name']}",
        f"near={near} knee corrected={row['knee_angle']:.0f} raw={row['knee_angle_raw']:.0f} ratio={row['side_ratio']:.2f}",
        f"vis h/k/a={row['_vh']:.2f}/{row['_vk']:.2f}/{row['_va']:.2f} inside/free/vis={inside}",
    )
    for index, text in enumerate(lines):
        cv2.putText(tile, text, (6, TILE + 20 + index * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return tile


def build_overlays(df: pd.DataFrame, data_dir: Path, out_dir: Path, per_bin: int, seed: int) -> tuple[pd.DataFrame, list[str]]:
    overlay_dir = out_dir / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    df = df.copy()
    df["_vh"] = near_value(df, "hip", "visibility")
    df["_vk"] = near_value(df, "knee", "visibility")
    df["_va"] = near_value(df, "ankle", "visibility")

    selected = []
    for name, label, low, high in OVERLAY_BINS:
        pool = df[(df["label"] == label) & df["is_side"] & (df["knee_angle"] >= low) & (df["knee_angle"] < high)]
        count = min(per_bin, len(pool))
        chosen = pool.iloc[rng.choice(len(pool), size=count, replace=False)].sort_values("knee_angle")
        tiles = []
        for index, (_, row) in enumerate(chosen.iterrows(), start=1):
            tile = render_overlay(row, data_dir, name)
            cv2.imwrite(str(overlay_dir / f"{name}_{index:02d}_{Path(row['image_name']).stem}.jpg"), tile, [cv2.IMWRITE_JPEG_QUALITY, 88])
            tiles.append(tile)
            selected.append(
                {
                    "bin": name, "order": index, "sample_id": row["sample_id"], "label": row["label"],
                    "near_leg": row["near_leg"], "knee_corrected": round(float(row["knee_angle"]), 1),
                    "knee_raw": round(float(row["knee_angle_raw"]), 1), "side_ratio": round(float(row["side_ratio"]), 3),
                    "near_joints_inside": bool(row["near_joints_inside"]), "bbox_touch_any": bool(row["bbox_touch_any"]),
                    "vis_hip": round(float(row["_vh"]), 2), "vis_knee": round(float(row["_vk"]), 2), "vis_ankle": round(float(row["_va"]), 2),
                }
            )
        columns = 3
        rows = int(np.ceil(len(tiles) / columns))
        sheet = np.zeros((rows * (TILE + BAR), columns * TILE, 3), dtype=np.uint8)
        for index, tile in enumerate(tiles):
            r, c = divmod(index, columns)
            sheet[r * (TILE + BAR):(r + 1) * (TILE + BAR), c * TILE:(c + 1) * TILE] = tile
        cv2.imwrite(str(overlay_dir / f"sheet_{name}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])

    selected_df = pd.DataFrame(selected)
    selected_df.to_csv(out_dir / "overlay_samples.csv", index=False, encoding="utf-8")

    # 교차 검증: arccos 구현과 atan2 구현, 보정 전/후 차이
    chosen_ids = set(selected_df["sample_id"])
    subset = df[df["sample_id"].isin(chosen_ids)]
    hip, knee, ankle = near_points(subset, pixel=True)
    diff = np.abs(angle_atan2(hip, knee, ankle) - subset["knee_angle"].to_numpy())
    notes = [f"overlay {len(subset)}개: arccos 구현과 atan2 독립 구현의 최대 차이 {diff.max():.6f}°"]

    side = df[df["is_side"]]
    for label in ("squat", "stand"):
        sel = side[side["label"] == label]
        delta = (sel["knee_angle"] - sel["knee_angle_raw"]).abs()
        notes.append(
            f"측면 {label} {len(sel)}개: |보정 후 − 보정 전| 중앙값 {delta.median():.2f}°, p95 {delta.quantile(0.95):.2f}°, 최대 {delta.max():.2f}°"
        )
        notes.append(
            f"측면 {label} 무릎각 중앙값: 보정 후 {sel['knee_angle'].median():.1f}° / 보정 전 {sel['knee_angle_raw'].median():.1f}°, "
            f"p5: {sel['knee_angle'].quantile(0.05):.1f}° / {sel['knee_angle_raw'].quantile(0.05):.1f}°"
        )
    return selected_df, notes


# ---------------------------------------------------------------- 0.5-2


def bin_label(low: float, high: float) -> str:
    return f"{low:.0f}~{min(high, 180):.0f}"


def share_table(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    counts = pd.crosstab(frame["angle_bin"], frame[column])
    shares = (counts.div(counts.sum(axis=1), axis=0) * 100).round(1)
    shares.insert(0, "n", counts.sum(axis=1))
    return shares.reset_index()


def half_squat_section(df: pd.DataFrame, model_predictions: pd.Series) -> list[str]:
    lines = ["## 0.5-2. 90~150° 구간 비율", ""]
    lines.append("구간은 90 ≤ 무릎각 < 150. 범위: 측면 / 측면+전신유효(관절 crop 안, bbox 경계 미접촉, visibility≥0.5) / 전체.")
    lines.append("")
    rows = []
    for label in ("squat", "stand"):
        for scope_name, mask in (
            ("측면", df["is_side"]),
            ("측면+전신유효", df["is_side"] & df["valid_body"]),
            ("전체", pd.Series(True, index=df.index)),
        ):
            sel = df[(df["label"] == label) & mask]["knee_angle"]
            mid = (sel >= 90) & (sel < 150)
            rows.append(
                {
                    "class": label, "scope": scope_name, "n": len(sel),
                    "<90": f"{(sel < 90).mean() * 100:.1f}%",
                    "90~150": f"{mid.mean() * 100:.1f}% ({int(mid.sum())})",
                    ">=150": f"{(sel >= 150).mean() * 100:.1f}%",
                }
            )
    lines.append(base.markdown_table(pd.DataFrame(rows)))

    frame = df[df["is_side"]].copy()
    frame["pred"] = model_predictions.loc[frame.index]
    frame["angle_bin"] = pd.cut(
        frame["knee_angle"], bins=list(ANGLE_BINS), right=False,
        labels=[bin_label(a, b) for a, b in zip(ANGLE_BINS[:-1], ANGLE_BINS[1:])],
    )
    lines += ["", "### XGBoost(FitRoute `model_weights.xgb`, 학습 저장소 모델과 SHA-256 동일) 예측과 무릎각 구간", ""]
    lines.append("측면 필터를 통과한 모든 클래스 샘플 기준, 구간별 행 합계 100%. train split 샘플은 모델이 학습에 사용했을 수 있어 **test split**을 우선 본다.")
    for scope_name, scoped in (("test split만", frame[frame["split"] == "test"]), ("전체 split", frame)):
        lines += ["", f"#### {scope_name}", "", "(A) 정답 라벨 구성 (%)", ""]
        lines.append(base.markdown_table(share_table(scoped, "label")))
        lines += ["", "(B) XGBoost 예측 라벨 구성 (%, 모든 정답 라벨)", ""]
        lines.append(base.markdown_table(share_table(scoped, "pred")))
        squat_only = scoped[scoped["label"] == "squat"]
        lines += ["", "(C) 정답이 squat인 샘플의 XGBoost 예측 구성 (%)", ""]
        lines.append(base.markdown_table(share_table(squat_only, "pred")))
    return lines


def predict_all(df: pd.DataFrame) -> pd.Series:
    from xgboost import XGBClassifier

    feature_columns = list(df.columns[len(base.META_COLUMNS):len(base.META_COLUMNS) + 132])
    classes = json.loads(FITROUTE_CLASSES_PATH.read_text(encoding="utf-8"))
    model = XGBClassifier()
    model.load_model(str(FITROUTE_MODEL_PATH))
    booster_names = model.get_booster().feature_names
    if booster_names is not None and list(booster_names) != feature_columns:
        sys.exit("ERROR: dataset feature columns do not match the model feature names.")
    probabilities = model.predict_proba(df[feature_columns].to_numpy(dtype=np.float32))
    class_ids = np.asarray(model.classes_)[probabilities.argmax(axis=1)].astype(int)
    return pd.Series([classes[i] for i in class_ids], index=df.index, name="pred")


# ---------------------------------------------------------------- 0.5-3


def exit_section(df: pd.DataFrame) -> list[str]:
    lines = ["## 0.5-3. crop 이탈 원인 (near leg 기준)", ""]
    lines.append("이탈 = 가까운 쪽 다리의 knee 또는 ankle이 crop(0~1) 밖. bbox 접촉 = 원본 YOLO bbox가 이미지 경계에 ±1px 이내. "
                 "padded 클램프 = +30% 확장 bbox가 이미지 경계에서 잘림.")
    lines.append("")

    rows = []
    for label in ("stand", "squat"):
        for group_name, mask in (("이탈", df["knee_or_ankle_outside"]), ("이탈 아님", ~df["knee_or_ankle_outside"])):
            sel = df[(df["label"] == label) & mask]
            n = len(sel)

            def pct(column: str) -> str:
                return f"{sel[column].mean() * 100:.1f}%" if n else "-"

            rows.append(
                {
                    "class": label, "group": group_name, "n": n,
                    "bbox 하단 접촉": pct("bbox_touch_bottom"), "bbox 어느 경계든 접촉": pct("bbox_touch_any"),
                    "padded 하단 클램프": pct("padded_clamped_bottom"), "padded 어느 경계든 클램프": pct("padded_clamped_any"),
                    "ankle이 crop 아래": pct("ankle_below_crop"), "ankle이 crop 위": pct("ankle_above_crop"),
                    "ankle이 crop 좌": pct("ankle_left_crop"), "ankle이 crop 우": pct("ankle_right_crop"),
                }
            )
    lines.append(base.markdown_table(pd.DataFrame(rows)))

    lines += ["", "### near leg visibility 분포 (p5/p25/p50/p75/p95)", ""]
    vis_rows = []
    for label in ("stand", "squat"):
        for group_name, mask in (("이탈", df["knee_or_ankle_outside"]), ("이탈 아님", ~df["knee_or_ankle_outside"])):
            sel = df[(df["label"] == label) & mask]
            for joint in ("knee", "ankle"):
                values = pd.Series(near_value(sel, joint, "visibility"))
                vis_rows.append(
                    {
                        "class": label, "group": group_name, "joint": joint, "n": len(sel),
                        **{f"p{p}": float(np.percentile(values, p)) if len(values) else np.nan for p in base.PERCENTILES},
                    }
                )
    lines.append(base.markdown_table(pd.DataFrame(vis_rows), 2))

    lines += ["", "### 이탈 샘플 제외 후 무릎각 분포 (재계산)", ""]
    lines.append("- `전신유효` = near leg의 hip/knee/ankle/heel/foot_index가 모두 crop 안 + bbox가 이미지 경계에 닿지 않음 + 해당 관절 visibility ≥ 0.5")
    lines.append("")
    subsets = (
        ("전체", pd.Series(True, index=df.index)),
        ("crop 안(이탈 제외)", ~df["knee_or_ankle_outside"]),
        ("측면", df["is_side"]),
        ("측면 + crop 안", df["is_side"] & ~df["knee_or_ankle_outside"]),
        ("측면 + 전신유효", df["is_side"] & df["valid_body"]),
        ("전신유효", df["valid_body"]),
    )
    rows = []
    for label in ("stand", "squat"):
        total = int((df["label"] == label).sum())
        for name, mask in subsets:
            row = {"class": label, "subset": name}
            row.update(base.percentile_row(df.loc[(df["label"] == label) & mask, "knee_angle"]))
            row["retained"] = f"{row['n'] / total * 100:.1f}%"
            rows.append(row)
    lines.append(base.markdown_table(pd.DataFrame(rows)))
    return lines


def main() -> int:
    arguments = parse_arguments()
    data_dir: Path = arguments.data_dir
    if not data_dir.is_dir():
        sys.exit(f"ERROR: --data-dir is not a directory: {data_dir}")
    out_dir: Path = arguments.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = base.find_single(data_dir, "dataset.csv")
    dataset = pd.read_csv(dataset_path)
    dataset = load_geometry(dataset, data_dir, arguments.cache)
    if dataset["crop_w"].isna().any():
        sys.exit("ERROR: some rows could not be restored.")
    consistency = check_against_phase0(dataset, data_dir)
    dataset = add_derived_columns(dataset)

    report = ["# Phase 0.5 검증 결과", "", f"- 데이터 경로(이 PC 기준): `{data_dir}`", f"- {consistency}", ""]

    print("overlays...")
    selected, notes = build_overlays(dataset, data_dir, out_dir, arguments.per_bin, arguments.seed)
    report += ["## 0.5-1. 무릎각 시각 검증", ""]
    report.append(f"- 선택: 측면 필터(비율 ≤ {base.SIDE_RATIO_PRIMARY}) 통과 샘플에서 구간별 {arguments.per_bin}개 무작위(seed {arguments.seed}), 무릎각 오름차순")
    report.append("- 표시: 흰 사각형=원본 이미지, 회색 여백=이미지 밖, 노랑=YOLO bbox, 하늘=+30% crop, 초록 굵은선=사용한 다리(hip-knee-ankle), 주황 얇은선=반대쪽 다리, 보라 점=heel/foot_index, 파랑=어깨-엉덩이")
    report.append("- 하단 문구: corrected=종횡비 보정(픽셀 좌표) 각도, raw=정규화 좌표 그대로 계산한 각도, inside/free/vis = (관절 crop 안 / bbox 경계 미접촉 / visibility 충족) Y 또는 n")
    report += [f"- {note}" for note in notes]
    report += ["", "contact sheet: `overlays/sheet_<bin>.jpg`, 개별 이미지: `overlays/<bin>_NN_*.jpg`, 목록: `overlay_samples.csv`", ""]
    for name, *_ in OVERLAY_BINS:
        report.append(f"![{name}](overlays/sheet_{name}.jpg)")
        report.append("")

    print("xgboost...")
    predictions = predict_all(dataset)
    report += half_squat_section(dataset, predictions)
    report.append("")
    report += exit_section(dataset)

    path = out_dir / "phase05_report.md"
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Report written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
