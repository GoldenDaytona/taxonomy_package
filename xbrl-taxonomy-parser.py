import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union
import xml.etree.ElementTree as ET
from collections import defaultdict
import re


class XBRLTaxonomyParser:
    """
    A parser for XBRL taxonomies that extracts information from XSD and other related files
    and converts it to a structured JSON format.
    """

    # XML namespaces commonly used in XBRL
    NAMESPACES = {
        'xs': 'http://www.w3.org/2001/XMLSchema',
        'xbrli': 'http://www.xbrl.org/2003/instance',
        'link': 'http://www.xbrl.org/2003/linkbase',
        'xlink': 'http://www.w3.org/1999/xlink',
        'label': 'http://www.xbrl.org/2003/label',
        'ref': 'http://www.xbrl.org/2006/ref',
        'xbrldt': 'http://xbrl.org/2005/xbrldt',
        'enum': 'http://xbrl.org/2020/extensible-enumerations-2.0',
        'formula': 'http://xbrl.org/2008/formula',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

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
        self.logger = self._setup_logger()

        # Cache for imported/included schemas to avoid reprocessing
        self.processed_schemas: Set[str] = set()

        # Main storage for parsed elements
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.linkbases: Dict[str, Dict[str, Any]] = {}
        self.role_types: Dict[str, Dict[str, Any]] = {}
        self.arcrole_types: Dict[str, Dict[str, Any]] = {}
        self.enumerations: Dict[str, Dict[str, Any]] = {}
        self.dimensions: Dict[str, Dict[str, Any]] = {}

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger('XBRLTaxonomyParser')
        logger.setLevel(logging.INFO)

        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Create file handler
        file_handler = logging.FileHandler(os.path.join(self.output_dir, 'parser.log'))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

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
                "timestamp": self._get_timestamp()
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

    def _get_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()

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
        for import_elem in root.findall('.//xs:import', self.NAMESPACES):
            schema_location = import_elem.get('schemaLocation')
            if schema_location:
                import_path = self._resolve_path(schema_location, schema_dir)
                if os.path.exists(import_path):
                    self._parse_schema(import_path)
                else:
                    self.logger.warning(f"Import schema not found: {import_path}")

        # Process includes
        for include_elem in root.findall('.//xs:include', self.NAMESPACES):
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
        # Handle URLs by converting to a local path if possible
        if reference_path.startswith(('http://', 'https://')):
            # Try to map to local files based on namespace patterns
            local_path = self._map_url_to_local_path(reference_path)
            if local_path:
                return local_path
            else:
                self.logger.warning(f"Cannot resolve URL to local path: {reference_path}")
                return reference_path

        # Handle relative paths
        if not os.path.isabs(reference_path):
            return os.path.normpath(os.path.join(base_dir, reference_path))

        return os.path.normpath(reference_path)

    def _map_url_to_local_path(self, url: str) -> Optional[str]:
        """
        Try to map a URL to a local file path based on known patterns.

        Args:
            url: The URL to map

        Returns:
            The local file path if mapping is possible, None otherwise
        """
        # Example mapping logic - customize based on your taxonomy structure
        url_patterns = {
            'http://www.xbrl.org/': os.path.join(self.base_dir, 'xbrl'),
            'http://taxonomies.xbrl.us/': os.path.join(self.base_dir, 'us'),
            # Add more mappings as needed
        }

        for prefix, local_dir in url_patterns.items():
            if url.startswith(prefix):
                relative_path = url[len(prefix):]
                return os.path.join(local_dir, relative_path)

        return None

    def _process_elements(self, root: ET.Element, namespace: str, schema_path: str) -> None:
        """
        Process element definitions (XBRL concepts).

        Args:
            root: The root element of the schema
            namespace: The target namespace of the schema
            schema_path: Path to the current schema file
        """
        for element in root.findall('.//xs:element', self.NAMESPACES):
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
                type_elem = element.find('./xs:complexType', self.NAMESPACES) or element.find('./xs:simpleType',
                                                                                              self.NAMESPACES)
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
        for attribute in type_elem.findall('.//xs:attribute', self.NAMESPACES):
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
        for child_elem in type_elem.findall('.//xs:element', self.NAMESPACES):
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
        restriction = type_elem.find('.//xs:restriction', self.NAMESPACES)
        if restriction is not None:
            base_type = restriction.get('base', '')
            type_info["restrictions"]["baseType"] = base_type
            type_info["restrictions"]["facets"] = {}

            # Collect all facets
            for facet in restriction.findall('./xs:*', self.NAMESPACES):
                facet_type = facet.tag.split('}')[-1]
                facet_value = facet.get('value')
                if facet_type and facet_value:
                    type_info["restrictions"]["facets"][facet_type] = facet_value

            # Check for enumerations
            enumerations = restriction.findall('./xs:enumeration', self.NAMESPACES)
            if enumerations:
                for enum in enumerations:
                    enum_value = enum.get('value')
                    if enum_value:
                        # Get annotation/documentation if available
                        doc = enum.find('./xs:annotation/xs:documentation', self.NAMESPACES)
                        enum_description = doc.text if doc is not None else None

                        type_info["enumerations"].append({
                            "value": enum_value,
                            "description": enum_description
                        })

        # Process unions
        union = type_elem.find('.//xs:union', self.NAMESPACES)
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
        for role_type in root.findall('.//link:roleType', self.NAMESPACES):
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
                definition = role_type.find('./link:definition', self.NAMESPACES)
                if definition is not None and definition.text:
                    role_definition["definition"] = definition.text

                # Get usedOn elements
                for used_on in role_type.findall('./link:usedOn', self.NAMESPACES):
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
        for arcrole_type in root.findall('.//link:arcroleType', self.NAMESPACES):
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
                definition = arcrole_type.find('./link:definition', self.NAMESPACES)
                if definition is not None and definition.text:
                    arcrole_definition["definition"] = definition.text

                # Get usedOn elements
                for used_on in arcrole_type.findall('./link:usedOn', self.NAMESPACES):
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

        for linkbase_ref in root.findall('.//link:linkbaseRef', self.NAMESPACES):
            xlink_href = linkbase_ref.get(f"{{{self.NAMESPACES['xlink']}}}href")
            xlink_role = linkbase_ref.get(f"{{{self.NAMESPACES['xlink']}}}role", '')

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
        for label_link in root.findall('.//link:labelLink', self.NAMESPACES):
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in label_link.findall('./link:loc', self.NAMESPACES):
                xlink_href = loc.get(f"{{{self.NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{self.NAMESPACES['xlink']}}}label")

                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id

            # Process label arcs to link concepts with labels
            for labelArc in label_link.findall('./link:labelArc', self.NAMESPACES):
                xlink_from = labelArc.get(f"{{{self.NAMESPACES['xlink']}}}from")
                xlink_to = labelArc.get(f"{{{self.NAMESPACES['xlink']}}}to")

                if xlink_from in concept_locs:
                    concept_id = concept_locs[xlink_from]

                    # Find the corresponding label
                    for label in label_link.findall(f"./link:label[@{{{self.NAMESPACES['xlink']}}}label='{xlink_to}']",
                                                    self.NAMESPACES):
                        label_role = label.get(f"{{{self.NAMESPACES['xlink']}}}role",
                                               'http://www.xbrl.org/2003/role/label')
                        lang = label.get(f"{{{self.NAMESPACES['xml']}}}lang", 'en')

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
        for reference_link in root.findall('.//link:referenceLink', self.NAMESPACES):
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in reference_link.findall('./link:loc', self.NAMESPACES):
                xlink_href = loc.get(f"{{{self.NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{self.NAMESPACES['xlink']}}}label")

                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id

            # Process reference arcs to link concepts with references
            for referenceArc in reference_link.findall('./link:referenceArc', self.NAMESPACES):
                xlink_from = referenceArc.get(f"{{{self.NAMESPACES['xlink']}}}from")
                xlink_to = referenceArc.get(f"{{{self.NAMESPACES['xlink']}}}to")

                if xlink_from in concept_locs:
                    concept_id = concept_locs[xlink_from]

                    # Find the corresponding reference
                    for reference in reference_link.findall(
                            f"./link:reference[@{{{self.NAMESPACES['xlink']}}}label='{xlink_to}']", self.NAMESPACES):
                        reference_role = reference.get(f"{{{self.NAMESPACES['xlink']}}}role",
                                                       'http://www.xbrl.org/2003/role/reference')

                        # Extract all parts of the reference
                        reference_parts = {}
                        for part in reference.findall('./ref:*', self.NAMESPACES):
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
        for link in root.findall(f'.//link:{link_type}', self.NAMESPACES):
            link_role = link.get(f"{{{self.NAMESPACES['xlink']}}}role", '')

            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in link.findall('./link:loc', self.NAMESPACES):
                xlink_href = loc.get(f"{{{self.NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{self.NAMESPACES['xlink']}}}label")

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
            for arc in link.findall(f'./link:{arc_name}', self.NAMESPACES):
                xlink_from = arc.get(f"{{{self.NAMESPACES['xlink']}}}from")
                xlink_to = arc.get(f"{{{self.NAMESPACES['xlink']}}}to")
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
        for definition_link in root.findall('.//link:definitionLink', self.NAMESPACES):
            link_role = definition_link.get(f"{{{self.NAMESPACES['xlink']}}}role", '')
            
            # Process all loc elements to get concept references
            concept_locs = {}
            for loc in definition_link.findall('./link:loc', self.NAMESPACES):
                xlink_href = loc.get(f"{{{self.NAMESPACES['xlink']}}}href")
                xlink_label = loc.get(f"{{{self.NAMESPACES['xlink']}}}label")
                
                if xlink_href and xlink_label:
                    # Extract concept ID from the href
                    concept_id = self._extract_concept_id_from_href(xlink_href)
                    if concept_id:
                        concept_locs[xlink_label] = concept_id
            
            # Process definition arcs to identify dimensions
            for definitionArc in definition_link.findall('./link:definitionArc', self.NAMESPACES):
                xlink_from = definitionArc.get(f"{{{self.NAMESPACES['xlink']}}}from")
                xlink_to = definitionArc.get(f"{{{self.NAMESPACES['xlink']}}}to")
                arcrole = definitionArc.get(f"{{{self.NAMESPACES['xlink']}}}arcrole", '')
                
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


def parse_taxonomy(base_dir, taxonomy_entry, output_dir):
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
    basic_stats = stats.get_basic_stats()
    element_types = stats.get_element_types()
    
    # Save statistics
    stats_data = {
        "basicStats": basic_stats,
        "elementTypes": element_types
    }
    
    stats_path = os.path.join(output_dir, "taxonomy_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, indent=2, ensure_ascii=False)
    
    return os.path.join(output_dir, "taxonomy.json")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse XBRL taxonomy and convert to JSON')
    parser.add_argument('--base-dir', 
                        default=os.path.normpath("C:/Users/blackdaytona/Desktop/Research/us-gaaps/us-gaap-2024"),
                        help='Base directory containing the taxonomy files')
    parser.add_argument('--taxonomy-entry', 
                        default=os.path.normpath("C:/Users/blackdaytona/Desktop/Research/us-gaaps/us-gaap-2024/entire/us-gaap-entryPoint-all-2024.xsd"),
                        help='Path to the entry point XSD file')
    parser.add_argument('--output-dir', 
                        default=os.path.normpath("C:/Users/blackdaytona/Desktop/Research"),
                        help='Directory to save the output JSON files')
    
    args = parser.parse_args()
    
    # Parse the taxonomy
    output_file = parse_taxonomy(args.base_dir, args.taxonomy_entry, args.output_dir)
    
    print(f"Taxonomy parsing complete. Main output file: {output_file}")
