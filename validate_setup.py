#!/usr/bin/env python3
"""
Setup validation script for Binance Arbitrage Backend
Checks for common configuration and dependency issues
"""

import os
import sys

def check_file_exists(filename, description):
    """Check if a file exists"""
    if os.path.exists(filename):
        print(f"✅ {description}: {filename}")
        return True
    else:
        print(f"❌ {description}: {filename} not found")
        return False

def check_env_config():
    """Check environment configuration"""
    print("\n📋 Checking Environment Configuration:")
    
    if not check_file_exists(".env", "Environment file"):
        print("   💡 Run: cp .env.example .env")
        return False
    
    # Check critical env vars
    try:
        with open(".env", "r") as f:
            content = f.read()
            
        issues = []
        if "your_binance_api_key_here" in content:
            issues.append("BINANCE_API_KEY not configured")
        if "your_binance_secret_key_here" in content:
            issues.append("BINANCE_SECRET_KEY not configured")
            
        if issues:
            print("❌ Environment configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ Environment variables appear to be configured")
            return True
            
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def check_python_version():
    """Check Python version"""
    print("\n🐍 Checking Python Version:")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (requires Python 3.8+)")
        return False

def check_required_files():
    """Check if all required files exist"""
    print("\n📁 Checking Required Files:")
    
    required_files = [
        ("config.py", "Configuration module"),
        ("models.py", "Data models"),
        ("arbitrage_executor.py", "Execution engine"),
        ("main.py", "Main API server"),
        ("requirements.txt", "Dependencies list"),
        (".env.example", "Environment template"),
        ("README.md", "Documentation"),
        ("start_backend.sh", "Startup script")
    ]
    
    all_exist = True
    for filename, description in required_files:
        if not check_file_exists(filename, description):
            all_exist = False
    
    return all_exist

def main():
    """Run all validation checks"""
    print("🔍 Binance Arbitrage Backend - Setup Validation")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_required_files),
        ("Environment Config", check_env_config),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        if check_func():
            passed += 1
    
    print(f"\n📊 Validation Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Setup validation successful!")
        print("\nNext steps:")
        print("1. Install dependencies: pip3 install -r requirements.txt")
        print("2. Configure your API keys in .env file")
        print("3. Start the server: ./start_backend.sh")
    else:
        print("\n⚠️  Please fix the issues above before proceeding")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())