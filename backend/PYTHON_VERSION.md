# Python Version Compatibility

## Recommended Versions

**Recommended: Python 3.11 or 3.12**

These versions have the best compatibility with all dependencies including:
- Pillow (image processing)
- PyTorch (ML models)
- Transformers (HuggingFace)
- Other ML/AI libraries

## Python 3.14 Compatibility Issues

Python 3.14 is very new and some packages may not support it yet:
- Pillow 10.2.0 doesn't support Python 3.14
- Some other packages may have build issues

We've updated requirements to use newer versions where possible, but **Python 3.11 or 3.12 is strongly recommended**.

## Using a Specific Python Version

### On macOS (with Homebrew)

```bash
# Install Python 3.11
brew install python@3.11

# Create venv with specific version
python3.11 -m venv app/venv
source app/venv/bin/activate
pip install -r requirements.txt
```

### On macOS (with pyenv)

```bash
# Install Python 3.11
pyenv install 3.11.9

# Set local version
cd backend
pyenv local 3.11.9

# Create venv
python -m venv app/venv
source app/venv/bin/activate
pip install -r requirements.txt
```

### Check Your Python Version

```bash
python3 --version
```

## Docker Alternative

If you're having Python version issues, consider using Docker instead:

```bash
cd backend
docker compose up -d
```

Docker uses Python 3.11 which has full compatibility with all dependencies.
