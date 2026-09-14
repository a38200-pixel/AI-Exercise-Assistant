"""Validate the immutable inputs used by the FitRoute Inno Setup installer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_ROOT = Path(__file__).resolve().parent
AI_ROOT = REPOSITORY_ROOT / "dist_candidate_protoc" / "FitRouteAIClient"
AI_EXE = AI_ROOT / "FitRouteAIClient.exe"
LAUNCHER_EXE = REPOSITORY_ROOT / "desktop_launcher" / "dist" / "FitRouteLauncher.exe"
CONFIG_PATH = INSTALLER_ROOT / "config.production.json"
ISS_PATH = INSTALLER_ROOT / "FitRouteAIClient.iss"
MANIFEST_PATH = INSTALLER_ROOT / "installer_manifest.json"

APP_ID = "{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}"
VERSION = "0.1.0"
EXPECTED_AI_BYTES = 5_203_968_114
EXPECTED_AI_FILE_COUNT = 3_653
EXPECTED_LAUNCHER_SHA256 = "7FCBBB7EB2AC36939AA24C6B77A4ABF1330CFF61907FF2F3093904FF1E36B173"
EXPECTED_AI_EXE_SHA256 = "09799FF2FABA0D53EA3CC4FB6DB32E80008A1257B14A51BEDE4F877CE3730A47"
EXPECTED_MODELS = {
    "models/detector/yolo26n.engine": "BBA6FE01B7114764E4C6625D49E06EBABBCFD15FABFF41E5CBC77BD7F60DAE11",
    "models/pose/pose_landmarker_full.task": "5134A3AAD27A58B93DA0088D431F366DA362B44E3CCFBE3462B3827A839011B1",
    "models/classifier/model_weights.xgb": "93571ABF066A2EF50840C88B83B40571D1BCBE93878347613AA9138E07F0A99D",
    "models/classifier/classes.json": "A5D6627B3862AAC345A3F40EDE1774C3231F924ACE79B48FCD9A66F907091D87",
}


class ValidationError(RuntimeError):
    """Raised when an installer input violates the pinned release contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Production config is unreadable: {exc}") from exc
    require(isinstance(value, dict), "Production config must be a JSON object.")
    return value


def validate_config(config: dict[str, Any]) -> None:
    expected_keys = {
        "ai_client_executable",
        "api_base_url",
        "supabase_url",
        "supabase_anon_key",
    }
    require(set(config) == expected_keys, "Production config schema is not exact.")
    require(
        config["ai_client_executable"].replace("/", "\\").casefold()
        == r"ai_client\fitrouteaiclient.exe".casefold(),
        "AI executable must be the install-relative ai_client path.",
    )
    require(
        config["api_base_url"] == "https://fitroute-api.onrender.com",
        "Production API URL is not pinned to Render.",
    )
    require(
        isinstance(config["supabase_url"], str)
        and config["supabase_url"].startswith("https://")
        and config["supabase_url"].endswith(".supabase.co"),
        "Supabase URL must be a hosted HTTPS project URL.",
    )
    publishable_key = config["supabase_anon_key"]
    require(
        isinstance(publishable_key, str)
        and publishable_key.startswith("sb_publishable_")
        and len(publishable_key) > len("sb_publishable_"),
        "Only a Supabase publishable client key is allowed.",
    )

    serialized = json.dumps(config, ensure_ascii=False)
    forbidden = (
        "AISW_203_113",
        "Documents\\GitHub",
        "vision_ai",
        "fitroute_build",
        "dist_candidate_protoc",
        "localhost",
        "127.0.0.1",
        "service_role",
        "sb_secret_",
        "FITROUTE_ACCESS_TOKEN=",
        "refresh_token",
        '"password"',
    )
    found = [token for token in forbidden if token.casefold() in serialized.casefold()]
    require(not found, f"Forbidden production config values found: {', '.join(found)}")
    require(
        not re.search(r"(?:^|[\"'\s])[A-Za-z]:[\\/]", serialized),
        "Absolute Windows path found in config.",
    )


def validate_iss() -> str:
    try:
        source = ISS_PATH.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ValidationError(f"Inno Setup script is unreadable: {exc}") from exc

    required_fragments = (
        f"AppId={{{{C75B86BB-3B71-4CDA-BEDF-1040AE9BB0A8}}",
        f'#define MyAppVersion "{VERSION}"',
        "PrivilegesRequired=lowest",
        r"DefaultDirName={localappdata}\Programs\FitRoute AI Client",
        "ArchitecturesAllowed=x64compatible",
        "MinVersion=10.0",
        "Compression=lzma2/normal",
        "SolidCompression=yes",
        "DiskSpanning=no",
        r"AppMutex=Local\FitRouteAIClientCamera",
        r'Source: "..\dist_candidate_protoc\FitRouteAIClient\*"',
        r'DestDir: "{app}\ai_client"',
        r'Subkey: "Software\Classes\fitroute\shell\open\command"',
        r'ValueData: """{app}\{#MyAppExeName}"" ""%1"""',
        "Flags: uninsdeletekey",
        r'Name: "{app}\ai_client"',
        'Parameters: "--logout"',
    )
    missing = [value for value in required_fragments if value not in source]
    require(not missing, f"Required Inno Setup directives are missing: {missing}")
    require("dist_candidate_testing" not in source, "Failed torch.testing candidate is referenced.")
    require("dist_candidate_polars" not in source, "Non-final Polars candidate is referenced.")
    require("..\\dist\\FitRouteAIClient" not in source, "Unoptimized AI bundle is referenced.")
    require("[Run]" not in source, "Post-install execution is not allowed.")
    return source


def validate_bundle() -> tuple[list[Path], dict[str, str]]:
    require(AI_ROOT.is_dir(), f"Final AI baseline is missing: {AI_ROOT}")
    require(AI_EXE.is_file(), f"AI executable is missing: {AI_EXE}")
    require(LAUNCHER_EXE.is_file(), f"Launcher is missing: {LAUNCHER_EXE}")

    files = sorted(path for path in AI_ROOT.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in files)
    require(len(files) == EXPECTED_AI_FILE_COUNT, f"AI file count changed: {len(files)}")
    require(total_bytes == EXPECTED_AI_BYTES, f"AI baseline size changed: {total_bytes}")
    require(sha256(AI_EXE) == EXPECTED_AI_EXE_SHA256, "AI executable hash changed.")
    require(sha256(LAUNCHER_EXE) == EXPECTED_LAUNCHER_SHA256, "Launcher hash changed.")

    model_hashes: dict[str, str] = {}
    for relative, expected_hash in EXPECTED_MODELS.items():
        model = AI_ROOT / Path(relative)
        require(model.is_file(), f"Required model is missing: {relative}")
        actual_hash = sha256(model)
        require(actual_hash == expected_hash, f"Model hash changed: {relative}")
        model_hashes[relative] = actual_hash

    lowered = [path.relative_to(AI_ROOT).as_posix().casefold() for path in files]
    require(
        not any(Path(path).name.startswith("nvinfer_builder_resource_") for path in lowered),
        "TensorRT builder resource remains in the final baseline.",
    )
    require(
        not any(
            part == "polars" or part.startswith("_polars_runtime")
            for path in lowered
            for part in path.split("/")
        ),
        "Polars runtime remains in the final baseline.",
    )
    require(
        "_internal/torch/bin/protoc.exe" not in lowered,
        "torch/bin/protoc.exe remains in the final baseline.",
    )
    for runtime in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
        require(any(Path(path).name == runtime for path in lowered), f"MSVC runtime missing: {runtime}")
    return files, model_hashes


def build_manifest(files: list[Path], model_hashes: dict[str, str], config: dict[str, Any]) -> dict[str, Any]:
    return {
        "installer": {
            "app_id": APP_ID,
            "version": VERSION,
            "scope": "per-user",
            "signed": False,
        },
        "ai_baseline": {
            "source": "dist_candidate_protoc/FitRouteAIClient",
            "file_count": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "mib": round(EXPECTED_AI_BYTES / 1024 / 1024, 6),
            "gib": round(EXPECTED_AI_BYTES / 1024 / 1024 / 1024, 6),
            "executable_sha256": sha256(AI_EXE),
        },
        "launcher": {
            "source": "desktop_launcher/dist/FitRouteLauncher.exe",
            "bytes": LAUNCHER_EXE.stat().st_size,
            "sha256": sha256(LAUNCHER_EXE),
        },
        "models": {
            relative: {
                "bytes": (AI_ROOT / relative).stat().st_size,
                "sha256": digest,
            }
            for relative, digest in model_hashes.items()
        },
        "production_config": {
            "ai_client_executable": config["ai_client_executable"],
            "api_base_url": config["api_base_url"],
            "supabase_url": config["supabase_url"],
            "supabase_key_kind": "publishable",
            "contains_secret_value": False,
        },
        "excluded": {
            "tensorrt_builder_resources": 0,
            "polars_runtime": 0,
            "torch_bin_protoc": 0,
            "torch_testing": "KEEP",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config()
        validate_config(config)
        validate_iss()
        files, model_hashes = validate_bundle()
        manifest = build_manifest(files, model_hashes, config)
        if args.write_manifest:
            MANIFEST_PATH.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print("INSTALLER INPUT VALIDATION PASS")
        print(f"AI baseline: {len(files)} files / {EXPECTED_AI_BYTES} bytes")
        print("TensorRT builder resources: 0")
        print("Polars runtime: 0")
        print("torch/bin/protoc.exe: 0")
        print("Production config: relative AI path, HTTPS services, publishable key")
        return 0
    except (ValidationError, OSError) as exc:
        print(f"INSTALLER INPUT VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
