"""
XBRL Taxonomy Parser - A tool for parsing XBRL taxonomies and converting them to JSON.

This package provides tools to parse XBRL taxonomy files, extract their structure,
and convert the data to a more accessible JSON format.
"""

__version__ = "1.0.0"

from .parser import XBRLTaxonomyParser
from .writer import XBRLTaxonomyWriter
from .stats import XBRLTaxonomyStats
from .cli import parse_taxonomy

__all__ = [
    "XBRLTaxonomyParser",
    "XBRLTaxonomyWriter",
    "XBRLTaxonomyStats",
    "parse_taxonomy"
]
