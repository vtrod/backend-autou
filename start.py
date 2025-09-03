#!/usr/bin/env python3
import os
import sys
import uvicorn

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('PYTHONPATH', current_dir)

if __name__ == "__main__":
    from app.main import app
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
