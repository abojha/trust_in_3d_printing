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
source .venv/Scripts/activate

# ============================
# STEP 3: Install dependencies
# ============================
echo "📥 Installing requirements..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# ============================
# STEP 4: Run Cura pipeline
# ============================
echo "🧩 Running Cura pipeline..."
python slicer/cura_engine.py

if [ $? -ne 0 ]; then
    echo "❌ Cura pipeline failed"
    exit 1
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