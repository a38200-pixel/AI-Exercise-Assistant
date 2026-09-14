"""Read-only Torch inventory and PE dependency analysis for a frozen bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pefile


GROUP_LABELS = {
    "torch_cpu_core": "A. Torch CPU core",
    "torch_cuda_core": "B. Torch CUDA core",
    "cublas": "C. cuBLAS",
    "cudnn": "D. cuDNN",
    "cufft": "E. cuFFT",
    "curand": "F. cuRAND",
    "cusolver": "G. cuSOLVER",
    "cusparse": "H. cuSPARSE",
    "cuda_runtime": "I. CUDA runtime / cudart",
    "nvrtc": "J. NVRTC",
    "nvjitlink": "K. NVJitLink",
    "distributed": "L. NCCL / distributed support",
    "profiler": "M. profiler / NVTX",
    "openmp": "N. OpenMP / runtime",
    "other": "O. Other",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(paths: list[Path]) -> dict[str, int | float]:
    files = [path for path in paths if path.is_file()]
    size = sum(path.stat().st_size for path in files)
    return {"bytes": size, "mib": round(size / 1024 / 1024, 6), "files": len(files)}


def files_below(path: Path) -> list[Path]:
    return sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else []


def dll_group(name: str) -> str:
    lower = name.lower()
    if lower.startswith("cublas"):
        return "cublas"
    if lower.startswith("cudnn"):
        return "cudnn"
    if lower.startswith("cufft"):
        return "cufft"
    if lower.startswith("curand"):
        return "curand"
    if lower.startswith("cusolver"):
        return "cusolver"
    if lower.startswith("cusparse"):
        return "cusparse"
    if lower.startswith("cudart"):
        return "cuda_runtime"
    if lower.startswith("nvjitlink"):
        return "nvjitlink"
    if lower.startswith(("nvrtc", "caffe2_nvrtc")):
        return "nvrtc"
    if lower.startswith(("cupti", "nvperf", "nvtoolsext")):
        return "profiler"
    if lower.startswith(("libiomp", "vcomp")):
        return "openmp"
    if lower in {"uv.dll", "shm.dll"} or lower.startswith("nccl"):
        return "distributed"
    if lower in {"torch_cuda.dll", "c10_cuda.dll"}:
        return "torch_cuda_core"
    if lower in {
        "torch_cpu.dll",
        "torch_python.dll",
        "torch.dll",
        "torch_global_deps.dll",
        "c10.dll",
    }:
        return "torch_cpu_core"
    return "other"


def pe_details(path: Path) -> tuple[str, list[str]]:
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    )
    machine = pefile.MACHINE_TYPE.get(pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine))
    imports = sorted(
        entry.dll.decode(errors="replace")
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])
    )
    pe.close()
    return machine, imports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle",
        nargs="?",
        type=Path,
        default=Path("dist_candidate_polars/FitRouteAIClient"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionally write the JSON inventory to this path.",
    )
    args = parser.parse_args()
    root = args.bundle.resolve()
    if not root.is_dir():
        parser.error(f"bundle does not exist: {root}")

    internal = root / "_internal"
    torch_root = internal / "torch"
    torch_lib = torch_root / "lib"
    torchvision_root = internal / "torchvision"
    torch_files = files_below(torch_root)
    torch_lib_files = files_below(torch_lib)
    torch_dlls = sorted(
        (path for path in torch_lib_files if path.suffix.lower() == ".dll"),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )

    dll_inventory = []
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in torch_dlls:
        machine, imports = pe_details(path)
        group = dll_group(path.name)
        grouped[group].append(path)
        dll_inventory.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "mib": round(path.stat().st_size / 1024 / 1024, 6),
                "sha256": sha256(path),
                "architecture": machine,
                "direct_imports": imports,
                "group": group,
                "group_label": GROUP_LABELS[group],
            }
        )

    group_summary = {}
    for group in GROUP_LABELS:
        group_summary[group] = {
            "label": GROUP_LABELS[group],
            **summarize(grouped.get(group, [])),
        }

    subtree_names = (
        "_dynamo",
        "_inductor",
        "compiler",
        "fx",
        "export",
        "onnx",
        "jit",
        "distributed",
        "testing",
        "profiler",
    )
    python_subtrees = {
        name: {"exists": (torch_root / name).is_dir(), **summarize(files_below(torch_root / name))}
        for name in subtree_names
    }

    development_resources = {}
    for name in ("include", "share", "cmake"):
        path = torch_root / name
        development_resources[name] = {
            "exists": path.exists(),
            **summarize(files_below(path)),
        }

    test_segments = {"test", "tests", "testing", "example", "examples", "benchmark", "benchmarks"}
    test_files = [
        path
        for path in torch_files
        if any(part.lower() in test_segments for part in path.relative_to(torch_root).parts[:-1])
    ]

    root_native = [
        path
        for path in internal.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".dll", ".pyd"}
        and torch_lib not in path.parents
        and path.name.lower().startswith(("torch", "c10", "cuda", "cud", "cublas", "cufft", "curand", "cusolver", "cusparse", "nvrtc", "nvjit", "nccl", "nvtx"))
    ]

    result = {
        "bundle": str(root),
        "bundle_total": summarize(files_below(root)),
        "torch": summarize(torch_files),
        "torch_lib": summarize(torch_lib_files),
        "torch_python_and_data": summarize([path for path in torch_files if torch_lib not in path.parents]),
        "torchvision": summarize(files_below(torchvision_root)),
        "torch_related_root_native": [
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
            }
            for path in sorted(root_native)
        ],
        "torch_lib_dll_count": len(torch_dlls),
        "torch_lib_dll_groups": group_summary,
        "torch_lib_dlls": dll_inventory,
        "torch_top_50_files": [
            {
                "path": path.relative_to(torch_root).as_posix(),
                "bytes": path.stat().st_size,
                "mib": round(path.stat().st_size / 1024 / 1024, 6),
            }
            for path in sorted(torch_files, key=lambda item: item.stat().st_size, reverse=True)[:50]
        ],
        "python_subtrees": python_subtrees,
        "development_resources": development_resources,
        "tests_examples_benchmarks": summarize(test_files),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        print(output)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
