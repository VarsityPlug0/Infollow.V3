import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Check if we're on Render
import os
if os.environ.get('RENDER'):
    print("Running on Render")
else:
    print("Not running on Render")

# Check for Python version environment variable
python_version = os.environ.get('PYTHON_VERSION')
if python_version:
    print(f"PYTHON_VERSION env var: {python_version}")
else:
    print("PYTHON_VERSION env var not set")