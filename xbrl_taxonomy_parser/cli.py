"""
Command-line interface for the XBRL Taxonomy Parser.

This module provides a command-line interface for parsing XBRL taxonomies
and converting them to JSON.
"""

import os
import json
import logging
from typing import Dict, Any

from .parser import XBRLTaxonomyParser
from .writer import XBRLTaxonomyWriter
from .stats import XBRLTaxonomyStats

def parse_taxonomy(base_dir: str, taxonomy_entry: str, output_dir: str) -> str:
    """
    Parse an XBRL taxonomy and save the results to JSON files.
    
    Args:
        base_dir: Base directory containing the taxonomy files
        taxonomy_entry: Path to the entry point XSD file
        output_dir: Directory to save the output JSON files
        
    Returns:
        The path to the main output JSON file
    """
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
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)
    
    return os.path.join(output_dir, "taxonomy.json")

def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse XBRL taxonomy and convert to JSON')
    parser.add_argument('--base-dir', 
                        required=True,
                        help='Base directory containing the taxonomy files')
    parser.add_argument('--taxonomy-entry', 
                        required=True,
                        help='Path to the entry point XSD file')
    parser.add_argument('--output-dir', 
                        required=True,
                        help='Directory to save the output JSON files')
    
    args = parser.parse_args()
    
    # Parse the taxonomy
    output_file = parse_taxonomy(args.base_dir, args.taxonomy_entry, args.output_dir)
    
    print(f"Taxonomy parsing complete. Main output file: {output_file}")

if __name__ == "__main__":
    main()
