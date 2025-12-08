#!/usr/bin/env python3
"""
Script to bump version in config template and installer.
Usage:
    python tools/bump_version.py --bump patch  # 4.0.10 -> 4.0.11
    python tools/bump_version.py --bump minor  # 4.0.10 -> 4.1.0
    python tools/bump_version.py --bump major  # 4.0.10 -> 5.0.0
    python tools/bump_version.py --version 4.2.0
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_TEMPLATE = os.path.join(BASE_DIR, 'config', 'config.json.template')
INSTALLER_ISS = os.path.join(BASE_DIR, 'vpn-manager-installer.iss')

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {path}")

def update_installer_version(new_version):
    """Update version in Inno Setup installer script."""
    if not os.path.exists(INSTALLER_ISS):
        print(f"Warning: Installer not found at {INSTALLER_ISS}")
        return False
    
    with open(INSTALLER_ISS, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update #define MyAppVersion
    content = re.sub(
        r'#define MyAppVersion "[^"]*"',
        f'#define MyAppVersion "{new_version}"',
        content
    )
    
    # Update comment version
    content = re.sub(
        r'; Version \d+\.\d+\.\d+',
        f'; Version {new_version}',
        content
    )
    
    with open(INSTALLER_ISS, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {INSTALLER_ISS}")
    return True

def parse_version(version_str):
    return list(map(int, version_str.split('.')))

def bump_version(current_version, part):
    major, minor, patch = parse_version(current_version)
    
    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    elif part == 'patch':
        patch += 1
        
    return f"{major}.{minor}.{patch}"

def update_template(new_version, new_date=None, developer=None):
    if not os.path.exists(CONFIG_TEMPLATE):
        print(f"Error: Template not found at {CONFIG_TEMPLATE}")
        sys.exit(1)
        
    data = load_json(CONFIG_TEMPLATE)
    
    # Update version
    current_version = data.get('app_info', {}).get('version', '0.0.0')
    print(f"Current version: {current_version}")
    print(f"New version:     {new_version}")
    
    if 'app_info' not in data:
        data['app_info'] = {}
        
    data['app_info']['version'] = new_version
    
    # Update dates
    today = datetime.now().strftime('%d.%m.%Y')
    iso_today = datetime.now().strftime('%Y-%m-%d')
    
    if new_date:
        data['app_info']['release_date'] = new_date
    else:
        data['app_info']['release_date'] = today
        
    data['app_info']['last_updated'] = iso_today
    
    # Update developer if provided
    if developer:
        data['app_info']['developer'] = developer
        
    save_json(CONFIG_TEMPLATE, data)
    
    # Also update installer
    update_installer_version(new_version)
    
    return current_version

def main():
    parser = argparse.ArgumentParser(description='Bump version in config template')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--bump', choices=['major', 'minor', 'patch'], help='Part of version to bump')
    group.add_argument('--version', help='Set specific version (e.g. 4.1.0)')
    
    parser.add_argument('--release-date', help='Set specific release date (DD.MM.YYYY)')
    parser.add_argument('--developer', help='Update developer name')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
    
    args = parser.parse_args()
    
    # Load current config
    if not os.path.exists(CONFIG_TEMPLATE):
        print(f"Error: Template not found at {CONFIG_TEMPLATE}")
        sys.exit(1)
        
    current_data = load_json(CONFIG_TEMPLATE)
    current_version = current_data.get('app_info', {}).get('version', '0.0.0')
    
    # Determine new version
    if args.version:
        new_version = args.version
    else:
        new_version = bump_version(current_version, args.bump)
        
    if args.dry_run:
        print(f"[DRY RUN] Would update version from {current_version} to {new_version}")
        if args.developer:
            print(f"[DRY RUN] Would set developer to: {args.developer}")
        return
        
    update_template(new_version, args.release_date, args.developer)
    print("✅ Version bumped successfully!")

if __name__ == '__main__':
    main()
