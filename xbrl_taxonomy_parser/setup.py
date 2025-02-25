from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="xbrl_taxonomy_parser",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A parser for XBRL taxonomies that converts them to structured JSON",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/xbrl-taxonomy-parser",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "xbrl-taxonomy-parser=xbrl_taxonomy_parser.cli:main",
        ],
    },
)
