from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[3]
_FEATURES_JSON = _REPO / ".agents" / "features.json"


def _load_features_json() -> dict:
    return json.loads(_FEATURES_JSON.read_text())


def _scan_feature_dirs() -> dict[str, str]:
    result: dict[str, str] = {}
    for domain_dir in _HERE.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        for feature_dir in domain_dir.iterdir():
            if feature_dir.is_dir() and not feature_dir.name.startswith("_"):
                result[feature_dir.name] = domain_dir.name
    return result


def _scan_standalone_files() -> set[str]:
    return {
        f.name for f in _HERE.iterdir()
        if f.is_file() and f.suffix == ".py" and not f.name.startswith("__")
    }


def test_features_json_covers_all_dirs() -> None:
    cfg = _load_features_json()
    known = cfg.get("known_features", {})
    disk = _scan_feature_dirs()
    missing: list[str] = []
    for fname in disk:
        if fname not in known:
            missing.append(fname)
    msg = "Features on disk missing from features.json: " + repr(missing)
    assert not missing, msg


def test_all_features_json_entries_exist_on_disk() -> None:
    cfg = _load_features_json()
    known = cfg.get("known_features", {})
    disk = _scan_feature_dirs()
    stale: list[str] = []
    domain_mismatch: list[str] = []
    for fname, domain in known.items():
        if fname not in disk:
            stale.append(fname)
        elif disk[fname] != domain:
            parts = (
                f"'{fname}': json=({domain})",
                f"disk=({disk[fname]})"
            )
            domain_mismatch.append(" ".join(parts))
    assert not stale, f"features.json entries missing on disk: {stale}"
    assert not domain_mismatch, f"Domain mismatches: {domain_mismatch}"


def test_standalone_files_listed_in_features_json() -> None:
    cfg = _load_features_json()
    listed = set(cfg.get("standalone", []))
    actual = _scan_standalone_files()
    missing = actual - listed
    extra = listed - actual
    assert not missing, (
        f"Standalone files in features/ not listed: {sorted(missing)}"
    )
    assert not extra, (
        f"Standalone files listed but not on disk: {sorted(extra)}"
    )
