#!/usr/bin/env python3
"""
Setup script for Prospector application
"""

import os
import sys

def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        print("Creating .env file...")
        with open('.env', 'w') as f:
            f.write("""# Prospector Configuration
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=prospector_secret_key_12345
FLASK_ENV=development
""")
        print("Created .env file. Please edit it and add your OpenAI API key.")
        return False
    return True

def check_requirements():
    """Check if requirements are installed"""
    try:
        import flask
        import openai
        return True
    except ImportError as e:
        print(f"Missing required packages: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    print("🔍 Setting up Prospector...")
    
    if not check_requirements():
        return 1
    
    if not create_env_file():
        return 1
    
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file and add your OpenAI API key")
    print("2. Run: python app.py")
    print("3. Open: http://localhost:5000")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
