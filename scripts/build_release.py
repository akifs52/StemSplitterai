"""
Build & Release automation script for StemSplitAI.

Usage:
    python scripts/build_release.py          # full build
    python scripts/build_release.py --skip-pyinstaller   # skip PyInstaller, only Inno Setup + latest.json
    python scripts/build_release.py --json-only          # only regenerate latest.json

Steps:
    1. Read version from version.py
    2. Run PyInstaller (StemSplitAI.spec)
    3. Patch Inno Setup .iss with current version
    4. Run Inno Setup Compiler (iscc)
    5. Compute SHA256 of the resulting setup exe
    6. Generate / update latest.json
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

# ── Paths ──────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(ROOT, "version.py")
ISS_FILE = os.path.join(ROOT, "installer", "stemsplitai.iss")
SPEC_FILE = os.path.join(ROOT, "StemSplitAI.spec")
DIST_DIR = os.path.join(ROOT, "dist")
LATEST_JSON = os.path.join(ROOT, "latest.json")


def read_version() -> str:
    """Extract APP_VERSION from version.py."""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', line)
            if m:
                return m.group(1)
    raise RuntimeError("APP_VERSION not found in version.py")


def read_github_url() -> str:
    """Extract APP_URL from version.py."""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r'APP_URL\s*=\s*["\']([^"\']+)["\']', line)
            if m:
                return m.group(1)
    return "https://github.com/akifs52/StemSplitterai"


def sha256_file(path: str) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_iss_version(version: str):
    """Update #define MyAppVersion in the .iss file."""
    with open(ISS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r'(#define\s+MyAppVersion\s+")[^"]*(")',
        rf'\g<1>{version}\g<2>',
        content,
    )
    with open(ISS_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Patched ISS version → {version}")


def run_pyinstaller():
    """Run PyInstaller with the .spec file."""
    print("\n═══ Step 1: PyInstaller ═══")
    cmd = [sys.executable, "-m", "PyInstaller", SPEC_FILE, "--noconfirm"]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("  ✗ PyInstaller failed!")
        sys.exit(1)
    print("  ✓ PyInstaller complete")


def find_iscc() -> str:
    """Find the Inno Setup compiler (iscc.exe)."""
    # Common install locations
    candidates = [
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c

    print("  ✗ ISCC.exe not found! Install Inno Setup 6 from https://jrsoftware.org/isinfo.php")
    print("    Or add iscc to your PATH.")
    sys.exit(1)


def run_inno_setup(version: str):
    """Compile the Inno Setup installer."""
    print("\n═══ Step 2: Inno Setup ═══")
    patch_iss_version(version)
    iscc = find_iscc()
    cmd = [iscc, ISS_FILE]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("  ✗ Inno Setup compilation failed!")
        sys.exit(1)
    print("  ✓ Inno Setup complete")


def generate_latest_json(version: str, setup_path: str):
    """Generate latest.json with SHA256 hash."""
    print("\n═══ Step 3: latest.json ═══")
    digest = sha256_file(setup_path)
    filename = os.path.basename(setup_path)
    github_url = read_github_url()
    download_url = f"{github_url}/releases/download/v{version}/{filename}"

    data = {
        "version": version,
        "url": download_url,
        "sha256": digest,
        "notes": f"StemSplitAI v{version}",
        "min_version": "1.0.0",
    }

    with open(LATEST_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  ✓ latest.json generated")
    print(f"    Version:  {version}")
    print(f"    URL:      {download_url}")
    print(f"    SHA256:   {digest}")
    print(f"    File:     {setup_path}")
    file_size_mb = os.path.getsize(setup_path) / (1024 * 1024)
    print(f"    Size:     {file_size_mb:.1f} MB")


def main():
    args = sys.argv[1:]
    version = read_version()
    print(f"StemSplitAI Build Script — v{version}")
    print("=" * 50)

    setup_filename = f"StemSplitAI-Setup-{version}.exe"
    setup_path = os.path.join(DIST_DIR, setup_filename)

    if "--json-only" in args:
        if not os.path.isfile(setup_path):
            print(f"  ✗ Setup file not found: {setup_path}")
            print("    Run a full build first.")
            sys.exit(1)
        generate_latest_json(version, setup_path)
        print("\n✓ Done (json-only mode)")
        return

    if "--skip-pyinstaller" not in args:
        run_pyinstaller()
    else:
        print("\n  ⏭  Skipping PyInstaller (--skip-pyinstaller)")

    run_inno_setup(version)

    if not os.path.isfile(setup_path):
        print(f"\n  ✗ Expected setup file not found: {setup_path}")
        print("    Check Inno Setup output settings.")
        sys.exit(1)

    generate_latest_json(version, setup_path)

    print("\n" + "=" * 50)
    print(f"✓ Build complete!")
    print(f"\nNext steps:")
    print(f"  1. Test the installer: {setup_path}")
    print(f"  2. Create a GitHub Release tagged 'v{version}'")
    print(f"  3. Upload {setup_filename} to the release")
    print(f"  4. Commit and push latest.json to the main branch")


if __name__ == "__main__":
    main()
