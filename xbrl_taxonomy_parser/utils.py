"""
Utility functions and constants for the XBRL Taxonomy Parser.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional

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
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xml': 'http://www.w3.org/XML/1998/namespace'
}

def setup_logger(name: str, output_dir: str) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        name: Name of the logger
        output_dir: Directory to save log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Create console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Create file handler
    file_handler = logging.FileHandler(os.path.join(output_dir, 'parser.log'))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def get_timestamp() -> str:
    """
    Get the current timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp string
    """
    return datetime.now().isoformat()

def resolve_path(reference_path: str, base_dir: str, base_taxonomy_dir: str, url_mappings: Dict[str, str]) -> str:
    """
    Resolve a relative path against a base directory.

    Args:
        reference_path: The relative path to resolve
        base_dir: The base directory
        base_taxonomy_dir: The base taxonomy directory
        url_mappings: Mappings from URL prefixes to local directories

    Returns:
        The resolved absolute path
    """
    # Handle URLs by converting to a local path if possible
    if reference_path.startswith(('http://', 'https://')):
        # Try to map to local files based on namespace patterns
        local_path = map_url_to_local_path(reference_path, base_taxonomy_dir, url_mappings)
        if local_path:
            return local_path
        else:
            return reference_path

    # Handle relative paths
    if not os.path.isabs(reference_path):
        return os.path.normpath(os.path.join(base_dir, reference_path))

    return os.path.normpath(reference_path)

def map_url_to_local_path(url: str, base_taxonomy_dir: str, url_mappings: Dict[str, str]) -> Optional[str]:
    """
    Try to map a URL to a local file path based on known patterns.

    Args:
        url: The URL to map
        base_taxonomy_dir: The base directory for taxonomy files
        url_mappings: Mappings from URL prefixes to local directories

    Returns:
        The local file path if mapping is possible, None otherwise
    """
    for prefix, local_dir in url_mappings.items():
        if url.startswith(prefix):
            relative_path = url[len(prefix):]
            # Normalize slashes for local filesystem
            relative_path = relative_path.replace('/', os.path.sep)
            return os.path.join(local_dir, relative_path)

    return None
