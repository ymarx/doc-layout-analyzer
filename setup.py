#!/usr/bin/env python3
"""
Setup Script for Document Layout Analyzer
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ""

# Read requirements
req_path = Path(__file__).parent / "requirements.txt"
requirements = []
if req_path.exists():
    requirements = [
        line.strip() for line in req_path.read_text().splitlines()
        if line.strip() and not line.startswith('#') and ';' not in line
    ]

setup(
    name="doc-layout-analyzer",
    version="1.0.0",
    author="Document Analysis Team",
    author_email="team@company.com",
    description="CPU/GPU dual-mode document layout analysis system with Korean language support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/company/doc-layout-analyzer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "gpu": [
            "torch>=2.1.0",
            "torchvision>=0.16.0",
            "paddlepaddle-gpu>=2.5.2",
        ],
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
        ],
        "docs": [
            "sphinx>=7.1.2",
            "sphinx-rtd-theme>=1.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "doc-analyzer=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "data/models/*"],
    },
)