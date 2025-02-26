"""
Main entry point for the XBRL Taxonomy Parser when run as a module.

This allows running the parser using:
python -m xbrl_taxonomy_parser --base-dir /path/to/taxonomy --taxonomy-entry /path/to/entry-point.xsd --output-dir /path/to/output
"""

from .cli import main

if __name__ == "__main__":
    main()