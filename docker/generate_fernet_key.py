#!/usr/bin/env python3
"""
Generate a Fernet key for Airflow.

Usage:
    python generate_fernet_key.py

This will output a Fernet key that can be used in docker-compose.yml
for the AIRFLOW__CORE__FERNET_KEY environment variable.
"""

try:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    print(key.decode())
except ImportError:
    print("Error: cryptography module not installed.")
    print("Install it with: pip install cryptography")
    print("\nAlternatively, you can use this placeholder (NOT for production):")
    print("your-fernet-key-here-change-in-production")
    exit(1)

