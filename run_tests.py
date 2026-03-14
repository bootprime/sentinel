"""
Sentinel Testing Suite Runner
Lightweight script to run all tests with proper configuration
"""

import subprocess
import sys
import os

def run_tests():
    """Run all Sentinel unit tests"""
    
    print("=" * 60)
    print("🧪 Sentinel Testing Suite")
    print("=" * 60)
    
    # Set PYTHONPATH
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.environ['PYTHONPATH'] = project_root
    
    print(f"\n📁 Project Root: {project_root}")
    print(f"🐍 Python Path: {os.environ['PYTHONPATH']}\n")
    
    # Simple test command without coverage (works without pytest-cov)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/",
        "-v",
        "--tb=short"
    ]
    
    print(f"🚀 Running: {' '.join(cmd)}\n")
    print("=" * 60)
    
    # Run tests
    result = subprocess.run(cmd, cwd=project_root)
    
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        print(f"Exit code: {result.returncode}")
    print("=" * 60)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())
