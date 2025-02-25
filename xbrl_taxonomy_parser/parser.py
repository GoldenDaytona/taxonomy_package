"""
XBRL Taxonomy Parser module.

This module contains the XBRLTaxonomyParser class which is responsible for
parsing XBRL taxonomy files and extracting their structure.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
import xml.etree.ElementTree as ET
from collections import defaultdict
import re

from .utils import NAMESPACES, setup_logger, get_timestamp, resolve_path, map_url_to_local_path

class XBRLTaxonomyParser:
    """
    A parser for XBRL taxonomies that extracts information from XSD and other related files
    and converts it to a structured JSON format.
    """

    def __init__(self, base_dir: str, taxonomy_entry: str, output_dir: str):
        """
        Initialize the XBRL taxonomy parser.

        Args:
            base_dir: Base directory containing the taxonomy files
            taxonomy_entry: Path to the entry point XSD file
            output_dir: Directory to save the output JSON files
        """
        self.base_dir = os.path.normpath(base_dir)
        self.taxonomy_entry = os.path.normpath(taxonomy_entry)
        self.output_dir = os.path.normpath(output_dir)

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize logger
        self.logger = setup_logger('XBRLTaxonomyParser', self.output_dir)

        # Cache for imported/included schemas to avoid reprocessing
        self.processed_schemas: Set[str] = set()

        # Main storage for parsed elements
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.linkbases: Dict[str, Dict[str, Any]] = {}
        self.role_types: Dict[str, Dict[str, Any]] = {}
        self.arcrole_types: Dict[str, Dict[str, Any]] = {}
        self.enumerations: Dict[str, Dict[str, Any]] = {}
        self.dimensions: Dict[str, Dict[str, Any]] = {}
        
        # URL to local path mappings - including the new mapping for FASB
        self.url_mappings = {
            'http://www.xbrl.org/': os.path.join(self.base_dir, 'xbrl'),
            'http://taxonomies.xbrl.us/': os.path.join(self.base_dir, 'us'),
            'https://xbrl.fasb.org/': os.path.join(self.base_dir, 'fasb'),
            'http://xbrl.fasb.org/': os.path.join(self.base_dir, 'fasb'),
            'https://xbrl.sec.gov/': os.path.join(self.base_dir, 'sec'),
            'http://xbrl.sec.gov/': os.path.join(self.base_dir, 'sec')
        }

    def parse(self) -> Dict[str, Any]:
        """
        Parse the taxonomy starting from the entry point.

        Returns:
            A dictionary containing the structured taxonomy data
        """
        self.logger.info(f"Starting to parse taxonomy from: {self.taxonomy_entry}")

        # Parse the main entry point
        self._parse_schema(self.taxonomy_entry)

        # Organize the complete taxonomy structure
        taxonomy_data = {
            "metadata": {
                "entryPoint": self.taxonomy_entry,
                "baseDir": self.base_dir,
                "timestamp": get_timestamp()
            },
            "concepts": self.concepts,
            "linkbases": self.linkbases,
            "roleTypes": self.role_types,
            "arcroleTypes": self.arcrole_types,
            "dimensions": self.dimensions,
            "enumerations": self.enumerations
        }

        # Save the complete taxonomy
        self._save_json(taxonomy_data, "complete_taxonomy.json")

        # Save individual components for easier access
        self._save_json(self.concepts, "concepts.json")
        self._save_json(self.linkbases, "linkbases.json")
        self._save_json(self.role_types, "role_types.json")
        self._save_json(self.dimensions, "dimensions.json")

        self.logger.info(f"Parsing complete. Files saved to: {self.output_dir}")
        return taxonomy_data

    def _save_json(self, data: Dict[str, Any], filename: str) -> None:
        """Save data as a JSON file."""
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Saved: {output_path}")

    def _parse_schema(self, schema_path: str) -> None:
        """
        Parse an XSD schema file and extract all relevant information.

        Args:
            schema_path: Path to the XSD schema file
        """
        # Avoid reprocessing
        if schema_path in self.processed_schemas:
            return

        self.processed_schemas.add(schema_path)
        self.logger.info(f"Parsing schema: {schema_path}")

        try:
            # Parse the XML schema
            tree = ET.parse(schema_path)
            root = tree.getroot()

            # Get the target namespace
            target_namespace = root.get('targetNamespace', '')

            # Process imports and includes
            self._process_imports_and_includes(root, schema_path)

            # Process elements (concepts)
            self._process_elements(root, target_namespace, schema_path)

            # Process role types
            self._process_role_types(root, target_namespace)

            # Process arcrole types
            self._process_arcrole_types(root, target_namespace)

            # Process linkbases referenced in the schema
            self._process_linkbase_refs(root, schema_path)

        except Exception as e:
            self.logger.error(f"Error parsing schema {schema_path}: {str(e)}")

    def _process_imports_and_includes(self, root: ET.Element, schema_path: str) -> None:
        """
        Process xs:import and xs:include elements to follow references.

        Args:
            root: The root element of the schema
            schema_path: Path to the current schema file
        """
        schema_dir = os.path.dirname(schema_path)

        # Process imports
        for import_elem in root.findall('.//xs:import', NAMESPACES):
            schema_location = import_elem.get('schemaLocation')
            if schema_location:
                import_path = self._resolve_path(schema_location, schema_dir)
                if os.path.exists(import_path):
                    self._parse_schema(import_path)
                else:
                    self.logger.warning(f"Import schema not found: {import_path}")

        # Process includes
        for include_elem in root.findall('.//xs:include', NAMESPACES):
            schema_location = include_elem.get('schemaLocation')
            if schema_location:
                include_path = self._resolve_path(schema_location, schema_dir)
                if os.path.exists(include_path):
                    self._parse_schema(include_path)
                else:
                    self.logger.warning(f"Include schema not found: {include_path}")

    def _resolve_path(self, reference_path: str, base_dir: str) -> str:
        """
        Resolve a relative path against a base directory.

        Args:
            reference_path: The relative path to resolve
            base_dir: The base directory

        Returns:
            The resolved absolute path
        """
        return resolve_path(reference_path, base_dir, self.base_dir, self.url_mappings)

    def _process_elements(self, root: ET.Element, namespace: str, schema_path: str) -> None:
        """
        Process element definitions (XBRL concepts).

        Args:
            root: The root element of the schema
            namespace: The target namespace of the schema
            schema_path: Path to the current schema file
        """
        for element in root.findall('.//xs:element', NAMESPACES):
            name = element.get('name')
            if name:
                # Create a unique ID for the concept
                concept_id = f"{namespace}#{name}"

                # Extract element attributes
                concept_data = {
                    "name": name,
                    "namespace": namespace,
                    "id": concept_id,
                    "abstract": element.get('abstract', 'false'),
                    "nillable": element.get('nillable', 'false'),
                    "substitutionGroup": element.get('substitutionGroup', ''),
                    "type": element.get('type', ''),
                    "periodType": None,  # Will be filled from label linkbases
                    "balance": None,  # Will be filled from label linkbases
                    "sourceFile": schema_path,
                    "labels": {},
                    "references": {},
                    "presentation": {},
                    "calculation": {},
                    "definition": {}
                }

                # Extract custom attributes (xbrli:periodType, xbrli:balance)
                for attrib_name, attrib_value in element.attrib.items():
                    if 'periodType' in attrib_name:
                        concept_data["periodType"] = attrib_value
                    elif 'balance' in attrib_name:
                        concept_data["balance"] = attrib_value

                # Process type definition if it's inline
                type_elem = element.find('./xs:complexType', NAMESPACES) or element.find('./xs:simpleType',
                                                                                      NAMESPACES)
                if type_elem is not None:
                    concept_data["hasCustomType"] = True
                    concept_data["customType"] = self._extract_type_info(type_elem)

                # Add to concepts dictionary
                self.concepts[concept_id] = concept_data

    def _extract_type_info(self, type_elem: ET.Element) -> Dict[str, Any]:
        """
        Extract information from a complex or simple type definition.

        Args:
            type_elem: The type element

        Returns:
            A dictionary with type information
        """
        type_info = {
            "kind": type_elem.tag.split('}')[-1],  # complexType or simpleType
            "attributes": [],
            "elements": [],
            "restrictions": {},
            "unions": [],
            "enumerations": []
        }

        # Process attributes
        for attribute in type_elem.findall('.//xs:attribute', NAMESPACES):
            attr_name = attribute.get('name')
            attr_type = attribute.get('type')
            attr_use = attribute.get('use', 'optional')

            if attr_name:
                type_info["attributes"].append({
                    "name": attr_name,
                    "type": attr_type,
                    "use": attr_use
                })

        # Process child elements
        for child_elem in type_elem.findall('.//xs:element', NAMESPACES):
            elem_name = child_elem.get('name')
            elem_type = child_elem.get('type')
            elem_min = child_elem.get('minOccurs', '1')
            elem_max = child_elem.get('maxOccurs', '1')

            if elem_name:
                type_info["elements"].append({
                    "name": elem_name,
                    "type": elem_type,
                    "minOccurs": elem_min,
                    "maxOccurs": elem_max
                })

        # Process restrictions
        restriction = type_elem.find('.//xs:restriction', NAMESPACES)
        if restriction is not None:
            base_type = restriction.get('base', '')
            type_info["restrictions"]["baseType"] = base_type
            type_info["restrictions"]["facets"] = {}

            # Collect all facets
            for facet in restriction.findall('./xs:*', NAMESPACES):
                facet_type = facet.tag.split('}')[-1]
                facet_value = facet.get('value')
                if facet_type and facet_value:
                    type_info["restrictions"]["facets"][facet_type] = facet_value

            # Check for enumerations
            enumerations = restriction.findall('./xs:enumeration', NAMESPACES)
            if enumerations:
                for enum in enumerations:
                    enum_value = enum.get('value')
                    if enum_value:
                        # Get annotation/documentation if available
                        doc = enum.find('./xs:annotation/xs:documentation', NAMESPACES)
                        enum_description = doc.text if doc is not None else None

                        type_info["enumerations"].append({
                            "value": enum_value,
                            "description": enum_description
                        })

        # Process unions
        union = type_elem.find('.//xs:union', NAMESPACES)
        if union is not None:
            member_types = union.get('memberTypes', '').split()
            type_info["unions"] = member_types

        return type_info

    def _process_role_types(self, root: ET.Element, namespace: str) -> None:
        """
        Process role type definitions.

        Args:
            root: The root element of the schema
            namespace: The target namespace of the schema
        """
        for role_type in root.findall('.//link:roleType', NAMESPACES):
            role_id = role_type.get('id')
            role_uri = role_type.get('roleURI')

            if role_id and role_uri:
                role_definition = {
                    "id": role_id,
                    "roleURI": role_uri,
                    "namespace": namespace,
                    "usedOn": []
                }

                # Get definition if present
                definition = role_type.find('./link:definition', NAMESPACES)
                if definition is not None and definition.text:
                    role_definition["definition"] = definition.text

                # Get usedOn elements
                for used_on in role_type.findall('./link:usedOn', NAMESPACES):
                    if used_on.text:
                        role_definition["usedOn"].append(used_on.text)

                self.role_types[role_uri] = role_definition

    def _process_arcrole_types(self, root: ET.Element, namespace: str) -> None:
        """
        Process arcrole type definitions.

        Args:
            root: The root element of the schema
            namespace: The target namespace of the schema
        """
        for arcrole_type in root.findall('.//link:arcroleType', NAMESPACES):
            arcrole_id = arcrole_type.get('id')
            arcrole_uri = arcrole_type.get('arcroleURI')

            if arcrole_id and arcrole_uri:
                arcrole_definition = {
                    "id": arcrole_id,
                    "arcroleURI": arcrole_uri,
                    "namespace": namespace,
                    "usedOn": [],
                    "cycles": arcrole_type.get('cyclesAllowed', 'none')
                }

                # Get definition if present
                definition = arcrole_type.find('./link:definition', NAMESPACES)
                if definition is not None and definition.text:
                    arcrole_definition["definition"] = definition.text

                # Get usedOn elements
                for used_on in arcrole_type.findall('./link:usedOn', NAMESPACES):
                    if used_on.text:
                        arcrole_definition["usedOn"].append(used_on.text)

                self.arcrole_types[arcrole_uri] = arcrole_definition

    def _process_linkbase_refs(self, root: ET.Element, schema_path: str) -> None:
        """
        Process linkbaseRef elements to parse referenced linkbases.

        Args:
            root: The root element of the schema
            schema_path: Path to the current schema file
        """
        schema_dir = os.path.dirname(schema_path)

        for linkbase_ref in root.findall('.//link:linkbaseRef', NAMESPACES):
            xlink_href = linkbase_ref.get(f"{{{NAMESPACES['xlink']}}}href")
            xlink_role = linkbase_ref.get(f"{{{NAMESPACES['xlink']}}}role", '')

            if xlink_href:
                linkbase_path = self._resolve_path(xlink_href, schema_dir)

                # Check if file exists
                if os.path.exists(linkbase_path):
                    self._parse_linkbase(linkbase_path, xlink_role)
                else:
                    self.logger.warning(f"Linkbase file not found: {linkbase_path}")

    def _parse_linkbase(self, linkbase_path: str, role: str = '') -> None:
        """
        Parse a linkbase file to extract relationships and labels.

        Args:
            linkbase_path: Path to the linkbase file
            role: The role of the linkbase
        """
        self.logger.info(f"Parsing linkbase: {linkbase_path}")

        try:
            # Parse the XML linkbase
            tree = ET.parse(linkbase_path)
            root = tree.getroot()

            # Process label linkbases
            self._process_label_links(root, linkbase_path)

            # Process reference linkbases
            self._process_reference_links(root, linkbase_path)

            # Process presentation linkbases
            self._process_presentation_links(root, linkbase_path)

            # Process calculation linkbases
            self._process_calculation_links(root, linkbase_path)

            # Process definition linkbases
            self._process_definition_links(root, linkbase_path)

        except Exception as e:
            self.logger.error(f"Error parsing linkbase {linkbase_path}: {str(e)}")

    def _process_label_links(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Process label links to extract concept labels.

        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        # Find all labelLink elements
        for label_link in root.findall('.//link:labelLink', NAMESPACES):
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in label_link.findall('./link:loc', NAMESPACES):
                xlink_href = loc.get(f"{{{NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{NAMESPACES['xlink']}}}label")

                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id

            # Process label arcs to link concepts with labels
            for labelArc in label_link.findall('./link:labelArc', NAMESPACES):
                xlink_from = labelArc.get(f"{{{NAMESPACES['xlink']}}}from")
                xlink_to = labelArc.get(f"{{{NAMESPACES['xlink']}}}to")

                if xlink_from in concept_locs:
                    concept_id = concept_locs[xlink_from]

                    # Find the corresponding label
                    for label in label_link.findall(f"./link:label[@{{{NAMESPACES['xlink']}}}label='{xlink_to}']",
                                                    NAMESPACES):
                        label_role = label.get(f"{{{NAMESPACES['xlink']}}}role",
                                               'http://www.xbrl.org/2003/role/label')
                        lang = label.get(f"{{{NAMESPACES['xml']}}}lang", 'en')

                        if concept_id in self.concepts:
                            # Ensure the labels dictionary is initialized
                            if "labels" not in self.concepts[concept_id]:
                                self.concepts[concept_id]["labels"] = {}

                            # Ensure the language dictionary is initialized
                            if lang not in self.concepts[concept_id]["labels"]:
                                self.concepts[concept_id]["labels"][lang] = {}

                            # Store the label
                            self.concepts[concept_id]["labels"][lang][label_role] = label.text or ''

    def _process_reference_links(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Process reference links to extract concept references.

        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        # Find all referenceLink elements
        for reference_link in root.findall('.//link:referenceLink', NAMESPACES):
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in reference_link.findall('./link:loc', NAMESPACES):
                xlink_href = loc.get(f"{{{NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{NAMESPACES['xlink']}}}label")

                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id

            # Process reference arcs to link concepts with references
            for referenceArc in reference_link.findall('./link:referenceArc', NAMESPACES):
                xlink_from = referenceArc.get(f"{{{NAMESPACES['xlink']}}}from")
                xlink_to = referenceArc.get(f"{{{NAMESPACES['xlink']}}}to")

                if xlink_from in concept_locs:
                    concept_id = concept_locs[xlink_from]

                    # Find the corresponding reference
                    for reference in reference_link.findall(
                            f"./link:reference[@{{{NAMESPACES['xlink']}}}label='{xlink_to}']", NAMESPACES):
                        reference_role = reference.get(f"{{{NAMESPACES['xlink']}}}role",
                                                       'http://www.xbrl.org/2003/role/reference')

                        # Extract all parts of the reference
                        reference_parts = {}
                        for part in reference.findall('./ref:*', NAMESPACES):
                            part_name = part.tag.split('}')[-1]
                            reference_parts[part_name] = part.text or ''

                        if concept_id in self.concepts:
                            # Ensure the references dictionary is initialized
                            if "references" not in self.concepts[concept_id]:
                                self.concepts[concept_id]["references"] = {}

                            # Store the reference
                            if reference_role not in self.concepts[concept_id]["references"]:
                                self.concepts[concept_id]["references"][reference_role] = []

                            self.concepts[concept_id]["references"][reference_role].append(reference_parts)

    def _process_presentation_links(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Process presentation links to extract hierarchical relationships.

        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        self._process_relationship_links(
            root,
            'presentationLink',
            'presentation',
            linkbase_path
        )

    def _process_calculation_links(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Process calculation links to extract calculation relationships.

        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        self._process_relationship_links(
            root,
            'calculationLink',
            'calculation',
            linkbase_path,
            extra_attrs=['weight']
        )

    def _process_definition_links(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Process definition links to extract definition relationships.

        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        self._process_relationship_links(
            root,
            'definitionLink',
            'definition',
            linkbase_path,
            extra_attrs=['contextElement', 'typedDomainRef', 'targetRole']
        )

        # Process dimension information
        self._extract_dimensions(root, linkbase_path)

    def _process_relationship_links(
            self,
            root: ET.Element,
            link_type: str,
            relationship_type: str,
            linkbase_path: str,
            extra_attrs: List[str] = None
    ) -> None:
        """
        Process relationship links to extract hierarchical relationships.

        Args:
            root: The root element of the linkbase
            link_type: The type of link to process (presentationLink, calculationLink, etc.)
            relationship_type: The type of relationship (presentation, calculation, etc.)
            linkbase_path: Path to the linkbase file
            extra_attrs: Additional attributes to extract from the arc
        """
        if extra_attrs is None:
            extra_attrs = []

        # Find all links of the specified type
        for link in root.findall(f'.//link:{link_type}', NAMESPACES):
            link_role = link.get(f"{{{NAMESPACES['xlink']}}}role", '')

            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in link.findall('./link:loc', NAMESPACES):
                xlink_href = loc.get(f"{{{NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{NAMESPACES['xlink']}}}label")

                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id

            # Build a hierarchy of relationships
            relationships = defaultdict(list)

            # Arc name varies depending on the link type
            arc_name = f"{relationship_type}Arc"

            # Process arcs to link concepts
            for arc in link.findall(f'./link:{arc_name}', NAMESPACES):
                xlink_from = arc.get(f"{{{NAMESPACES['xlink']}}}from")
                xlink_to = arc.get(f"{{{NAMESPACES['xlink']}}}to")
                order = arc.get('order', '1')
                preferred_label = arc.get('preferredLabel', '')

                # Extract additional attributes
                additional_attrs = {}
                for attr in extra_attrs:
                    value = arc.get(attr)
                    if value:
                        additional_attrs[attr] = value

                if xlink_from in concept_locs and xlink_to in concept_locs:
                    parent_id = concept_locs[xlink_from]
                    child_id = concept_locs[xlink_to]

                    relationship = {
                        "to": child_id,
                        "order": float(order),
                        "preferredLabel": preferred_label
                    }

                    # Add additional attributes
                    relationship.update(additional_attrs)

                    relationships[parent_id].append(relationship)

            # Store relationships in the appropriate dictionary
            for parent_id, children in relationships.items():
                if parent_id in self.concepts:
                    # Sort children by order
                    sorted_children = sorted(children, key=lambda x: x["order"])

                    # Ensure the relationship dictionary is initialized
                    if relationship_type not in self.concepts[parent_id]:
                        self.concepts[parent_id][relationship_type] = {}
                    if link_role not in self.concepts[parent_id][relationship_type]:
                        self.concepts[parent_id][relationship_type][link_role] = []
                    
                    self.concepts[parent_id][relationship_type][link_role].extend(sorted_children)
            
            # Also store a separate linkbase structure for easier navigation
            self.linkbases.setdefault(relationship_type, {}).setdefault(link_role, {
                "concepts": list(set(concept_locs.values())),
                "relationships": dict(relationships),
                "sourceFile": linkbase_path
            })
    
    def _extract_dimensions(self, root: ET.Element, linkbase_path: str) -> None:
        """
        Extract dimensional information from definition linkbases.
        
        Args:
            root: The root element of the linkbase
            linkbase_path: Path to the linkbase file
        """
        # Find all definitionLink elements
        for definition_link in root.findall('.//link:definitionLink', NAMESPACES):
            link_role = definition_link.get(f"{{{NAMESPACES['xlink']}}}role", '')
            
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in definition_link.findall('./link:loc', NAMESPACES):
                xlink_href = loc.get(f"{{{NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{NAMESPACES['xlink']}}}label")
                
                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id
            
            # Process definition arcs to identify dimensions
            for definitionArc in definition_link.findall('./link:definitionArc', NAMESPACES):
                xlink_from = definitionArc.get(f"{{{NAMESPACES['xlink']}}}from")
                xlink_to = definitionArc.get(f"{{{NAMESPACES['xlink']}}}to")
                arcrole = definitionArc.get(f"{{{NAMESPACES['xlink']}}}arcrole", '')
                
                if xlink_from in concept_locs and xlink_to in concept_locs:
                    from_id = concept_locs[xlink_from]
                    to_id = concept_locs[xlink_to]
                    
                    # Check for dimension-domain relationships
                    if arcrole == 'http://xbrl.org/int/dim/arcrole/dimension-domain':
                        self._add_dimension(from_id, to_id, 'domain', link_role, linkbase_path)
                    
                    # Check for domain-member relationships
                    elif arcrole == 'http://xbrl.org/int/dim/arcrole/domain-member':
                        self._add_dimension(from_id, to_id, 'member', link_role, linkbase_path)
                    
                    # Check for hypercube-dimension relationships
                    elif arcrole == 'http://xbrl.org/int/dim/arcrole/hypercube-dimension':
                        self._add_dimension(from_id, to_id, 'dimension', link_role, linkbase_path)
                    
                    # Check for all relationships
                    elif arcrole == 'http://xbrl.org/int/dim/arcrole/all':
                        self._add_dimension(from_id, to_id, 'hypercube', link_role, linkbase_path)
    
    def _add_dimension(self, from_id: str, to_id: str, rel_type: str, link_role: str, source_file: str) -> None:
        """
        Add dimensional information to the dimensions dictionary.
        
        Args:
            from_id: The concept ID of the source concept
            to_id: The concept ID of the target concept
            rel_type: The type of dimensional relationship
            link_role: The role of the link
            source_file: The source file
        """
        # Initialize dimension structure
        if from_id not in self.dimensions:
            self.dimensions[from_id] = {
                "id": from_id,
                "related": {},
                "roles": set()
            }
        
        # Initialize relation type
        if rel_type not in self.dimensions[from_id]["related"]:
            self.dimensions[from_id]["related"][rel_type] = set()
        
        # Add target ID
        self.dimensions[from_id]["related"][rel_type].add(to_id)
        
        # Add role
        self.dimensions[from_id]["roles"].add(link_role)
        
        # Make sets serializable to JSON
        for key, value in self.dimensions[from_id]["related"].items():
            self.dimensions[from_id]["related"][key] = list(value)
        
        self.dimensions[from_id]["roles"] = list(self.dimensions[from_id]["roles"])
        
        # Add source file
        self.dimensions[from_id]["sourceFile"] = source_file
    
    def _extract_concept_id_from_href(self, href: str) -> Optional[str]:
        """
        Extract a concept ID from an XLink href attribute.
        
        Args:
            href: The href attribute value
            
        Returns:
            The concept ID if extraction is successful, None otherwise
        """
        # Remove fragment identifier
        if '#' in href:
            schema_path, fragment = href.split('#', 1)
            
            # Try to find the namespace for the schema
            namespace = None
            for concept in self.concepts.values():
                if schema_path in concept.get('sourceFile', ''):
                    namespace = concept.get('namespace')
                    break
            
            if namespace:
                # Return the concept ID
                return f"{namespace}#{fragment}"
            else:
                # Try to extract namespace from schema
                try:
                    schema_path = self._resolve_path(schema_path, os.path.dirname(self.taxonomy_entry))
                    if os.path.exists(schema_path):
                        tree = ET.parse(schema_path)
                        root = tree.getroot()
                        namespace = root.get('targetNamespace')
                        if namespace:
                            return f"{namespace}#{fragment}"
                except Exception:
                    pass
        
        return None
