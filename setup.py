from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup

PROJECT_ROOT = Path(__file__).resolve().parent
README = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

setup(
    name="jalali-calendar-erpnext",
    version="0.2.0",
    description="Jalali calendar integration for ERPNext/Frappe environments",
    long_description=README,
    long_description_content_type="text/markdown",
    author="OpenAI",
    author_email="support@example.com",
    url="https://github.com/openai/new-jalali-calendar-for-erpnext",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "frappe>=14.0.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Framework :: Frappe",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Persian",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Office/Business",
    ],
)
