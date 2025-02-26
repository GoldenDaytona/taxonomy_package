"""
Main entry point for the XBRL Taxonomy Parser with optional command-line arguments.

This allows running the parser in two ways:
1. With defaults: python __main__.py
2. With custom arguments: python __main__.py --base-dir /path/to/taxonomy --taxonomy-entry /path/to/entry-point.xsd --output-dir /path/to/output
"""

import sys
import os
import argparse

# Add the current directory to the Python path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from xbrl_taxonomy_parser.parser import XBRLTaxonomyParser
from xbrl_taxonomy_parser.writer import XBRLTaxonomyWriter
from xbrl_taxonomy_parser.stats import XBRLTaxonomyStats

def parse_taxonomy(base_dir, taxonomy_entry, output_dir):
    """Parse the taxonomy and save output files."""
    # Create the parser
    parser = XBRLTaxonomyParser(base_dir, taxonomy_entry, output_dir)

    # Parse the taxonomy
    taxonomy_data = parser.parse()

    # Create the writer
    writer = XBRLTaxonomyWriter(taxonomy_data, output_dir)

    # Write the complete taxonomy to JSON
    writer.write_json()

    # Write the concept hierarchy
    writer.write_concept_hierarchy()

    # Write the dimensional structure
    writer.write_dimensional_structure()

    # Generate statistics
    stats = XBRLTaxonomyStats(taxonomy_data)
    stats_data = stats.generate_full_report()

    # Save statistics
    stats_path = os.path.join(output_dir, "taxonomy_stats.json")
    import json
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)

    print(f"Taxonomy parsing complete. Files saved to: {output_dir}")

def main():
    # Default paths
    project_root = os.path.abspath(os.path.dirname(__file__))
    default_base_dir = os.path.join(project_root, "database_directory", "us-gaaps", "us-gaap-2024")
    default_taxonomy_entry = os.path.join(default_base_dir, "entire", "us-gaap-entryPoint-all-2024.xsd")
    default_output_dir = os.path.join(project_root, "database_directory", "jsons")

    # Set up argument parser with default values
    parser = argparse.ArgumentParser(description='Parse XBRL taxonomy and convert to JSON')
    parser.add_argument('--base-dir',
                      default=default_base_dir,
                      help='Base directory containing the taxonomy files')
    parser.add_argument('--taxonomy-entry',
                      default=default_taxonomy_entry,
                      help='Path to the entry point XSD file')
    parser.add_argument('--output-dir',
                      default=default_output_dir,
                      help='Directory to save the output JSON files')

    args = parser.parse_args()

    # Make sure directories exist
    os.makedirs(args.base_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Using base directory: {args.base_dir}")
    print(f"Using taxonomy entry: {args.taxonomy_entry}")
    print(f"Using output directory: {args.output_dir}")

    # Parse the taxonomy
    parse_taxonomy(args.base_dir, args.taxonomy_entry, args.output_dir)

if __name__ == "__main__":
    main()