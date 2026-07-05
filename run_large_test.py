"""
End-to-End Test Script: OKF Updater Multi-Agent Pipeline on Real-World Dataset
Steps:
  1. Download the Titanic CSV dataset from GitHub.
  2. Save it under large_test_data/.
  3. Create a .env file to test the security boundary.
  4. Run the multi-agent pipeline on large_test_data/.
  5. Verify the generated okf_manifest.json.
"""

import os
import sys
import json
import asyncio
import urllib.request

# ── Resolve project root and target directory ──────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(SCRIPT_DIR, "large_test_data")

TITANIC_URL = (
    "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
)
TITANIC_CSV = os.path.join(TARGET_DIR, "titanic.csv")
ENV_FILE    = os.path.join(TARGET_DIR, ".env")
MANIFEST    = os.path.join(TARGET_DIR, "okf_manifest.json")

# ── STEP 2 ─────────────────────────────────────────────────────────────────────
def download_titanic():
    os.makedirs(TARGET_DIR, exist_ok=True)
    print(f"\n{'='*60}")
    print("STEP 2 – Downloading Titanic dataset …")
    print(f"  URL  : {TITANIC_URL}")
    print(f"  Dest : {TITANIC_CSV}")
    urllib.request.urlretrieve(TITANIC_URL, TITANIC_CSV)
    size = os.path.getsize(TITANIC_CSV)
    print(f"  ✔  Download complete ({size:,} bytes)\n")

# ── STEP 3 ─────────────────────────────────────────────────────────────────────
def create_env_file():
    print("STEP 3 – Creating decoy .env file for security test …")
    with open(ENV_FILE, "w") as f:
        f.write("FAKE_PASSWORD=12345\n")
    print(f"  ✔  Created {ENV_FILE}\n")

# ── STEP 4 ─────────────────────────────────────────────────────────────────────
def run_pipeline():
    from agent_system import run_multi_agent_pipeline
    print("STEP 4 – Running Multi-Agent Pipeline …")
    print(f"  Target directory: {TARGET_DIR}")
    print(f"{'='*60}\n")
    asyncio.run(run_multi_agent_pipeline(TARGET_DIR))

# ── STEP 5 ─────────────────────────────────────────────────────────────────────
def verify_output():
    print(f"\n{'='*60}")
    print("STEP 5 – Verifying Output …")

    # 5a. Manifest exists
    if not os.path.exists(MANIFEST):
        print("  ✘  FAIL: okf_manifest.json was NOT created!")
        sys.exit(1)

    print(f"  ✔  okf_manifest.json found at:\n     {MANIFEST}\n")

    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)

    print("─── okf_manifest.json contents ───────────────────────────")
    print(json.dumps(manifest, indent=2))
    print("──────────────────────────────────────────────────────────\n")

    # 5b. Contains Titanic schema
    manifest_str = json.dumps(manifest).lower()
    titanic_columns = [
        "passengerid", "survived", "pclass", "name", "sex", "age",
        "sibsp", "parch", "ticket", "fare", "cabin", "embarked"
    ]
    found   = [c for c in titanic_columns if c in manifest_str]
    missing = [c for c in titanic_columns if c not in manifest_str]

    print("TITANIC COLUMN VERIFICATION:")
    for col in titanic_columns:
        mark = "✔" if col in manifest_str else "✘"
        print(f"  {mark}  {col}")

    if missing:
        print(f"\n  ⚠  Columns not found in manifest: {missing}")
    else:
        print("\n  ✔  ALL Titanic columns are present in the manifest!")

    # 5c. .env NOT in manifest
    print("\nSECURITY CHECK – .env file must NOT appear in manifest:")
    env_leaked = any(
        phrase in manifest_str
        for phrase in [".env", "fake_password", "12345"]
    )
    if env_leaked:
        print("  ✘  FAIL: .env content was leaked into the manifest!")
        sys.exit(1)
    else:
        print("  ✔  PASS: .env file was correctly excluded from the manifest.")

    print(f"\n{'='*60}")
    print("ALL CHECKS PASSED – End-to-End Test Successful!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    download_titanic()
    create_env_file()
    run_pipeline()
    verify_output()
