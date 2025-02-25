"""
XBRL Taxonomy Writer module.

This module contains the XBRLTaxonomyWriter class which is responsible for
writing XBRL taxonomy data to various output formats.
"""

import os
import json
from typing import Dict, Any, List

class XBRLTaxonomyWriter:
    """
    A class to write XBRL taxonomy data to various output formats.
    """
    
    def __init__(self, taxonomy_data: Dict[str, Any], output_dir: str):
        """
        Initialize the XBRL taxonomy writer.
        
        Args:
            taxonomy_data: The taxonomy data to write
            output_dir: Directory to save the output files
        """
        self.taxonomy_data = taxonomy_data
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def write_json(self, filename: str = "taxonomy.json") -> None:
        """
        Write the taxonomy data to a JSON file.
        
        Args:
            filename: The name of the output file
        """
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.taxonomy_data, f, indent=2, ensure_ascii=False)
        
    def write_concept_hierarchy(self, filename: str = "concept_hierarchy.json") -> None:
        """
        Write a hierarchical representation of concepts based on presentation linkbases.
        
        Args:
            filename: The name of the output file
        """
        # Build hierarchy from presentation relationships
        hierarchy = self._build_concept_hierarchy()
        
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, indent=2, ensure_ascii=False)
    
    def _build_concept_hierarchy(self) -> Dict[str, Any]:
        """
        Build a hierarchical representation of concepts based on presentation linkbases.
        
        Returns:
            A dictionary containing the concept hierarchy
        """
        hierarchy = {}
        
        # Get presentation linkbases
        presentation_linkbases = self.taxonomy_data.get('linkbases', {}).get('presentation', {})
        
        for role, linkbase in presentation_linkbases.items():
            role_hierarchy = {
                "role": role,
                "definition": self._get_role_definition(role),
                "roots": []
            }
            
            relationships = linkbase.get('relationships', {})
            all_children = set()
            
            # Collect all concepts that appear as children
            for parent, children in relationships.items():
                for child in children:
                    all_children.add(child.get('to'))
            
            # Find root concepts (those that appear as parents but not as children)
            root_concepts = [parent for parent in relationships.keys() 
                             if parent not in all_children]
            
            # Build hierarchy for each root
            for root in root_concepts:
                root_hierarchy = self._build_concept_subtree(root, relationships)
                role_hierarchy["roots"].append(root_hierarchy)
            
            hierarchy[role] = role_hierarchy
        
        return hierarchy
    
    def _build_concept_subtree(self, concept_id: str, relationships: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Build a subtree for a concept based on its relationships.
        
        Args:
            concept_id: The ID of the concept
            relationships: A dictionary of relationships
            
        Returns:
            A dictionary containing the concept subtree
        """
        concept_info = self.taxonomy_data.get('concepts', {}).get(concept_id, {})
        
        subtree = {
            "id": concept_id,
            "name": concept_info.get('name', ''),
            "labels": self._simplify_labels(concept_info.get('labels', {})),
            "children": []
        }
        
        # Add children if any
        if concept_id in relationships:
            for child in relationships[concept_id]:
                child_id = child.get('to')
                child_subtree = self._build_concept_subtree(child_id, relationships)
                subtree["children"].append(child_subtree)
        
        return subtree
    
    def _simplify_labels(self, labels: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """
        Simplify the label structure for cleaner output.
        
        Args:
            labels: The full label structure
            
        Returns:
            A simplified dictionary of labels
        """
        if not labels:
            return {}
        
        # Prefer English labels if available
        lang = 'en' if 'en' in labels else list(labels.keys())[0]
        
        # Create a mapping of role to label text
        return labels.get(lang, {})
    
    def _get_role_definition(self, role: str) -> str:
        """
        Get the definition for a role.
        
        Args:
            role: The role URI
            
        Returns:
            The definition of the role if found, the role URI otherwise
        """
        role_type = self.taxonomy_data.get('roleTypes', {}).get(role, {})
        return role_type.get('definition', role)
    
    def write_dimensional_structure(self, filename: str = "dimensions.json") -> None:
        """
        Write a structured representation of dimensions.
        
        Args:
            filename: The name of the output file
        """
        dimensions = self.taxonomy_data.get('dimensions', {})
        
        structured_dimensions = {}
        
        for dim_id, dim_info in dimensions.items():
            # Check if this is a hypercube
            if 'hypercube' in dim_info.get('related', {}):
                structured_dimensions[dim_id] = self._build_hypercube_structure(dim_id, dimensions)
        
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(structured_dimensions, f, indent=2, ensure_ascii=False)
    
    def _build_hypercube_structure(self, hypercube_id: str, dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a structured representation of a hypercube.
        
        Args:
            hypercube_id: The ID of the hypercube
            dimensions: The dimensions dictionary
            
        Returns:
            A dictionary containing the hypercube structure
        """
        hypercube_info = dimensions.get(hypercube_id, {})
        concept_info = self.taxonomy_data.get('concepts', {}).get(hypercube_id, {})
        
        structure = {
            "id": hypercube_id,
            "name": concept_info.get('name', ''),
            "labels": self._simplify_labels(concept_info.get('labels', {})),
            "dimensions": []
        }
        
        # Add dimensions
        for dim_id in hypercube_info.get('related', {}).get('dimension', []):
            dim_structure = self._build_dimension_structure(dim_id, dimensions)
            structure["dimensions"].append(dim_structure)
        
        return structure
    
    def _build_dimension_structure(self, dimension_id: str, dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a structured representation of a dimension.
        
        Args:
            dimension_id: The ID of the dimension
            dimensions: The dimensions dictionary
            
        Returns:
            A dictionary containing the dimension structure
        """
        dimension_info = dimensions.get(dimension_id, {})
        concept_info = self.taxonomy_data.get('concepts', {}).get(dimension_id, {})
        
        structure = {
            "id": dimension_id,
            "name": concept_info.get('name', ''),
            "labels": self._simplify_labels(concept_info.get('labels', {})),
            "domains": []
        }
        
        # Add domains
        for domain_id in dimension_info.get('related', {}).get('domain', []):
            domain_structure = self._build_domain_structure(domain_id, dimensions)
            structure["domains"].append(domain_structure)
        
        return structure
    
    def _build_domain_structure(self, domain_id: str, dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a structured representation of a domain.
        
        Args:
            domain_id: The ID of the domain
            dimensions: The dimensions dictionary
            
        Returns:
            A dictionary containing the domain structure
        """
        domain_info = dimensions.get(domain_id, {})
        concept_info = self.taxonomy_data.get('concepts', {}).get(domain_id, {})
        
        structure = {
            "id": domain_id,
            "name": concept_info.get('name', ''),
            "labels": self._simplify_labels(concept_info.get('labels', {})),
            "members": []
        }
        
        # Add members
        for member_id in domain_info.get('related', {}).get('member', []):
            member_structure = self._build_member_structure(member_id, dimensions)
            structure["members"].append(member_structure)
        
        return structure
    
    def _build_member_structure(self, member_id: str, dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a structured representation of a member.
        
        Args:
            member_id: The ID of the member
            dimensions: The dimensions dictionary
            
        Returns:
            A dictionary containing the member structure
        """
        member_info = dimensions.get(member_id, {})
        concept_info = self.taxonomy_data.get('concepts', {}).get(member_id, {})
        
        structure = {
            "id": member_id,
            "name": concept_info.get('name', ''),
            "labels": self._simplify_labels(concept_info.get('labels', {})),
            "children": []
        }
        
        # Add child members recursively
        for child_id in member_info.get('related', {}).get('member', []):
            child_structure = self._build_member_structure(child_id, dimensions)
            structure["children"].append(child_structure)
        
        return structure
