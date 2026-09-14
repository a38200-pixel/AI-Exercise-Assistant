"""Read-only size and duplicate inventory for the frozen FitRoute AI Client."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


NVIDIA_PREFIXES = (
    "cudnn",
    "cublas",
    "cufft",
    "curand",
    "cusolver",
    "cusparse",
    "nvrtc",
    "nvjitlink",
    "cuda",
    "npp",
    "nccl",
    "nvtoolsext",
    "cudart",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def owner(relative_path: str) -> str:
    value = relative_path.replace("\\", "/").lower()
    name = Path(value).name
    if value.startswith("models/"):
        return "FitRoute model"
    if "/torch/" in f"/{value}" or "/torch-" in f"/{value}":
        return "PyTorch"
    if "torchvision" in value:
        return "TorchVision"
    if "tensorrt" in value or name.startswith(("nvinfer", "nvonnxparser")):
        return "TensorRT"
    if "mediapipe" in value:
        return "MediaPipe"
    if "/cv2/" in f"/{value}" or "opencv" in value:
        return "OpenCV"
    if "xgboost" in value:
        return "XGBoost"
    if "/sklearn/" in f"/{value}" or "scikit_learn" in value:
        return "scikit-learn"
    if "/scipy" in f"/{value}":
        return "SciPy"
    if "/numpy" in f"/{value}":
        return "NumPy"
    if "matplotlib" in value or "mpl-data" in value:
        return "Matplotlib"
    if "ultralytics" in value:
        return "Ultralytics"
    if name.endswith((".dll", ".pyd", ".so")):
        return "Native/Python runtime"
    return "Python package data"


def summary(paths: list[Path], root: Path) -> dict[str, int]:
    selected = [path for path in paths if path.is_file()]
    return {
        "bytes": sum(path.stat().st_size for path in selected),
        "files": len(selected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        nargs="?",
        type=Path,
        default=Path("dist/FitRouteAIClient"),
    )
    args = parser.parse_args()
    root = args.bundle.resolve()
    if not root.is_dir():
        parser.error(f"bundle does not exist: {root}")

    files = sorted(path for path in root.rglob("*") if path.is_file())
    directories = sorted(path for path in root.rglob("*") if path.is_dir())
    file_sizes = {path: path.stat().st_size for path in files}

    def relative(path: Path) -> str:
        return path.relative_to(root).as_posix()

    def subtree(path: Path) -> dict[str, int | str]:
        entries = [item for item in files if item == path or path in item.parents]
        return {"path": relative(path), **summary(entries, root)}

    top_level = [subtree(path) for path in root.iterdir()]
    top_level.sort(key=lambda item: int(item["bytes"]), reverse=True)

    internal = root / "_internal"
    internal_directories = [subtree(path) for path in internal.iterdir() if path.is_dir()]
    internal_directories.sort(key=lambda item: int(item["bytes"]), reverse=True)
    bundle_bytes = sum(file_sizes.values())
    for item in internal_directories:
        item["percent"] = round(int(item["bytes"]) * 100 / bundle_bytes, 4)

    largest_files = []
    for path in sorted(files, key=file_sizes.get, reverse=True)[:50]:
        rel = relative(path)
        largest_files.append(
            {
                "path": rel,
                "bytes": file_sizes[path],
                "extension": path.suffix.lower() or "[none]",
                "owner": owner(rel),
            }
        )

    over_50_mib = [
        {
            "path": relative(path),
            "bytes": file_sizes[path],
            "extension": path.suffix.lower() or "[none]",
            "owner": owner(relative(path)),
        }
        for path in sorted(files, key=file_sizes.get, reverse=True)
        if file_sizes[path] >= 50 * 1024 * 1024
    ]

    component_rules = {
        "torch": lambda rel: rel.startswith("_internal/torch/"),
        "torch_lib": lambda rel: rel.startswith("_internal/torch/lib/"),
        "torchvision": lambda rel: rel.startswith("_internal/torchvision/")
        or rel.startswith("_internal/torchvision-"),
        "tensorrt": lambda rel: "tensorrt" in rel.lower()
        or Path(rel).name.lower().startswith(("nvinfer", "nvonnxparser")),
        "mediapipe": lambda rel: rel.startswith("_internal/mediapipe")
        or rel.startswith("_internal/mediapipe-"),
        "opencv": lambda rel: rel.startswith("_internal/cv2/")
        or "opencv" in Path(rel).name.lower(),
        "xgboost": lambda rel: rel.startswith("_internal/xgboost")
        or rel.startswith("_internal/xgboost-"),
        "sklearn": lambda rel: rel.startswith("_internal/sklearn/")
        or "scikit_learn" in rel.lower(),
        "scipy": lambda rel: rel.startswith("_internal/scipy")
        or rel.startswith("_internal/scipy.libs/"),
        "numpy": lambda rel: rel.startswith("_internal/numpy")
        or rel.startswith("_internal/numpy.libs/"),
        "matplotlib": lambda rel: rel.startswith("_internal/matplotlib/")
        or "mpl-data" in rel.lower(),
        "ultralytics": lambda rel: rel.startswith("_internal/ultralytics")
        or rel.startswith("_internal/ultralytics-"),
        "models": lambda rel: rel.startswith("models/"),
    }
    components = {}
    for name, rule in component_rules.items():
        selected = [path for path in files if rule(relative(path))]
        components[name] = summary(selected, root)

    torch_cuda_files = [
        path
        for path in files
        if relative(path).startswith("_internal/torch/lib/")
        and path.suffix.lower() == ".dll"
        and path.name.lower().startswith(NVIDIA_PREFIXES + ("torch_cuda",))
    ]
    components["torch_cuda_dlls"] = summary(torch_cuda_files, root)

    torch_root = internal / "torch"
    torch_breakdown = [subtree(path) for path in torch_root.iterdir()] if torch_root.is_dir() else []
    torch_breakdown.sort(key=lambda item: int(item["bytes"]), reverse=True)

    torchvision_root = internal / "torchvision"
    torchvision_breakdown = (
        [subtree(path) for path in torchvision_root.iterdir()] if torchvision_root.is_dir() else []
    )
    torchvision_breakdown.sort(key=lambda item: int(item["bytes"]), reverse=True)

    package_breakdowns = {}
    for package_name in (
        "mediapipe",
        "cv2",
        "xgboost",
        "sklearn",
        "scipy",
        "numpy",
        "matplotlib",
        "ultralytics",
    ):
        package_root = internal / package_name
        items = [subtree(path) for path in package_root.iterdir()] if package_root.is_dir() else []
        items.sort(key=lambda item: int(item["bytes"]), reverse=True)
        package_breakdowns[package_name] = items

    nvidia_files = []
    for path in files:
        lower_name = path.name.lower()
        if path.suffix.lower() == ".dll" and lower_name.startswith(NVIDIA_PREFIXES):
            nvidia_files.append(
                {
                    "name": path.name,
                    "path": relative(path),
                    "bytes": file_sizes[path],
                }
            )
    nvidia_files.sort(key=lambda item: int(item["bytes"]), reverse=True)

    tensorrt_files = []
    for path in files:
        rel = relative(path)
        lower = path.name.lower()
        if component_rules["tensorrt"](rel):
            if lower.startswith("nvinfer_builder_resource"):
                classification = "B"
                kind = "builder resource"
            elif lower.startswith("nvonnxparser"):
                classification = "B"
                kind = "ONNX parser"
            elif "lean" in lower or "dispatch" in lower:
                classification = "C"
                kind = "lean/dispatch runtime"
            elif lower.startswith("nvinfer_plugin"):
                classification = "A"
                kind = "plugin runtime"
            elif lower.startswith("nvinfer"):
                classification = "A"
                kind = "inference runtime"
            elif "bindings" in rel.lower():
                classification = "A"
                kind = "Python bindings"
            else:
                classification = "C"
                kind = "package metadata/resource"
            tensorrt_files.append(
                {
                    "path": rel,
                    "bytes": file_sizes[path],
                    "classification": classification,
                    "kind": kind,
                }
            )
    tensorrt_files.sort(key=lambda item: int(item["bytes"]), reverse=True)

    extension_counts: dict[str, dict[str, int]] = {}
    by_extension: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        by_extension[path.suffix.lower() or "[none]"].append(path)
    for extension, paths in by_extension.items():
        extension_counts[extension] = summary(paths, root)

    dll_groups: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        if path.suffix.lower() == ".dll":
            dll_groups[path.name.lower()].append(path)

    duplicate_dlls = []
    exact_waste = 0
    exact_group_count = 0
    different_group_count = 0
    for name, paths in dll_groups.items():
        if len(paths) < 2:
            continue
        entries = []
        hashes = Counter()
        sizes_by_hash: dict[str, int] = {}
        for path in paths:
            digest = sha256(path)
            hashes[digest] += 1
            sizes_by_hash[digest] = file_sizes[path]
            entries.append(
                {
                    "path": relative(path),
                    "bytes": file_sizes[path],
                    "sha256": digest,
                }
            )
        group_waste = sum((count - 1) * sizes_by_hash[digest] for digest, count in hashes.items())
        if any(count > 1 for count in hashes.values()):
            exact_group_count += 1
        if len(hashes) > 1:
            different_group_count += 1
        exact_waste += group_waste
        duplicate_dlls.append(
            {
                "name": name,
                "copies": len(paths),
                "hashes": len(hashes),
                "exact_waste_bytes": group_waste,
                "entries": entries,
            }
        )
    duplicate_dlls.sort(
        key=lambda item: (int(item["exact_waste_bytes"]), sum(e["bytes"] for e in item["entries"])),
        reverse=True,
    )

    result = {
        "root": str(root),
        "totals": {
            "bytes": bundle_bytes,
            "files": len(files),
            "directories_excluding_root": len(directories),
        },
        "top_level": top_level,
        "internal_top_directories": internal_directories[:30],
        "largest_files": largest_files,
        "files_over_50_mib": over_50_mib,
        "components": components,
        "torch_breakdown": torch_breakdown,
        "torchvision_breakdown": torchvision_breakdown,
        "package_breakdowns": package_breakdowns,
        "nvidia_files": nvidia_files,
        "tensorrt_files": tensorrt_files,
        "extension_summary": extension_counts,
        "duplicate_dll_summary": {
            "same_name_groups": len(duplicate_dlls),
            "exact_duplicate_groups": exact_group_count,
            "same_name_different_binary_groups": different_group_count,
            "exact_waste_bytes": exact_waste,
        },
        "duplicate_dlls": duplicate_dlls,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
