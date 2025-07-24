#!/usr/bin/env python3
"""
Startup script for the converted API server
"""
import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Ensure we're in the backend directory for correct database path resolution
os.chdir(backend_dir)
print(f"📁 Working directory: {os.getcwd()}")

if __name__ == "__main__":
    try:
        # Import and run the API
        from app.api.api import app
        import uvicorn
        
        print("🚀 Starting converted API server from backend directory...")
        print(f"🗄️  Expected database location: {os.path.join(backend_dir, 'indexing_qa.db')}")
        
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        import traceback
        traceback.print_exc() 