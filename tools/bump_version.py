#!/usr/bin/env python3
"""Backward-compatible wrapper around tools/update_version.py."""

import argparse
import sys

from update_version import main as update_version_main


def build_parser():
    parser = argparse.ArgumentParser(description="Compatibility wrapper for version bumping")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bump", choices=["major", "minor", "patch"], help="Part of version to bump")
    group.add_argument("--version", help="Set specific version (e.g. 4.1.1)")
    parser.add_argument("--release-date", dest="release_date", help="DD.MM.YYYY")
    parser.add_argument("--last-updated", dest="last_updated", help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    return parser


def main():
    args = build_parser().parse_args()

    forwarded_args = []
    if args.version:
        forwarded_args = ["sync", args.version]
    else:
        forwarded_args = ["bump", args.bump]

    if args.release_date:
        forwarded_args.extend(["--release-date", args.release_date])
    if args.last_updated:
        forwarded_args.extend(["--last-updated", args.last_updated])
    if args.dry_run:
        forwarded_args.append("--dry-run")

    return update_version_main(forwarded_args)


if __name__ == "__main__":
    sys.exit(main())
