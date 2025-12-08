#!/usr/bin/env python3
"""
Script to sync local config.json with the template.
Usage:
    python tools/update_version.py status
    python tools/update_version.py sync
"""

import os
import sys
import json
import argparse
import shutil

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_TEMPLATE = os.path.join(BASE_DIR, 'config', 'config.json.template')
CONFIG_LOCAL = os.path.join(BASE_DIR, 'config.json')

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {path}")

def get_version(data):
    if not data: return "N/A"
    return data.get('app_info', {}).get('version', 'N/A')

def show_status():
    print("[STATUS] VERSION INFO")
    print("-" * 30)
    
    # Template
    tpl_data = load_json(CONFIG_TEMPLATE)
    tpl_ver = get_version(tpl_data)
    tpl_date = tpl_data.get('app_info', {}).get('release_date', 'N/A') if tpl_data else 'N/A'
    
    print(f"📄 Template (Source of Truth):")
    print(f"   Path:    config/config.json.template")
    print(f"   Version: {tpl_ver}")
    print(f"   Date:    {tpl_date}")
    print("")
    
    # Local
    local_data = load_json(CONFIG_LOCAL)
    local_ver = get_version(local_data)
    
    print(f"💻 Local Config:")
    print(f"   Path:    config.json")
    print(f"   Version: {local_ver}")
    
    if tpl_ver == local_ver:
        print("\n✅ SYNCED")
    else:
        print(f"\n⚠️  OUT OF SYNC (Template: {tpl_ver} != Local: {local_ver})")
        print("   Run 'python tools/update_version.py sync' to update local config.")

def sync_config():
    print("[SYNC] Synchronizing local config with template...")
    
    if not os.path.exists(CONFIG_TEMPLATE):
        print(f"❌ Error: Template not found at {CONFIG_TEMPLATE}")
        return
        
    tpl_data = load_json(CONFIG_TEMPLATE)
    if not tpl_data:
        print("❌ Error: Failed to load template")
        return
        
    # If local doesn't exist, create it from template
    if not os.path.exists(CONFIG_LOCAL):
        print("Local config not found. Creating from template...")
        shutil.copy2(CONFIG_TEMPLATE, CONFIG_LOCAL)
        print(f"✅ Created {CONFIG_LOCAL}")
        return

    # If exists, update only version info
    local_data = load_json(CONFIG_LOCAL)
    if not local_data:
        print("❌ Error: Failed to load local config")
        return
        
    # Update app_info from template
    if 'app_info' not in local_data:
        local_data['app_info'] = {}
        
    # Preserve local settings if needed, but here we strictly sync version info
    local_data['app_info'] = tpl_data['app_info']
    
    # Sync service_urls (optional, usually good to sync)
    if 'service_urls' in tpl_data:
        local_data['service_urls'] = tpl_data['service_urls']
        
    save_json(CONFIG_LOCAL, local_data)
    print(f"✅ Local config updated to version {get_version(tpl_data)}")

def main():
    parser = argparse.ArgumentParser(description='Manage version synchronization')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Status command
    subparsers.add_parser('status', help='Show current version status')
    
    # Sync command
    subparsers.add_parser('sync', help='Sync local config with template')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        show_status()
    elif args.command == 'sync':
        sync_config()

if __name__ == '__main__':
    main()
