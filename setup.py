"""Setup script for CodeReview AI."""

from __future__ import annotations

from setuptools import find_packages, setup

setup(
    name="codereview-ai",
    version="1.0.0",
    description="AI-powered Code Review Assistant for Python",
    author="Mani",
    author_email="myfamily9006@gmail.com",
    url="https://github.com/codereview-ai/codereview-ai",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "codereview-ai=src.cli:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
