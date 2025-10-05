#!/usr/bin/env python3
"""Setup script for DevSync Bot — cross-platform, venv-aware installer."""

import os
import sys
import subprocess
from pathlib import Path
from textwrap import dedent

HERE = Path(__file__).resolve().parent
VENV_DIR = HERE / ".venv"

def run(cmd, desc=None, check=True, env=None):
    if desc:
        print(f"{desc}...")
    try:
        # Use list form to avoid shell differences; show stderr on failure
        subprocess.run(cmd, check=check, env=env)
        if desc:
            print(f"Complete: {desc}")
        return True
    except subprocess.CalledProcessError as e:
        if desc:
            print(f"Failed: {desc} (exit {e.returncode})")
        return False

def py_exe():
    # If we created a venv, prefer its interpreter
    vpy = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(vpy if vpy.exists() else sys.executable)

def pip(*args):
    return [py_exe(), "-m", "pip", *args]

def ensure_venv():
    if VENV_DIR.exists():
        print(f"🧪 Using existing virtualenv: {VENV_DIR}")
        return True
    print("🧪 Creating virtualenv .venv ...")
    ok = run([sys.executable, "-m", "venv", str(VENV_DIR)], "Create virtualenv")
    if not ok:
        print("⚠️ Could not create virtualenv; proceeding with system interpreter.")
    return ok

def ensure_pip():
    run([py_exe(), "-m", "ensurepip", "--upgrade"], "Ensure pip")
    run(pip("install", "--upgrade", "pip", "setuptools", "wheel"), "Upgrade pip/setuptools/wheel")

def install_main_requirements():
    req = HERE / "requirements.txt"
    if not req.exists():
        print("requirements.txt not found — skipping dependency install.")
        return True
    return run(pip("install", "-r", str(req)), "Install main dependencies")


def load_env_and_check():
    env_path = HERE / ".env"
    if not env_path.exists():
        print("\n.env file not found!")
        print("Please create a .env with required configuration (see README).")
        return False

    try:
        from dotenv import load_dotenv
    except ImportError:
        print("\nInstalling python-dotenv for env validation...")
        if not run(pip("install", "python-dotenv"), "Install python-dotenv"):
            print("Could not install python-dotenv — skipping validation.")
            return True  # don't hard fail
        from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path)

    required = {
        "Core": ["ANTHROPIC_API_KEY"],
        "Jira": ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
        "GitHub": ["GITHUB_TOKEN", "GITHUB_REPO"],
        "Slack (for bot)": ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET"],
    }

    print("\n📋 Checking configuration:")
    ok = True
    for category, keys in required.items():
        print(f"\n{category}:")
        for k in keys:
            v = os.getenv(k)
            if v:
                masked = (f"{v[:4]}...{v[-4:]}" if any(s in k for s in ("KEY", "TOKEN", "SECRET")) and len(v) > 8 else v)
                print(f"  {k}: {masked}")
            else:
                print(f"  {k}: NOT SET")
                if category != "Slack (for bot)":
                    ok = False
    if not ok:
        print("\nSome required variables are missing. Update your .env and re-run.")
    return ok

def print_banner():
    print(dedent("""
    ╔══════════════════════════════════════╗
    ║   🤖 DevSync Bot Setup Script        ║
    ║   Slack × GitHub × Jira Assistant    ║
    ╚══════════════════════════════════════╝
    """).strip())

def suggest_python_version():
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 13):
        print("⚠️ You are on Python 3.13 — some libs may not support it yet.")
        print("   If you hit build errors, try Python 3.11 or 3.12.")

def main():
    print_banner()

    if sys.version_info < (3, 8):
        print("Python 3.8+ required")
        sys.exit(1)

    print(f"Python {sys.version_info.major}.{sys.version_info.minor} detected")
    suggest_python_version()

    # 1) venv + pip
    created = ensure_venv()
    ensure_pip()

    # 2) deps
    if not install_main_requirements():
        print("\n⚠️ Failed to install main dependencies.")
        print(f"Try: {py_exe()} -m pip install -r requirements.txt")
        sys.exit(1)


    # 4) env + validation
    all_good = load_env_and_check()

    # 5) logs dir
    logs_dir = HERE / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        print("Created logs directory")

    print("\n" + "=" * 60)
    if all_good:
        print("\nSetup complete!")
    else:
        print("\nSetup incomplete — fix the missing env vars above.")
        # still print next steps

    # 6) Next steps
    print("\nNext steps:")
    print(f"1) Activate the virtualenv:\n   source {VENV_DIR}/bin/activate" if os.name != "nt" else
          f"   {VENV_DIR}\\Scripts\\activate")
    print("2) Run the Slack bot:\n   python slack_bot.py")
    print("3) Test components:\n   python test_components.py")
    print("\nIf Slack creds are not set yet:")
    print(" - Create a Slack app → enable Socket Mode")
    print(" - Scopes: app_mentions:read, channels:history, chat:write, im:history, users:read")
    print(" - Add tokens to .env and re-run this setup.\n")

    # Exit non-zero if env validation failed (helps CI)
    if not all_good:
        sys.exit(2)

if __name__ == "__main__":
    main()
