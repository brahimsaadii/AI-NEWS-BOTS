#!/usr/bin/env python3
"""
Quick verification that all packages are installed correctly.
"""

def check_packages():
    """Check if all required packages are installed."""
    packages = [
        'telegram',
        'feedparser', 
        'requests',
        'openai',
        'apscheduler',
        'yaml',
        'dotenv'
    ]
    
    print("📦 Checking installed packages...")
    all_good = True
    
    for package in packages:
        try:
            if package == 'yaml':
                import yaml
                print(f"✅ {package} (PyYAML)")
            elif package == 'dotenv':
                import dotenv
                print(f"✅ {package} (python-dotenv)")
            else:
                __import__(package)
                print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    print("🔍 News Tweet Bots - Package Verification\n")
    
    if check_packages():
        print("\n🎉 All packages are installed correctly!")
        print("You can now run: python main.py")
    else:
        print("\n❌ Some packages are missing!")
        print("Please run: pip install -r requirements.txt")
