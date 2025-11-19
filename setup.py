"""Setup script for Baselinr."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from package
version = "0.1.0"

setup(
    name="baselinr",
    version=version,
    author="Baselinr Contributors",
    author_email="baselinr@example.com",
    description="Modern data profiling and drift detection framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/baselinrhq/baselinr",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docker"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",  # PostgreSQL driver
        "tabulate>=0.9.0",  # CLI table formatting
    ],
    extras_require={
        "snowflake": [
            "snowflake-sqlalchemy>=1.5.0",
            "snowflake-connector-python>=3.0.0",
        ],
        "dagster": [
            "dagster>=1.5.0",
            "dagster-webserver>=1.5.0",
            "dagster-postgres>=0.21.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
        "all": [
            "snowflake-sqlalchemy>=1.5.0",
            "snowflake-connector-python>=3.0.0",
            "dagster>=1.5.0",
            "dagster-webserver>=1.5.0",
            "dagster-postgres>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "baselinr=baselinr.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)

