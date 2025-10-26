#!/bin/bash
# Clear Python cache to force reimport of modules

echo "Clearing Python bytecode cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Cache cleared!"

echo "Restarting bot..."
pkill -9 python
sleep 1
python main.py

