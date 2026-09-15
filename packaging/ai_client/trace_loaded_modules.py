"""Trace native modules loaded by the Windows FitRoute AI Client.

The tracer is read-only with respect to the target bundle. It launches the
requested executable, polls Toolhelp32 module snapshots, and writes reports
after the child exits normally (Q or ESC in the FitRoute camera window).
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
ERROR_NO_MORE_FILES = 18
ERROR_BAD_LENGTH = 24
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MAX_MODULE_NAME32 = 255
MAX_PATH = 260

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIRECTORY = REPOSITORY_ROOT / "artifacts" / "runtime-traces"
DEFAULT_JSON_OUTPUT = DEFAULT_ARTIFACT_DIRECTORY / "runtime_module_trace.json"
DEFAULT_MARKDOWN_OUTPUT = DEFAULT_ARTIFACT_DIRECTORY / "runtime_module_trace.md"
DEFAULT_TORCH_INVENTORY = (
    REPOSITORY_ROOT / "artifacts" / "ai-client" / "ai_client_torch_bundle_inventory.json"
)

FALLBACK_STATIC_REQUIRED = {
    "cublas64_12.dll",
    "cublaslt64_12.dll",
    "cudnn64_9.dll",
    "cufft64_11.dll",
    "cusolver64_11.dll",
    "cusparse64_12.dll",
    "c10.dll",
    "c10_cuda.dll",
    "msvcp140.dll",
    "torch_cpu.dll",
}


class MODULEENTRY32W(ctypes.Structure):
    """Windows MODULEENTRY32W structure."""

    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(wintypes.BYTE)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * (MAX_MODULE_NAME32 + 1)),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    ]


class TraceError(RuntimeError):
    """Raised for an actionable tracer failure."""


def _windows_api() -> tuple[Any, Any, Any, Any]:
    if os.name != "nt":
        raise TraceError("This tracer supports Windows only.")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_snapshot = kernel32.CreateToolhelp32Snapshot
    create_snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    create_snapshot.restype = wintypes.HANDLE

    module_first = kernel32.Module32FirstW
    module_first.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    module_first.restype = wintypes.BOOL

    module_next = kernel32.Module32NextW
    module_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    module_next.restype = wintypes.BOOL

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    return create_snapshot, module_first, module_next, close_handle


def enumerate_modules(pid: int) -> list[dict[str, Any]]:
    """Return one Toolhelp32 module snapshot for *pid*."""
    create_snapshot, module_first, module_next, close_handle = _windows_api()
    snapshot = None
    for _attempt in range(5):
        ctypes.set_last_error(0)
        snapshot = create_snapshot(
            TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
            pid,
        )
        if snapshot != INVALID_HANDLE_VALUE:
            break
        error = ctypes.get_last_error()
        if error != ERROR_BAD_LENGTH:
            raise TraceError(
                f"CreateToolhelp32Snapshot failed for PID {pid}: "
                f"WinError {error} ({ctypes.FormatError(error).strip()})"
            )
        time.sleep(0.01)
    else:
        raise TraceError(
            f"CreateToolhelp32Snapshot repeatedly returned ERROR_BAD_LENGTH "
            f"for PID {pid}."
        )

    assert snapshot is not None
    modules: list[dict[str, Any]] = []
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        ctypes.set_last_error(0)
        if not module_first(snapshot, ctypes.byref(entry)):
            error = ctypes.get_last_error()
            if error == ERROR_NO_MORE_FILES:
                return []
            raise TraceError(
                f"Module32FirstW failed for PID {pid}: "
                f"WinError {error} ({ctypes.FormatError(error).strip()})"
            )

        while True:
            modules.append(
                {
                    "basename": entry.szModule,
                    "full_path": entry.szExePath,
                    "image_size": int(entry.modBaseSize),
                }
            )
            ctypes.set_last_error(0)
            if not module_next(snapshot, ctypes.byref(entry)):
                error = ctypes.get_last_error()
                if error != ERROR_NO_MORE_FILES:
                    raise TraceError(
                        f"Module32NextW failed for PID {pid}: "
                        f"WinError {error} ({ctypes.FormatError(error).strip()})"
                    )
                break
    finally:
        close_handle(snapshot)
    return modules


def normalized_path(path: Path | str) -> str:
    """Return a Windows-case-insensitive comparison key."""
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def path_is_within(path: Path | str, root: Path | str) -> bool:
    try:
        return os.path.commonpath(
            [normalized_path(path), normalized_path(root)]
        ) == normalized_path(root)
    except ValueError:
        return False


def path_origin(path: str, bundle_root: Path) -> str:
    """Classify a loaded module's provider."""
    basename = Path(path).name.casefold()
    normalized = normalized_path(path)
    nvidia_names = {
        "nvcuda.dll",
        "nvapi64.dll",
        "nvml.dll",
        "nvd3dumx.dll",
        "nvwgf2umx.dll",
        "nvldumdx.dll",
    }
    if path_is_within(path, bundle_root):
        return "BUNDLE"
    if (
        basename in nvidia_names
        or basename.startswith(("nvoglv", "nvgpucomp", "nvcompiler"))
        or "nvidia corporation" in normalized
        or "\\nvidia corporation\\" in normalized
    ):
        return "NVIDIA_DRIVER"
    windows_root = Path(os.environ.get("WINDIR", r"C:\Windows"))
    if path_is_within(path, windows_root):
        return "WINDOWS"
    return "EXTERNAL"


def native_group(relative_path: str, basename: str) -> tuple[str, str]:
    """Return (group, component) for a bundled native file."""
    rel = relative_path.replace("\\", "/").casefold()
    name = basename.casefold()
    cuda_prefixes = (
        ("cublaslt", "cuBLASLt"),
        ("cublas", "cuBLAS"),
        ("cudnn", "cuDNN"),
        ("cufft", "cuFFT"),
        ("curand", "cuRAND"),
        ("cusolver", "cuSOLVER"),
        ("cusparse", "cuSPARSE"),
        ("cudart", "CUDA runtime"),
        ("nvrtc", "NVRTC"),
        ("caffe2_nvrtc", "NVRTC"),
        ("nvjitlink", "NVJitLink"),
        ("cupti", "CUPTI"),
        ("nvtoolsext", "NVTX"),
        ("nvperf", "nvperf"),
    )
    if "torchvision/" in rel:
        return "TorchVision", "TorchVision native"
    if any(part in rel for part in ("tensorrt", "nvinfer", "nvonnxparser")):
        return "TensorRT", "TensorRT runtime/binding"
    for prefix, component in cuda_prefixes:
        if name.startswith(prefix):
            return "CUDA", component
    if "/torch/lib/" in f"/{rel}" or name.startswith(("torch", "c10")):
        return "Torch", "Torch core"
    if "/cv2/" in f"/{rel}" or name.startswith("opencv"):
        return "OpenCV", "OpenCV native"
    if "mediapipe" in rel:
        return "MediaPipe", "MediaPipe native"
    if "xgboost" in rel:
        return "XGBoost", "XGBoost native"
    return "Other", "Other native"


def load_static_required(inventory_path: Path) -> set[str]:
    """Load Torch PE direct dependencies from the 6-B-3A inventory."""
    required = set(FALLBACK_STATIC_REQUIRED)
    if not inventory_path.is_file():
        return required
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        dlls = payload.get("torch_lib_dlls", [])
        by_name = {item.get("name", "").casefold(): item for item in dlls}
        torch_cuda = by_name.get("torch_cuda.dll", {})
        required.update(
            Path(name).name.casefold()
            for name in torch_cuda.get("direct_imports", [])
        )
    except (OSError, ValueError, TypeError) as exc:
        print(
            f"Warning: could not read Torch PE inventory {inventory_path}: {exc}",
            file=sys.stderr,
        )
    return required


def bundle_native_inventory(
    bundle_root: Path,
    static_required: set[str],
) -> list[dict[str, Any]]:
    """Inventory every DLL and PYD under the target bundle."""
    inventory = []
    for path in sorted(
        (
            item
            for item in bundle_root.rglob("*")
            if item.is_file() and item.suffix.casefold() in {".dll", ".pyd"}
        ),
        key=lambda item: item.as_posix().casefold(),
    ):
        relative = path.relative_to(bundle_root).as_posix()
        group, component = native_group(relative, path.name)
        inventory.append(
            {
                "basename": path.name,
                "relative_path": relative,
                "full_path": str(path.resolve()),
                "bytes": path.stat().st_size,
                "mib": round(path.stat().st_size / 1024 / 1024, 6),
                "group": group,
                "component": component,
                "static_required": path.name.casefold() in static_required,
            }
        )
    return inventory


def unique_output_path(path: Path, started_at: datetime) -> Path:
    """Avoid overwriting an earlier runtime observation."""
    if not path.exists():
        return path
    stamp = started_at.astimezone().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}-{stamp}{path.suffix}")


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise TraceError(f"Failed to write report {path}: {exc}") from exc


def summarize_groups(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, int]] = {}
    for item in inventory:
        group = groups.setdefault(
            item["group"],
            {
                "files": 0,
                "bytes": 0,
                "loaded": 0,
                "static_required": 0,
                "not_observed": 0,
                "unknown": 0,
            },
        )
        group["files"] += 1
        group["bytes"] += item["bytes"]
        if item["status"] == "LOADED":
            group["loaded"] += 1
        elif item["status"] == "NOT_OBSERVED":
            group["not_observed"] += 1
        elif item["status"] == "UNKNOWN":
            group["unknown"] += 1
        if item["static_required"]:
            group["static_required"] += 1
    return [
        {
            "group": name,
            **values,
            "mib": round(values["bytes"] / 1024 / 1024, 6),
        }
        for name, values in sorted(groups.items())
    ]


def markdown_report(payload: dict[str, Any]) -> str:
    process = payload["process"]
    inventory = payload["bundle_native_inventory"]
    loaded_bundle = [item for item in inventory if item["status"] == "LOADED"]
    not_observed = sorted(
        (item for item in inventory if item["status"] == "NOT_OBSERVED"),
        key=lambda item: item["bytes"],
        reverse=True,
    )
    static_required = [
        item for item in inventory if item["static_required"]
    ]
    origins = payload["loaded_module_origin_summary"]
    checks = payload["baseline_validation"]

    lines = [
        "# FitRoute runtime module trace",
        "",
        "## Execution",
        "",
        f"- Executable: `{process['exe']}`",
        f"- Arguments: `{' '.join(process['arguments'])}`",
        f"- PID: {process['pid']}",
        f"- Started: {process['started_at']}",
        f"- Elapsed: {process['elapsed_seconds']:.3f} seconds",
        f"- Poll interval: {payload['poll_interval_ms']} ms",
        f"- Exit code: {process['exit_code']}",
        "",
        "## Summary",
        "",
        f"- Unique modules observed: {len(payload['loaded_modules'])}",
        f"- Bundle native inventory: {len(inventory)}",
        f"- Loaded bundle native: {len(loaded_bundle)}",
        f"- Static-required native files: {len(static_required)}",
        f"- Not observed bundle native: {len(not_observed)}",
        "- `NOT_OBSERVED` means review only; it does not mean removable.",
        "",
        "## Baseline validation",
        "",
        f"- TensorRT builder resources: {checks['tensorrt_builder_resources']}",
        f"- Polars runtime paths: {checks['polars_runtime_paths']}",
        f"- `torch/bin/protoc.exe`: {checks['torch_bin_protoc']}",
        "",
        "## Loaded module origins",
        "",
        f"- BUNDLE: {origins.get('BUNDLE', 0)}",
        f"- WINDOWS: {origins.get('WINDOWS', 0)}",
        f"- NVIDIA_DRIVER: {origins.get('NVIDIA_DRIVER', 0)}",
        f"- EXTERNAL: {origins.get('EXTERNAL', 0)}",
        "",
        "## Group summary",
        "",
        "| Group | Files | MiB | Loaded | Static required | Not observed | Unknown |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for group in payload["group_summary"]:
        lines.append(
            f"| {group['group']} | {group['files']} | {group['mib']:.3f} | "
            f"{group['loaded']} | {group['static_required']} | "
            f"{group['not_observed']} | {group['unknown']} |"
        )

    lines.extend(
        [
            "",
            "## Top 20 NOT_OBSERVED bundle native files",
            "",
            "| File | MiB | Group | Direct dependency | Status |",
            "|---|---:|---|---|---|",
        ]
    )
    for item in not_observed[:20]:
        lines.append(
            f"| `{item['relative_path']}` | {item['mib']:.3f} | "
            f"{item['group']} / {item['component']} | No known direct requirement | "
            "NOT_OBSERVED |"
        )

    lines.extend(
        [
            "",
            "## STATIC_REQUIRED",
            "",
            "These files remain required by the recorded PE dependency graph. A loaded file can be both `LOADED` and `static_required=true`.",
            "",
            "| File | MiB | Group | Status |",
            "|---|---:|---|---|",
        ]
    )
    for item in sorted(static_required, key=lambda value: value["bytes"], reverse=True):
        lines.append(
            f"| `{item['relative_path']}` | {item['mib']:.3f} | "
            f"{item['group']} / {item['component']} | {item['status']} + STATIC_REQUIRED |"
        )

    lines.extend(
        [
            "",
            "## Loaded modules by origin",
            "",
            "| First seen (s) | Module | Origin | Full path |",
            "|---:|---|---|---|",
        ]
    )
    for item in payload["loaded_modules"]:
        lines.append(
            f"| {item['first_observed_seconds']:.3f} | `{item['basename']}` | "
            f"{item['origin']} | `{item['full_path']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- LOADED: observed at least once during this run.",
            "- STATIC_REQUIRED: not observed, but a direct PE dependency of `torch_cuda.dll`; do not remove.",
            "- NOT_OBSERVED: not observed and not statically required by the imported Torch inventory; review only.",
            "- UNKNOWN/EXTERNAL paths must be investigated before any packaging change.",
            "- No file was removed or modified by this trace.",
            "",
        ]
    )
    return "\n".join(lines)


def run_trace(args: argparse.Namespace) -> int:
    exe = Path(args.exe).expanduser().resolve()
    if not exe.is_file():
        raise TraceError(f"Executable does not exist: {exe}")
    if exe.suffix.casefold() != ".exe":
        raise TraceError(f"Expected a Windows .exe file: {exe}")
    if args.interval_ms <= 0:
        raise TraceError("--interval-ms must be greater than zero.")

    bundle_root = exe.parent
    static_required = load_static_required(Path(args.torch_inventory).resolve())
    inventory = bundle_native_inventory(bundle_root, static_required)
    started_wall = datetime.now(timezone.utc)
    started_monotonic = time.monotonic()
    command = [str(exe), "--exercise", args.exercise]
    print(f"Launching: {subprocess.list2cmdline(command)}")
    print("Close the FitRoute camera normally with Q or ESC to finish the trace.")
    try:
        process = subprocess.Popen(command, cwd=str(bundle_root), shell=False)
    except OSError as exc:
        raise TraceError(f"Failed to launch {exe}: {exc}") from exc

    loaded_once: dict[str, dict[str, Any]] = {}
    snapshot_errors = 0
    try:
        while True:
            elapsed = time.monotonic() - started_monotonic
            try:
                modules = enumerate_modules(process.pid)
                snapshot_errors = 0
            except TraceError as exc:
                if process.poll() is not None:
                    break
                snapshot_errors += 1
                if snapshot_errors >= 3:
                    raise TraceError(
                        f"Module snapshot failed three consecutive times: {exc}"
                    ) from exc
                time.sleep(args.interval_ms / 1000)
                continue

            for module in modules:
                key = normalized_path(module["full_path"])
                if key not in loaded_once:
                    module["first_observed_seconds"] = round(elapsed, 6)
                    module["origin"] = path_origin(module["full_path"], bundle_root)
                    module["inside_bundle"] = module["origin"] == "BUNDLE"
                    module["bundle_relative_path"] = (
                        Path(module["full_path"]).resolve().relative_to(bundle_root).as_posix()
                        if module["inside_bundle"]
                        else None
                    )
                    loaded_once[key] = module

            if process.poll() is not None:
                break
            time.sleep(args.interval_ms / 1000)
    except (KeyboardInterrupt, TraceError):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        raise

    elapsed_seconds = time.monotonic() - started_monotonic
    observed_paths = set(loaded_once)
    for item in inventory:
        observed = normalized_path(item["full_path"]) in observed_paths
        if observed:
            item["status"] = "LOADED"
        elif item["static_required"]:
            item["status"] = "STATIC_REQUIRED"
        else:
            item["status"] = "NOT_OBSERVED"

    loaded_modules = sorted(
        loaded_once.values(),
        key=lambda item: (item["first_observed_seconds"], item["basename"].casefold()),
    )
    not_observed = [item for item in inventory if item["status"] == "NOT_OBSERVED"]
    static_items = [item for item in inventory if item["static_required"]]
    review = sorted(not_observed, key=lambda item: item["bytes"], reverse=True)
    origin_summary = {name: 0 for name in ("BUNDLE", "WINDOWS", "NVIDIA_DRIVER", "EXTERNAL")}
    for module in loaded_modules:
        origin_summary[module["origin"]] += 1

    all_relative_paths = [
        path.relative_to(bundle_root).as_posix().casefold()
        for path in bundle_root.rglob("*")
        if path.is_file()
    ]
    baseline_validation = {
        "tensorrt_builder_resources": sum(
            "nvinfer_builder_resource_" in path for path in all_relative_paths
        ),
        "polars_runtime_paths": sum(
            "polars" in path.split("/") for path in all_relative_paths
        ),
        "torch_bin_protoc": sum(
            path.endswith("torch/bin/protoc.exe") for path in all_relative_paths
        ),
    }

    json_path = unique_output_path(Path(args.json_output).resolve(), started_wall)
    markdown_path = unique_output_path(Path(args.markdown_output).resolve(), started_wall)
    payload = {
        "process": {
            "pid": process.pid,
            "exe": str(exe),
            "arguments": command[1:],
            "started_at": started_wall.isoformat(),
            "elapsed_seconds": round(elapsed_seconds, 6),
            "exit_code": process.returncode,
        },
        "poll_interval_ms": args.interval_ms,
        "loaded_once": True,
        "loaded_modules": loaded_modules,
        "loaded_module_origin_summary": origin_summary,
        "bundle_native_inventory": inventory,
        "group_summary": summarize_groups(inventory),
        "baseline_validation": baseline_validation,
        "not_observed_bundle_native": not_observed,
        "static_required": static_items,
        "candidate_for_review": review,
        "reports": {"json": str(json_path), "markdown": str(markdown_path)},
        "notes": [
            "NOT_OBSERVED does not mean removable.",
            "STATIC_REQUIRED remains required regardless of polling observations.",
            "The tracer did not modify the target bundle.",
        ],
    }
    write_text_atomic(json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_text_atomic(markdown_path, markdown_report(payload))

    bundle_loaded = sum(item["status"] == "LOADED" for item in inventory)
    print("Trace complete")
    print(f"Elapsed: {elapsed_seconds:.3f} seconds")
    print(f"Unique modules observed: {len(loaded_modules)}")
    print(f"Bundle modules observed: {bundle_loaded}")
    print(f"NOT_OBSERVED candidates: {len(not_observed)}")
    print(f"Report path: {markdown_path}")
    print(f"JSON path: {json_path}")
    if not loaded_modules:
        raise TraceError(
            "The child exited before any module snapshot could be collected. "
            f"Exit code: {process.returncode}"
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", help="Path to FitRouteAIClient.exe.")
    parser.add_argument(
        "--exercise",
        choices=("squat", "stretch", "idle"),
        default="squat",
        help="Exercise argument passed to the child (default: squat).",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=100,
        help="Module polling interval in milliseconds (default: 100).",
    )
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN_OUTPUT))
    parser.add_argument("--torch-inventory", default=str(DEFAULT_TORCH_INVENTORY))
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Enumerate this Python process without launching the AI Client.",
    )
    args = parser.parse_args(argv)
    if not args.self_test and not args.exe:
        parser.error("--exe is required unless --self-test is used")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            modules = enumerate_modules(os.getpid())
            if not modules:
                raise TraceError("Self-test returned no loaded modules.")
            print(f"Self-test PASS: enumerated {len(modules)} modules for PID {os.getpid()}.")
            print(f"Python module: {modules[0]['full_path']}")
            return 0
        return run_trace(args)
    except TraceError as exc:
        print(f"Trace failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
