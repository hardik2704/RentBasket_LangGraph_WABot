#!/usr/bin/env python3
"""
Sync conversation logs from Render backend to local logs/ directory.
"""
import os
import sys
import requests
import time
import argparse
from dotenv import load_dotenv

# Ensure we're in the right path for imports/env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Config (Overrides from .env if present)
RENDER_URL = os.getenv("RENDER_URL", "https://rentbasket-wabot.onrender.com")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "12345")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

def sync_logs(quiet=False):
    if not quiet:
        print(f"🔄 Syncing logs from: {RENDER_URL}")
        print(f"📁 Target directory: {LOGS_DIR}")
    
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        if not quiet:
            print(f"✨ Created logs/ directory.")

    try:
        # Get list of logs
        list_url = f"{RENDER_URL}/logs?secret={VERIFY_TOKEN}"
        if not quiet:
            print(f"🔍 Fetching file list...")
        
        r = requests.get(list_url, timeout=10)
        
        if r.status_code == 403:
            print("❌ Access Forbidden: Check your VERIFY_TOKEN.")
            return
        elif r.status_code == 404:
            print("❌ Endpoints not found: Ensure the latest code is deployed on Render.")
            return
            
        r.raise_for_status()
        
        data = r.json()
        files = data.get("files", [])
        
        if not files:
            if not quiet:
                print("📭 No log files found on server.")
            return

        if not quiet:
            print(f"📊 Found {len(files)} log files.")
        
        downloaded_count = 0
        skipped_count = 0
        
        for f in files:
            file_name = f["name"]
            remote_size = f["size_bytes"]
            local_path = os.path.join(LOGS_DIR, file_name)
            
            # Check if file exists and has the same size
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                if local_size == remote_size:
                    skipped_count += 1
                    continue
            
            # Download file
            if not quiet:
                print(f"  📥 Downloading {file_name} ({remote_size} bytes)...")
            download_url = f"{RENDER_URL}/logs/{file_name}?secret={VERIFY_TOKEN}"
            fr = requests.get(download_url, timeout=10)
            fr.raise_for_status()
            
            with open(local_path, "wb") as lf:
                lf.write(fr.content)
            downloaded_count += 1

        if not quiet or downloaded_count > 0:
            print(f"✅ Sync Complete! (📥 {downloaded_count} new, ⏭️ {skipped_count} skipped)")
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not reach {RENDER_URL}")
    except Exception as e:
        print(f"❌ Error during sync: {e}")

def main():
    parser = argparse.ArgumentParser(description="Sync Render logs locally.")
    parser.add_argument("--watch", action="store_true", help="Keep syncing in a loop.")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between syncs (default: 60).")
    args = parser.parse_args()

    if args.watch:
        print(f"👀 Watch mode active. Syncing every {args.interval}s...")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                sync_logs(quiet=True)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 Stopped watching.")
    else:
        sync_logs()

if __name__ == "__main__":
    main()
