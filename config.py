"""
Configuration for development and production environments.
"""
import os
from pathlib import Path

# Development mode
DEV_MODE = True

# Base paths
BASE_DIR = Path(__file__).parent
OLD_REPO_DIR = BASE_DIR.parent / 'VideoSnippets' if DEV_MODE else None

# Storage paths
UPLOAD_DIR = BASE_DIR / 'uploads'
LIBRARY_DIR = BASE_DIR / 'library'

# Import paths for development
if DEV_MODE and OLD_REPO_DIR:
    import sys
    # Add old repo to path for importing existing modules
    if OLD_REPO_DIR not in sys.path:
        sys.path.append(str(OLD_REPO_DIR))

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
LIBRARY_DIR.mkdir(exist_ok=True)
