"""
XBRL Taxonomy Statistics module.

This module contains the XBRLTaxonomyStats class which is responsible for
generating statistics and analytics for an XBRL taxonomy.
"""

from typing import Dict, Any

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
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the taxonomy.
        
        Returns:
            A dictionary containing basic statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})
        linkbases = self.taxonomy_data.get('linkbases', {})
        
        stats = {
            "totalConcepts": len(concepts),
            "abstractConcepts": sum(1 for c in concepts.values() if c.get('abstract') == 'true'),
            "nonAbstractConcepts": sum(1 for c in concepts.values() if c.get('abstract') != 'true'),
            "presentationNetworks": len(linkbases.get('presentation', {})),
            "calculationNetworks": len(linkbases.get('calculation', {})),
            "definitionNetworks": len(linkbases.get('definition', {})),
            "roleTypes": len(self.taxonomy_data.get('roleTypes', {})),
            "arcroleTypes": len(self.taxonomy_data.get('arcroleTypes', {})),
            "dimensions": len(self.taxonomy_data.get('dimensions', {})),
            "hypercubes": sum(1 for d in self.taxonomy_data.get('dimensions', {}).values() 
                             if 'hypercube' in d.get('related', {})),
            "explicitDimensions": sum(1 for d in self.taxonomy_data.get('dimensions', {}).values() 
                                     if 'dimension' in d.get('related', {}))
        }
        
        return stats
    
    def get_element_types(self) -> Dict[str, int]:
        """
        Get statistics about the types of elements in the taxonomy.
        
        Returns:
            A dictionary containing element type statistics
        """
        concepts = self.taxonomy_data.get('concepts', {})
        
        types = {}
        
        for concept in concepts.values():
            concept_type = concept.get('type', 'unknown')
            types[concept_type] = types.get(concept_type, 0) + 1
        
        return dict(sorted(types.items(), key=lambda x: x[1], reverse=True))
    
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
        
        for concept_id, concept in concepts.items():
            for linkbase_type in usage.keys():
                if linkbase_type in concept:
                    role_count = len(concept[linkbase_type])
                    usage[linkbase_type][concept_id] = role_count
        
        # Sort by usage count
        for linkbase_type in usage.keys():
            usage[linkbase_type] = dict(sorted(usage[linkbase_type].items(), 
                                            key=lambda x: x[1], reverse=True))
        
        return usage
    
    def get_role_usage(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about how roles are used in different linkbases.
        
        Returns:
            A dictionary containing role usage statistics
        """
        linkbases = self.taxonomy_data.get('linkbases', {})
        
        usage = {}
        
        for linkbase_type, roles in linkbases.items():
            usage[linkbase_type] = {}
            
            for role, role_data in roles.items():
                concept_count = len(role_data.get('concepts', []))
                usage[linkbase_type][role] = concept_count
        
        # Sort by usage count
        for linkbase_type in usage.keys():
            usage[linkbase_type] = dict(sorted(usage[linkbase_type].items(), 
                                            key=lambda x: x[1], reverse=True))
        
        return usage
    
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
            "roleUsage": self.get_role_usage()
        }
        
        return report
