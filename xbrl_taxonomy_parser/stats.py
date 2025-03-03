"""
XBRL Taxonomy Statistics module.

This module contains the XBRLTaxonomyStats class which is responsible for
generating statistics and analytics for an XBRL taxonomy.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
from functools import lru_cache


class XBRLTaxonomyStats:
    """
    A class to generate statistics and analytics for an XBRL taxonomy.
    """

    def __init__(self, taxonomy_data: Dict[str, Any]):
        """
        Initialize the XBRL taxonomy statistics generator.

        Args:
            taxonomy_data: The taxonomy data to analyze
        """
        self.taxonomy_data = taxonomy_data

    @lru_cache(maxsize=1)
    def get_basic_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the taxonomy.

        Returns:
            A dictionary containing basic statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})
        linkbases = self.taxonomy_data.get('linkbases', {})

        # Count abstract and non-abstract concepts in a single pass
        abstract_count = 0
        non_abstract_count = 0

        for c in concepts.values():
            if c.get('abstract') == 'true':
                abstract_count += 1
            else:
                non_abstract_count += 1

        stats = {
            "totalConcepts": len(concepts),
            "abstractConcepts": abstract_count,
            "nonAbstractConcepts": non_abstract_count,
            "presentationNetworks": len(linkbases.get('presentation', {})),
            "calculationNetworks": len(linkbases.get('calculation', {})),
            "definitionNetworks": len(linkbases.get('definition', {})),
            "roleTypes": len(self.taxonomy_data.get('roleTypes', {})),
            "arcroleTypes": len(self.taxonomy_data.get('arcroleTypes', {})),
        }

        # Process dimensions in a more efficient way
        dimensions = self.taxonomy_data.get('dimensions', {})
        hypercube_count = 0
        explicit_dimension_count = 0

        for dim in dimensions.values():
            related = dim.get('related', {})
            if 'hypercube' in related:
                hypercube_count += 1
            if 'dimension' in related:
                explicit_dimension_count += 1

        stats.update({
            "dimensions": len(dimensions),
            "hypercubes": hypercube_count,
            "explicitDimensions": explicit_dimension_count
        })

        return stats

    @lru_cache(maxsize=1)
    def get_element_types(self) -> Dict[str, int]:
        """
        Get statistics about the types of elements in the taxonomy.

        Returns:
            A dictionary containing element type statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})

        # Count element types in a single pass
        types = {}

        for concept in concepts.values():
            concept_type = concept.get('type', 'unknown')
            types[concept_type] = types.get(concept_type, 0) + 1

        # Sort by count (most used types first)
        return dict(sorted(types.items(), key=lambda x: x[1], reverse=True))

    @lru_cache(maxsize=1)
    def get_concept_usage(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about how concepts are used in different linkbases.

        Returns:
            A dictionary containing concept usage statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})

        usage = {
            "presentation": {},
            "calculation": {},
            "definition": {}
        }

        # Process all concepts in a single pass for each linkbase
        for concept_id, concept in concepts.items():
            for linkbase_type in usage.keys():
                if linkbase_type in concept:
                    role_count = len(concept[linkbase_type])
                    usage[linkbase_type][concept_id] = role_count

        # Sort usage by count (most used concepts first)
        for linkbase_type in usage.keys():
            usage[linkbase_type] = dict(sorted(
                usage[linkbase_type].items(),
                key=lambda x: x[1],
                reverse=True
            ))

        return usage

    @lru_cache(maxsize=1)
    def get_role_usage(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about how roles are used in different linkbases.

        Returns:
            A dictionary containing role usage statistics
        """
        linkbases = self.taxonomy_data.get('linkbases', {})

        usage = {}

        # Process all linkbases
        for linkbase_type, roles in linkbases.items():
            usage[linkbase_type] = {}

            for role, role_data in roles.items():
                concept_count = len(role_data.get('concepts', []))
                usage[linkbase_type][role] = concept_count

        # Sort by usage count
        for linkbase_type in usage.keys():
            usage[linkbase_type] = dict(sorted(
                usage[linkbase_type].items(),
                key=lambda x: x[1],
                reverse=True
            ))

        return usage

    @lru_cache(maxsize=1)
    def get_namespace_stats(self) -> Dict[str, int]:
        """
        Get statistics about namespaces used in the taxonomy.

        Returns:
            A dictionary containing namespace usage statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})

        namespaces = {}

        # Count concepts per namespace
        for concept in concepts.values():
            namespace = concept.get('namespace', 'unknown')
            namespaces[namespace] = namespaces.get(namespace, 0) + 1

        # Sort by count (most used namespaces first)
        return dict(sorted(namespaces.items(), key=lambda x: x[1], reverse=True))

    @lru_cache(maxsize=1)
    def get_period_type_stats(self) -> Dict[str, int]:
        """
        Get statistics about period types used in the taxonomy.

        Returns:
            A dictionary containing period type usage statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})

        period_types = {}

        # Count concepts per period type
        for concept in concepts.values():
            period_type = concept.get('periodType', 'unknown')
            period_types[period_type] = period_types.get(period_type, 0) + 1

        return period_types

    @lru_cache(maxsize=1)
    def generate_full_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive statistics report for the taxonomy.

        Returns:
            A dictionary containing all statistics
        """
        report = {
            "basicStats": self.get_basic_stats(),
            "elementTypes": self.get_element_types(),
            "conceptUsage": self.get_concept_usage(),
            "roleUsage": self.get_role_usage(),
            "namespaceStats": self.get_namespace_stats(),
            "periodTypeStats": self.get_period_type_stats()
        }

        return report

    def save_report(self, output_dir: str, filename: str = "taxonomy_stats.json") -> str:
        """
        Generate and save a comprehensive statistics report for the taxonomy.

        Args:
            output_dir: Directory to save the report
            filename: Name of the output file

        Returns:
            Path to the saved report file
        """
        # Generate the full report
        report = self.generate_full_report()

        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Save the report to a JSON file
        output_path = Path(output_dir) / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"Taxonomy statistics report saved to: {output_path}")
        return str(output_path)

    def get_top_concepts(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most frequently used concepts across all linkbases.

        Args:
            count: Number of top concepts to return

        Returns:
            List of top concepts with usage information
        """
        usage = self.get_concept_usage()

        # Combine usage across all linkbases
        combined_usage = {}

        for linkbase_type, concepts in usage.items():
            for concept_id, role_count in concepts.items():
                if concept_id not in combined_usage:
                    combined_usage[concept_id] = 0
                combined_usage[concept_id] += role_count

        # Sort by total usage
        sorted_usage = sorted(
            combined_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:count]

        # Get concept details
        concepts = self.taxonomy_data.get('concepts', {})
        top_concepts = []

        for concept_id, total_usage in sorted_usage:
            if concept_id in concepts:
                concept = concepts[concept_id]
                top_concepts.append({
                    "id": concept_id,
                    "name": concept.get('name', ''),
                    "type": concept.get('type', ''),
                    "totalUsage": total_usage,
                    "presentationUsage": usage["presentation"].get(concept_id, 0),
                    "calculationUsage": usage["calculation"].get(concept_id, 0),
                    "definitionUsage": usage["definition"].get(concept_id, 0)
                })

        return top_concepts