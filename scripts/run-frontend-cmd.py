#!/usr/bin/env python3
"""
Cross-platform script to run frontend commands
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: run-frontend-cmd.py <command> [args...]")
        sys.exit(1)
    
    frontend_dir = Path(__file__).parent.parent / "dashboard" / "frontend"
    
    if not frontend_dir.exists():
        print("Frontend directory not found, skipping frontend command")
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    os.chdir(frontend_dir)
    
    if command == "test":
        cmd = ["npm", "run", "test:run"]
    elif command == "lint":
        cmd = ["npm", "run", "lint"] + args
    elif command == "format":
        cmd = ["npm", "run", "lint", "--", "--fix"]
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    result = subprocess.run(cmd, shell=os.name == "nt")
    # Exit with the same code as the command
    if result.returncode != 0:
        sys.exit(result.returncode)
    sys.exit(0)

if __name__ == "__main__":
    main()

