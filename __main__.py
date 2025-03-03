"""
Main entry point for the XBRL Taxonomy Parser.

Usage:
    from xbrl_taxonomy_parser import parse_xbrl_taxonomy

    parse_xbrl_taxonomy(
        base_dir="/path/to/taxonomy",
        taxonomy_entry="/path/to/entry-point.xsd",
        output_dir="/path/to/output"
    )
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path for package imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from xbrl_taxonomy_parser.parser import XBRLTaxonomyParser
from xbrl_taxonomy_parser.writer import XBRLTaxonomyWriter
from xbrl_taxonomy_parser.stats import XBRLTaxonomyStats


def parse_xbrl_taxonomy(base_dir, taxonomy_entry, output_dir):
    """
    Parse an XBRL taxonomy and save all output files.

    Args:
        base_dir (str): Base directory containing the taxonomy files
        taxonomy_entry (str): Path to the entry point XSD file
        output_dir (str): Directory to save the output JSON files

    Returns:
        dict: The parsed taxonomy data
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create and run the parser
    parser = XBRLTaxonomyParser(base_dir, taxonomy_entry, output_dir)
    taxonomy_data = parser.parse()

    # Write all outputs
    writer = XBRLTaxonomyWriter(taxonomy_data, output_dir)
    writer.write_all_outputs()

    # Generate and save statistics report
    stats = XBRLTaxonomyStats(taxonomy_data)
    stats.save_report(output_dir)

    print(f"Taxonomy parsing complete. Files saved to: {output_dir}")
    return taxonomy_data


if __name__ == "__main__":
    # Default example usage when run directly
    project_root = Path(__file__).parent.parent
    default_base_dir = str(project_root / "database_directory" / "us-gaaps" / "us-gaap-2024")
    default_taxonomy_entry = str(Path(default_base_dir) / "entire" / "us-gaap-entryPoint-all-2024.xsd")
    default_output_dir = str(project_root / "database_directory" / "jsons")

    # Print information
    print(f"Using base directory: {default_base_dir}")
    print(f"Using taxonomy entry: {default_taxonomy_entry}")
    print(f"Using output directory: {default_output_dir}")

    # Parse the taxonomy with defaults
    parse_xbrl_taxonomy(default_base_dir, default_taxonomy_entry, default_output_dir)