"""POLAR MediaPipe 학습 데이터의 stand/squat 무릎각 분포와 실패 샘플을 분석한다.

원본 데이터는 읽기 전용으로만 사용하고 FitRoute 저장소로 복사하지 않는다.
결과물(보고서, 표, 히스토그램)만 --out-dir에 저장한다.

실행 예:
    python scripts/analysis/polar_squat_angle_analysis.py --data-dir <POLAR data 폴더>
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "versions" / "v0.2.0" / "analysis"

# 학습 저장소 02_extract_mediapipe_landmarks.py의 crop 설정과 동일해야 한다.
BBOX_PADDING = 0.30

PERCENTILES = (5, 25, 50, 75, 95)
SIDE_RATIO_THRESHOLDS = (0.25, 0.35, 0.50)
# 초기값(임시). 분포를 보고 Phase 1 전에 재검토한다.
SIDE_RATIO_PRIMARY = 0.35
MIN_VISIBILITY = 0.5
HIST_BIN_DEGREES = 5

META_COLUMNS = ("sample_id", "image_name", "person_index", "split", "class_id", "label")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="POLAR 학습 데이터 루트 (Annotations/, labels/, processed/ 포함). 기본값 없음.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"결과물 저장 위치 (기본: {DEFAULT_OUT_DIR})",
    )
    return parser.parse_args(argv)


def find_single(data_dir: Path, name: str) -> Path:
    matches = sorted(data_dir.rglob(name))
    if not matches:
        sys.exit(f"ERROR: '{name}' not found under --data-dir: {data_dir}")
    if len(matches) > 1:
        print(f"WARNING: multiple '{name}' found; using the first: {matches[0]}")
    return matches[0]


def describe_file(path: Path, rows: int | None) -> dict:
    stat = path.stat()
    return {
        "path": str(path),
        "rows": rows,
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------- crop 복원


def restore_crop_sizes(df: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    """YOLO label + 이미지 크기로 padding된 crop의 픽셀 w, h를 복원한다."""
    label_cache: dict[tuple[str, str], list[tuple[float, float, float, float]]] = {}
    size_cache: dict[tuple[str, str], tuple[int, int]] = {}

    widths = np.full(len(df), np.nan)
    heights = np.full(len(df), np.nan)

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
                    if len(parts) < 5:
                        continue
                    boxes.append(tuple(float(value) for value in parts[1:5]))
            label_cache[key] = boxes

            annotation_path = data_dir / "Annotations" / split / f"{stem}.json"
            if annotation_path.is_file():
                annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
                size_cache[key] = (int(annotation["width"]), int(annotation["height"]))

        boxes = label_cache[key]
        if key not in size_cache or person_index >= len(boxes):
            continue

        image_width, image_height = size_cache[key]
        center_x, center_y, box_w, box_h = boxes[person_index]
        # 학습 저장소와 동일: round-half-even 후 int
        x1 = int(round(center_x * image_width - box_w * image_width / 2.0))
        y1 = int(round(center_y * image_height - box_h * image_height / 2.0))
        x2 = int(round(center_x * image_width + box_w * image_width / 2.0))
        y2 = int(round(center_y * image_height + box_h * image_height / 2.0))

        pad_x = int(round((x2 - x1) * BBOX_PADDING))
        pad_y = int(round((y2 - y1) * BBOX_PADDING))
        crop_x1 = max(0, x1 - pad_x)
        crop_y1 = max(0, y1 - pad_y)
        crop_x2 = min(image_width, x2 + pad_x)
        crop_y2 = min(image_height, y2 + pad_y)

        widths[position] = crop_x2 - crop_x1
        heights[position] = crop_y2 - crop_y1

    result = df.copy()
    result["crop_w"] = widths
    result["crop_h"] = heights
    return result


def crop_checksum(df: pd.DataFrame, summary: dict) -> list[str]:
    """복원한 crop 통계를 학습 시점의 extraction_summary.json과 대조한다."""
    expected = summary.get("crop_statistics", {})
    lines = []
    for axis, column in (("width", "crop_w"), ("height", "crop_h")):
        values = df[column].dropna()
        got = {
            "min": float(values.min()),
            "mean": float(values.mean()),
            "max": float(values.max()),
        }
        for stat in ("min", "mean", "max"):
            want = float(expected[f"{axis}_{stat}"])
            ok = abs(got[stat] - want) < 1e-6 * max(1.0, abs(want))
            lines.append(
                f"{axis}_{stat}: restored={got[stat]:.6f} summary={want:.6f} "
                f"{'MATCH' if ok else 'MISMATCH'}"
            )
    lines.append(f"restored rows: {int(df['crop_w'].notna().sum())} / {len(df)}")
    return lines


# ---------------------------------------------------------------- 각도 계산


def compute_angles(df: pd.DataFrame) -> pd.DataFrame:
    """픽셀 비율 보정 후 가까운 쪽 다리의 무릎각과 측면 비율을 계산한다."""
    w = df["crop_w"].to_numpy()
    h = df["crop_h"].to_numpy()

    def point(name: str) -> np.ndarray:
        return np.stack([df[f"{name}_x"].to_numpy() * w, df[f"{name}_y"].to_numpy() * h], axis=1)

    def vis(name: str) -> np.ndarray:
        return df[f"{name}_visibility"].to_numpy()

    def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
        """b에서의 a-b-c 사이각(도)."""
        v1, v2 = a - b, c - b
        norm = np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            cosine = np.clip((v1 * v2).sum(axis=1) / norm, -1.0, 1.0)
        return np.degrees(np.arccos(cosine))

    left_vis_sum = vis("left_hip") + vis("left_knee") + vis("left_ankle")
    right_vis_sum = vis("right_hip") + vis("right_knee") + vis("right_ankle")
    use_left = left_vis_sum >= right_vis_sum

    knee_left = angle(point("left_hip"), point("left_knee"), point("left_ankle"))
    knee_right = angle(point("right_hip"), point("right_knee"), point("right_ankle"))

    near_min_vis = np.where(
        use_left,
        np.minimum.reduce([vis("left_hip"), vis("left_knee"), vis("left_ankle")]),
        np.minimum.reduce([vis("right_hip"), vis("right_knee"), vis("right_ankle")]),
    )

    shoulder_l, shoulder_r = point("left_shoulder"), point("right_shoulder")
    hip_l, hip_r = point("left_hip"), point("right_hip")
    torso_length = np.linalg.norm((shoulder_l + shoulder_r) / 2 - (hip_l + hip_r) / 2, axis=1)
    shoulder_dx = np.abs(shoulder_l[:, 0] - shoulder_r[:, 0])
    with np.errstate(invalid="ignore", divide="ignore"):
        side_ratio = np.where(torso_length > 0, shoulder_dx / torso_length, np.nan)

    torso_min_vis = np.minimum.reduce(
        [vis("left_shoulder"), vis("right_shoulder"), vis("left_hip"), vis("right_hip")]
    )

    out = df.copy()
    out["near_leg"] = np.where(use_left, "left", "right")
    out["knee_angle"] = np.where(use_left, knee_left, knee_right)
    out["side_ratio"] = side_ratio
    out["near_leg_min_vis"] = near_min_vis
    out["torso_min_vis"] = torso_min_vis
    return out


# ---------------------------------------------------------------- 통계/그림


def percentile_row(values: pd.Series) -> dict:
    clean = values.dropna()
    row = {"n": int(len(clean))}
    for percentile in PERCENTILES:
        row[f"p{percentile}"] = float(np.percentile(clean, percentile)) if len(clean) else np.nan
    return row


def subset_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    side = df["side_ratio"] <= SIDE_RATIO_PRIMARY
    visible = (df["near_leg_min_vis"] >= MIN_VISIBILITY) & (df["torso_min_vis"] >= MIN_VISIBILITY)
    return {
        "all": pd.Series(True, index=df.index),
        f"side(ratio<={SIDE_RATIO_PRIMARY})": side,
        f"side+vis>={MIN_VISIBILITY}": side & visible,
    }


def build_angle_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in ("stand", "squat"):
        in_class = df["label"] == label
        for subset_name, mask in subset_masks(df).items():
            row = {"class": label, "subset": subset_name}
            row.update(percentile_row(df.loc[in_class & mask, "knee_angle"]))
            rows.append(row)
    return pd.DataFrame(rows)


def save_histogram(df: pd.DataFrame, out_path: Path) -> None:
    bins = np.arange(0, 180 + HIST_BIN_DEGREES, HIST_BIN_DEGREES)
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.5))
    for axis, (title, mask) in zip(axes, subset_masks(df).items()):
        for label, color in (("stand", "#2a9d8f"), ("squat", "#e76f51")):
            values = df.loc[(df["label"] == label) & mask, "knee_angle"].dropna()
            axis.hist(
                values,
                bins=bins,
                alpha=0.6,
                color=color,
                density=True,
                label=f"{label} (n={len(values)})",
            )
        for threshold in (150, 160):
            axis.axvline(threshold, color="gray", linestyle="--", linewidth=0.8)
        axis.set_title(title, fontsize=10)
        axis.set_xlabel("Knee angle (deg), near leg")
        axis.set_ylabel("Density")
        axis.legend()
    fig.suptitle("POLAR knee angle distribution (dashed: 150 / 160 deg)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def save_side_ratio_histogram(df: pd.DataFrame, out_path: Path) -> None:
    bins = np.linspace(0, 2.0, 81)
    fig, axis = plt.subplots(figsize=(8, 4.5))
    for label, color in (("stand", "#2a9d8f"), ("squat", "#e76f51")):
        values = df.loc[df["label"] == label, "side_ratio"].dropna()
        axis.hist(
            values.clip(upper=2.0),
            bins=bins,
            alpha=0.6,
            color=color,
            density=True,
            label=f"{label} (n={len(values)})",
        )
    for threshold in SIDE_RATIO_THRESHOLDS:
        axis.axvline(threshold, color="gray", linestyle="--", linewidth=0.8)
    axis.set_xlabel("Shoulder x-gap / torso length (pixel-corrected, clipped at 2.0)")
    axis.set_ylabel("Density")
    axis.set_title("Side-view ratio (dashed: 0.25 / 0.35 / 0.50)")
    axis.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def side_threshold_counts(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in ("stand", "squat"):
        subset = df[df["label"] == label]
        row = {"class": label, "total": len(subset), "ratio_nan": int(subset["side_ratio"].isna().sum())}
        for threshold in SIDE_RATIO_THRESHOLDS:
            row[f"ratio<={threshold}"] = int((subset["side_ratio"] <= threshold).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def outside_unit_square_rate(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in ("stand", "squat"):
        subset = df[df["label"] == label]
        row = {"class": label, "n": len(subset)}
        for name in ("left_hip", "left_knee", "left_ankle", "right_hip", "right_knee", "right_ankle"):
            outside = (
                (subset[f"{name}_x"] < 0)
                | (subset[f"{name}_x"] > 1)
                | (subset[f"{name}_y"] < 0)
                | (subset[f"{name}_y"] > 1)
            )
            row[name] = f"{outside.mean() * 100:.1f}%"
        rows.append(row)
    return pd.DataFrame(rows)


def failed_analysis(
    dataset: pd.DataFrame, failed: pd.DataFrame, data_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    success_counts = dataset["label"].value_counts()
    failed_counts = failed["label"].value_counts()
    classes = sorted(set(success_counts.index) | set(failed_counts.index))
    rows = []
    total_failed = int(failed_counts.sum())
    total_all = int(success_counts.sum() + failed_counts.sum())
    for label in classes:
        ok = int(success_counts.get(label, 0))
        bad = int(failed_counts.get(label, 0))
        rows.append(
            {
                "class": label,
                "success": ok,
                "failed": bad,
                "total": ok + bad,
                "fail_rate_%": round(bad / (ok + bad) * 100, 2),
                "share_of_failures_%": round(bad / total_failed * 100, 2),
                "share_of_all_samples_%": round((ok + bad) / total_all * 100, 2),
            }
        )
    per_class = pd.DataFrame(rows).sort_values("fail_rate_%", ascending=False)

    by_split = (
        failed.groupby(["label", "split"]).size().unstack(fill_value=0).reset_index()
        if len(failed)
        else pd.DataFrame()
    )

    # 실패한 crop이 작거나 극단적인지 확인한다. (failed는 crop 크기가 이미 복원된 상태)
    failed_sized = failed
    size_rows = []
    for label in ("squat", "stand", "bendover", "lying"):
        for name, frame in (("success", dataset), ("failed", failed_sized)):
            subset = frame[frame["label"] == label]
            size_rows.append(
                {
                    "class": label,
                    "group": name,
                    "n": len(subset),
                    "crop_w_median": float(subset["crop_w"].median()),
                    "crop_h_median": float(subset["crop_h"].median()),
                    "crop_h_p10": float(subset["crop_h"].quantile(0.10)),
                    "aspect_h/w_median": float((subset["crop_h"] / subset["crop_w"]).median()),
                }
            )
    return per_class, by_split, pd.DataFrame(size_rows)


def markdown_table(df: pd.DataFrame, float_digits: int = 1) -> str:
    formatted = df.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(
                lambda value: "-" if pd.isna(value) else f"{value:.{float_digits}f}"
            )
    header = "| " + " | ".join(map(str, formatted.columns)) + " |"
    divider = "| " + " | ".join("---" for _ in formatted.columns) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in formatted.itertuples(index=False)]
    return "\n".join([header, divider, *body])


def main() -> int:
    arguments = parse_arguments()
    data_dir: Path = arguments.data_dir
    if not data_dir.is_dir():
        sys.exit(f"ERROR: --data-dir is not a directory: {data_dir}")
    out_dir: Path = arguments.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_path = find_single(data_dir, "dataset.csv")
    failed_path = find_single(data_dir, "failed_samples.csv")
    classes_path = find_single(data_dir, "classes.json")
    summary_path = dataset_path.parent / "extraction_summary.json"

    dataset = pd.read_csv(dataset_path)
    failed = pd.read_csv(failed_path)
    classes = json.loads(classes_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}

    missing_meta = [column for column in META_COLUMNS if column not in dataset.columns]
    if missing_meta:
        sys.exit(f"ERROR: dataset.csv is missing metadata columns: {missing_meta}")

    report: list[str] = ["# Phase 0 분석 결과", ""]
    report.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 데이터 경로(이 PC 기준): `{data_dir}`")
    report.append("")

    report.append("## 데이터 출처")
    report.append("")
    sources = [
        describe_file(dataset_path, len(dataset)),
        describe_file(failed_path, len(failed)),
        describe_file(classes_path, len(classes)),
    ]
    report.append(markdown_table(pd.DataFrame(sources)))
    report.append("")

    report.append("## 1. 메타데이터 컬럼")
    report.append("")
    meta_rows = [
        {"column": column, "dtype": str(dataset[column].dtype), "example": str(dataset[column].iloc[0])}
        for column in META_COLUMNS
    ]
    report.append(markdown_table(pd.DataFrame(meta_rows)))
    report.append("")
    report.append(f"- 전체 컬럼 {dataset.shape[1]}개 = 메타 {len(META_COLUMNS)} + feature {dataset.shape[1] - len(META_COLUMNS)}")
    report.append(f"- sample_id 중복 없음: {dataset['sample_id'].is_unique}")
    report.append(f"- image_name 고유 수: {dataset['image_name'].nunique()} / 행 {len(dataset)}")
    report.append(f"- person_index 분포: {dataset['person_index'].value_counts().to_dict()}")
    report.append(f"- split 분포: {dataset['split'].value_counts().to_dict()}")
    report.append(f"- class 분포: {dataset['label'].value_counts().to_dict()}")

    dataset = restore_crop_sizes(dataset, data_dir)
    report.append("")
    report.append("### crop 픽셀 w, h 복원 검증")
    report.append("")
    report.append(
        "복원식: `labels/*.txt`(YOLO bbox) + `Annotations/*.json`(원본 width/height) → "
        f"학습 저장소와 동일한 padding {BBOX_PADDING}. 검증: `extraction_summary.json`의 crop_statistics와 대조."
    )
    report.append("")
    failed = restore_crop_sizes(failed, data_dir)
    if summary:
        # extraction_summary.json의 crop 통계는 성공 + 실패 샘플 전체(total_annotations) 기준이다.
        report.append(f"- 대조 대상: dataset.csv + failed_samples.csv = {len(dataset) + len(failed)}행")
        combined = pd.concat([dataset[["crop_w", "crop_h"]], failed[["crop_w", "crop_h"]]], ignore_index=True)
        report.extend(f"- {line}" for line in crop_checksum(combined, summary))
    else:
        report.append("- extraction_summary.json 없음: 검증 불가")
    unrestored = int(dataset["crop_w"].isna().sum())
    if unrestored:
        print(f"WARNING: {unrestored} rows could not be restored; excluded from angle analysis.")
    dataset = dataset.dropna(subset=["crop_w", "crop_h"]).reset_index(drop=True)

    dataset = compute_angles(dataset)

    report.append("")
    report.append("## 2. 측면 샘플 필터")
    report.append("")
    report.append(
        "- 비율 = |왼쪽 어깨 x − 오른쪽 어깨 x| ÷ (어깨 중점 ~ 엉덩이 중점 거리), 모두 crop 픽셀 좌표로 보정 후 계산"
    )
    report.append(f"- 주 임계값 {SIDE_RATIO_PRIMARY} (**임시 초기값**). 아래 표로 민감도를 함께 확인")
    report.append("")
    report.append(markdown_table(side_threshold_counts(dataset)))
    save_side_ratio_histogram(dataset, out_dir / "side_ratio_hist.png")
    report.append("")
    report.append("![side ratio](side_ratio_hist.png)")

    report.append("")
    report.append("## 3. stand / squat 무릎각 분포 (가까운 쪽 다리)")
    report.append("")
    report.append("- 가까운 쪽 다리: hip, knee, ankle visibility 합이 큰 쪽")
    report.append(f"- `side+vis`: 측면 필터 + 다리/몸통 관절 visibility ≥ {MIN_VISIBILITY}")
    report.append("")
    angle_table = build_angle_table(dataset)
    angle_table.to_csv(out_dir / "knee_angle_percentiles.csv", index=False, encoding="utf-8")
    report.append(markdown_table(angle_table))
    save_histogram(dataset, out_dir / "knee_angle_hist.png")
    report.append("")
    report.append("![knee angle](knee_angle_hist.png)")
    report.append("")
    report.append("### landmark가 crop(0~1) 밖에 있는 비율")
    report.append("")
    report.append(markdown_table(outside_unit_square_rate(dataset)))

    per_class, by_split, size_table = failed_analysis(dataset, failed, data_dir)
    per_class.to_csv(out_dir / "failed_by_class.csv", index=False, encoding="utf-8")
    report.append("")
    report.append("## 4. failed_samples.csv 클래스 분포")
    report.append("")
    report.append(f"- 실패 사유: {failed['reason'].value_counts().to_dict()}")
    report.append("")
    report.append(markdown_table(per_class, 2))
    report.append("")
    report.append("### class × split")
    report.append("")
    report.append(markdown_table(by_split))
    report.append("")
    report.append("### 성공/실패 crop 크기 비교 (픽셀)")
    report.append("")
    report.append(markdown_table(size_table, 1))

    report_path = out_dir / "phase0_report.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
