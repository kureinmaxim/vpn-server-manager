#!/usr/bin/env python3
"""Version management for VPN Server Manager."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CONFIG = ROOT / "config.json"
TEMPLATE_CONFIG = ROOT / "config" / "config.json.template"
README_FILE = ROOT / "README.md"
INSTALLER_ISS = ROOT / "vpn-manager-installer.iss"
ENV_EXAMPLE = ROOT / "env.example"
APP_CONFIG = ROOT / "app" / "config.py"
APP_INIT = ROOT / "app" / "__init__.py"
SETUP_PY = ROOT / "setup.py"


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, content, dry_run=False):
    if dry_run:
        print(f"[DRY RUN] Would update {path.relative_to(ROOT)}")
        return
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path.relative_to(ROOT)}")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data, dry_run=False):
    if dry_run:
        print(f"[DRY RUN] Would update {path.relative_to(ROOT)}")
        return
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Updated {path.relative_to(ROOT)}")


def parse_version(version):
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid semantic version: {version}")
    return tuple(int(part) for part in parts)


def bump_semver(version, part):
    major, minor, patch = parse_version(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump part: {part}")


def today_release_date():
    return datetime.now().strftime("%d.%m.%Y")


def today_iso_date():
    return datetime.now().strftime("%Y-%m-%d")


def get_source_metadata():
    data = load_json(SOURCE_CONFIG)
    app_info = data.setdefault("app_info", {})
    return {
        "version": app_info.get("version", "0.0.0"),
        "release_date": app_info.get("release_date", today_release_date()),
        "last_updated": app_info.get("last_updated", today_iso_date()),
    }


def set_source_metadata(metadata, dry_run=False):
    data = load_json(SOURCE_CONFIG)
    app_info = data.setdefault("app_info", {})
    app_info["version"] = metadata["version"]
    app_info["release_date"] = metadata["release_date"]
    app_info["last_updated"] = metadata["last_updated"]
    save_json(SOURCE_CONFIG, data, dry_run=dry_run)


def update_template_config(metadata, dry_run=False):
    data = load_json(TEMPLATE_CONFIG)
    app_info = data.setdefault("app_info", {})
    app_info["version"] = metadata["version"]
    app_info["release_date"] = metadata["release_date"]
    app_info["last_updated"] = metadata["last_updated"]
    save_json(TEMPLATE_CONFIG, data, dry_run=dry_run)


def replace_or_fail(text, pattern, replacement, description, flags=0):
    new_text, count = re.subn(pattern, replacement, text, flags=flags)
    if count == 0:
        raise RuntimeError(f"Could not update {description}")
    return new_text


def update_readme(metadata, dry_run=False):
    content = read_text(README_FILE)
    content = replace_or_fail(
        content,
        r"^# VPN Server Manager v[^\n]+",
        f"# VPN Server Manager v{metadata['version']}",
        "README version header",
        flags=re.MULTILINE,
    )
    write_text(README_FILE, content, dry_run=dry_run)


def update_installer(metadata, dry_run=False):
    content = read_text(INSTALLER_ISS)
    content = replace_or_fail(
        content,
        r'#define MyAppVersion "[^"]+"',
        f'#define MyAppVersion "{metadata["version"]}"',
        "installer version",
    )
    write_text(INSTALLER_ISS, content, dry_run=dry_run)


def update_env_example(metadata, dry_run=False):
    content = read_text(ENV_EXAMPLE)
    content = replace_or_fail(
        content,
        r"^APP_VERSION=.*$",
        f"APP_VERSION={metadata['version']}",
        "env.example APP_VERSION",
        flags=re.MULTILINE,
    )
    write_text(ENV_EXAMPLE, content, dry_run=dry_run)


def update_app_config(metadata, dry_run=False):
    content = read_text(APP_CONFIG)
    content = replace_or_fail(
        content,
        r'f\.write\("APP_VERSION=[^"\n]+\\n"\)',
        f'f.write("APP_VERSION={metadata["version"]}\\\\n")',
        "app/config.py minimal env APP_VERSION",
    )
    content = replace_or_fail(
        content,
        r"APP_VERSION = os\.getenv\('APP_VERSION', '[^']+'\)",
        f"APP_VERSION = os.getenv('APP_VERSION', '{metadata['version']}')",
        "app/config.py fallback APP_VERSION",
    )
    write_text(APP_CONFIG, content, dry_run=dry_run)


def update_app_init(metadata, dry_run=False):
    content = read_text(APP_INIT)
    content = replace_or_fail(
        content,
        r'"version": "[^"]+"',
        f'"version": "{metadata["version"]}"',
        "app/__init__.py fallback version",
    )
    content = replace_or_fail(
        content,
        r'"last_updated": "[^"]+"',
        f'"last_updated": "{metadata["last_updated"]}"',
        "app/__init__.py fallback last_updated",
    )
    write_text(APP_INIT, content, dry_run=dry_run)


def update_setup_py(metadata, dry_run=False):
    content = read_text(SETUP_PY)
    content = replace_or_fail(
        content,
        r"return config\.get\('app_info', \{\}\)\.get\('version', '[^']+'\)",
        f"return config.get('app_info', {{}}).get('version', '{metadata['version']}')",
        "setup.py config fallback version",
    )
    content = replace_or_fail(
        content,
        r"return '[^']+'",
        f"return '{metadata['version']}'",
        "setup.py hardcoded fallback version",
    )
    write_text(SETUP_PY, content, dry_run=dry_run)


def get_json_version(path):
    if not path.exists():
        return "MISSING"
    try:
        return load_json(path).get("app_info", {}).get("version", "N/A")
    except Exception:
        return "ERROR"


def get_regex_value(path, pattern):
    if not path.exists():
        return "MISSING"
    match = re.search(pattern, read_text(path), re.MULTILINE)
    return match.group(1) if match else "N/A"


def print_status():
    source = get_source_metadata()
    versions = [
        ("source", "config.json", source["version"]),
        ("template", "config/config.json.template", get_json_version(TEMPLATE_CONFIG)),
        ("readme", "README.md", get_regex_value(README_FILE, r"^# VPN Server Manager v([^\n]+)")),
        ("installer", "vpn-manager-installer.iss", get_regex_value(INSTALLER_ISS, r'#define MyAppVersion "([^"]+)"')),
        ("env", "env.example", get_regex_value(ENV_EXAMPLE, r"^APP_VERSION=(.+)$")),
        ("app_config", "app/config.py", get_regex_value(APP_CONFIG, r"APP_VERSION = os\.getenv\('APP_VERSION', '([^']+)'\)")),
        ("app_init", "app/__init__.py", get_regex_value(APP_INIT, r'"version": "([^"]+)"')),
        ("setup", "setup.py", get_regex_value(SETUP_PY, r"return config\.get\('app_info', \{\}\)\.get\('version', '([^']+)'\)")),
    ]

    print("[STATUS] VPN Server Manager version tracking")
    print("-" * 56)
    print(f"Source version:      {source['version']}")
    print(f"Release date:        {source['release_date']}")
    print(f"Last updated (ISO):  {source['last_updated']}")
    print("")

    mismatches = []
    for label, path, value in versions:
        marker = "OK" if value == source["version"] else "DIFF"
        print(f"{label:10} {marker:4} {value:10} {path}")
        if value != source["version"]:
            mismatches.append(path)

    if mismatches:
        print("")
        print("Out of sync files:")
        for path in mismatches:
            print(f"- {path}")
        print("")
        print("Run `python tools/update_version.py sync` to align derived files.")
    else:
        print("")
        print("All tracked version files are in sync.")


def sync_all(metadata, dry_run=False):
    set_source_metadata(metadata, dry_run=dry_run)
    update_template_config(metadata, dry_run=dry_run)
    update_readme(metadata, dry_run=dry_run)
    update_installer(metadata, dry_run=dry_run)
    update_env_example(metadata, dry_run=dry_run)
    update_app_config(metadata, dry_run=dry_run)
    update_app_init(metadata, dry_run=dry_run)
    update_setup_py(metadata, dry_run=dry_run)


def build_metadata(args):
    current = get_source_metadata()

    if args.command == "sync":
        version = args.version or current["version"]
        release_date = args.release_date or (today_release_date() if args.version else current["release_date"])
        last_updated = args.last_updated or (today_iso_date() if args.version else current["last_updated"])
    elif args.command == "bump":
        version = bump_semver(current["version"], args.part)
        release_date = args.release_date or today_release_date()
        last_updated = args.last_updated or today_iso_date()
    else:
        raise ValueError(f"Unsupported command for metadata build: {args.command}")

    parse_version(version)
    return {
        "version": version,
        "release_date": release_date,
        "last_updated": last_updated,
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Manage VPN Server Manager versions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show version tracking status")

    sync_parser = subparsers.add_parser("sync", help="Sync all tracked files from config.json")
    sync_parser.add_argument("version", nargs="?", help="Optional explicit version, e.g. 4.1.1")
    sync_parser.add_argument("--release-date", dest="release_date", help="DD.MM.YYYY")
    sync_parser.add_argument("--last-updated", dest="last_updated", help="YYYY-MM-DD")
    sync_parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")

    bump_parser = subparsers.add_parser("bump", help="Bump semantic version and sync all files")
    bump_parser.add_argument("part", choices=["major", "minor", "patch"])
    bump_parser.add_argument("--release-date", dest="release_date", help="DD.MM.YYYY")
    bump_parser.add_argument("--last-updated", dest="last_updated", help="YYYY-MM-DD")
    bump_parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print_status()
        return 0

    metadata = build_metadata(args)
    print(f"Target version:      {metadata['version']}")
    print(f"Target release date: {metadata['release_date']}")
    print(f"Target last updated: {metadata['last_updated']}")
    print("")
    sync_all(metadata, dry_run=getattr(args, "dry_run", False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
