#!/bin/bash

echo "🚀 Starting Full Pipeline..."

# ============================
# STEP 0: Move to project root
# ============================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit

# ============================
# STEP 1: Create venv if missing
# ============================
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# ============================
# STEP 2: Activate venv
# ============================
echo "🔧 Activating virtual environment..."
# Linux/macOS: source .venv/bin/activate
# Windows (Git Bash): source .venv/Scripts/activate
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "❌ Could not find venv activation script"
    exit 1
fi

# ============================
# STEP 3: Install dependencies
# ============================
echo "📥 Installing requirements..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# ============================
# STEP 4: Run Cura pipeline (OPTIONAL)
# ============================
# This step requires CuraEngine installed locally.
# G-code and behavioral references are already in the repo,
# so this step is ONLY needed to regenerate from STL files.
echo "🧩 Running Cura pipeline (optional — skip if CuraEngine not installed)..."
python slicer/cura_engine.py 2>/dev/null

if [ $? -ne 0 ]; then
    echo "⚠️  Cura pipeline skipped (CuraEngine not found — this is OK)"
    echo "   Pre-generated G-code files will be used instead."
fi

# ============================
# STEP 5: Run experiments
# ============================
echo "🧪 Running experiments..."
python main.py experiments/experiments_config.json

if [ $? -ne 0 ]; then
    echo "❌ Experiment execution failed"
    exit 1
fi

# ============================
# DONE
# ============================
echo "🎯 FULL PIPELINE COMPLETED SUCCESSFULLY"