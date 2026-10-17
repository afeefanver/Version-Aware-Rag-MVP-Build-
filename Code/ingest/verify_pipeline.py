"""
Verification script for the Version-Aware RAG ingestion pipeline.
Confirms that all components are properly installed and can be imported.
"""

import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check that we're using a compatible Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"ERROR: Python {version.major}.{version.minor} is not supported. Need Python 3.8+")
        return False
    print(f"PASS: Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True


def check_virtual_environment():
    """Check if we're in the expected virtual environment."""
    # Check if we can find the .venv directory
    venv_path = Path("../.venv")
    if venv_path.exists():
        print("PASS: Virtual environment directory found")
        return True
    else:
        print("WARN: Virtual environment directory not found at ../.venv")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        ('sentence-transformers', 'sentence_transformers'),
        ('qdrant-client', 'qdrant_client'),
        ('python-frontmatter', 'frontmatter'),  # Special case: package name != import name
        ('numpy', 'numpy')
    ]

    missing = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"PASS: {package_name}")
        except ImportError:
            print(f"FAIL: {package_name} (not installed)")
            missing.append(package_name)

    return len(missing) == 0


def check_project_structure():
    """Check if the expected project structure exists."""
    expected_dirs = [
        '../data',
        '../data/policies',
        '../ingest',
        '../retrieval',
        '../generation',
        '../conflicts',
        '../eval',
        '../app'
    ]

    missing = []
    for dir_path in expected_dirs:
        if Path(dir_path).exists():
            print(f"PASS: {dir_path}")
        else:
            print(f"FAIL: {dir_path} (missing)")
            missing.append(dir_path)

    return len(missing) == 0


def check_manifest():
    """Check if the manifest file exists and is valid."""
    manifest_path = Path("../data/manifest.json")
    if not manifest_path.exists():
        print("FAIL: Manifest file not found at ../data/manifest.json")
        return False

    try:
        import json
        with open(manifest_path, 'r') as f:
            data = json.load(f)

        if 'documents' not in data:
            print("FAIL: Manifest missing 'documents' key")
            return False

        print(f"PASS: Manifest file valid - contains {len(data['documents'])} documents")
        return True
    except json.JSONDecodeError as e:
        print(f"FAIL: Manifest file contains invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Error reading manifest: {e}")
        return False


def check_ingestion_modules():
    """Check if ingestion modules can be imported."""
    # Add ingest directory to path
    sys.path.insert(0, str(Path("../ingest").resolve()))

    modules = [
        'parsers',
        'chunker',
        'registry',
        'embedder',
        'pipeline',
        'utils'
    ]

    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"PASS: {module}")
        except Exception as e:
            print(f"FAIL: {module} - {e}")
            failed.append((module, str(e)))

    return len(failed) == 0


def main():
    """Run all verification checks."""
    print("Version-Aware RAG Ingestion Pipeline Verification")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Manifest File", check_manifest),
        ("Ingestion Modules", check_ingestion_modules)
    ]

    passed = 0
    total = len(checks)

    for name, check_func in checks:
        print(f"\n{name}:")
        if check_func():
            passed += 1
        print()  # Extra spacing

    print("=" * 50)
    print(f"Results: {passed}/{total} checks passed")

    if passed == total:
        print("SUCCESS: All checks passed! The ingestion pipeline is ready to use.")
        print("\nNext steps:")
        print("1. To install missing dependencies: pip install sentence-transformers qdrant-client")
        print("2. To start ingestion: python -m ingest.pipeline (see pipeline.py for usage)")
        print("3. Proceed to Phase 3: Version-aware retrieval")
        return True
    else:
        print("FAILURE: Some checks failed. Please address the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)