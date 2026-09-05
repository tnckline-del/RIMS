"""
Purpose:
    Provide the initial executable framework for the Retirement Income
    Management System (RIMS).

Responsibilities:
    - Verify the supported Python version.
    - Establish the RIMS project directory structure.
    - Provide a simple command-line entry point.
    - Report the current RIMS build environment.

Dependencies:
    Python standard library only.

Revision History:
    0.2.0 - Initial application build framework.

Author:
    RIMS Development Team
"""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path


PROJECT_VERSION = "0.2.0"
MINIMUM_PYTHON_VERSION = (3, 12)

PROJECT_DIRECTORIES = (
    "src",
    "tests",
    "docs",
    "data",
    "data/imports",
    "data/snapshots",
    "data/archive",
    "output",
)


def get_project_root() -> Path:
    """Return the root directory of the RIMS project."""
    return Path(__file__).resolve().parent


def verify_python_version() -> None:
    """Verify that the running Python version meets RIMS requirements."""
    current_version = sys.version_info[:2]

    if current_version < MINIMUM_PYTHON_VERSION:
        required = ".".join(str(value) for value in MINIMUM_PYTHON_VERSION)
        current = ".".join(str(value) for value in current_version)

        raise RuntimeError(
            f"RIMS requires Python {required} or newer. "
            f"Current Python version is {current}."
        )


def create_project_directories(project_root: Path) -> list[Path]:
    """Create required RIMS directories and return the created paths."""
    directories: list[Path] = []

    for relative_directory in PROJECT_DIRECTORIES:
        directory = project_root / relative_directory
        directory.mkdir(parents=True, exist_ok=True)
        directories.append(directory)

    return directories


def display_build_information(project_root: Path) -> None:
    """Display the current RIMS build environment."""
    python_version = platform.python_version()

    print()
    print("Retirement Income Management System (RIMS)")
    print("=" * 48)
    print(f"RIMS version:    {PROJECT_VERSION}")
    print(f"Python version:  {python_version}")
    print(f"Project root:    {project_root}")
    print("Build status:    READY")
    print()


def run_build() -> int:
    """Execute the RIMS build framework."""
    verify_python_version()

    project_root = get_project_root()
    create_project_directories(project_root)
    display_build_information(project_root)

    return 0


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Initialize and verify the RIMS application framework."
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"RIMS {PROJECT_VERSION}",
    )

    return parser.parse_args()


def main() -> int:
    """Run the RIMS application."""
    parse_arguments()
    return run_build()


if __name__ == "__main__":
    sys.exit(main())