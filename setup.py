"""Packaging for Charterloom AI."""

from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent

setup(
    name="charterloom",
    version="1.2.0",
    description="Intelligent workflow and template recommender for custom project lifecycles",
    long_description=(ROOT / "README.md").read_text(encoding="utf8"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("tests",)),
    python_requires=">=3.10",
    install_requires=[line.strip() for line in (ROOT / "requirements.txt").read_text().splitlines()
                      if line.strip() and not line.startswith("#") and "pytest" not in line and "httpx" not in line],
    extras_require={"test": ["pytest>=8.0", "httpx>=0.27"]},
    entry_points={"console_scripts": ["charterloom=charterloom.cli:main"]},
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
