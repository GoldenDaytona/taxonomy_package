"""
Utility functions and constants for the XBRL Taxonomy Parser.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, Any, Set
from functools import lru_cache
from pathlib import Path

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

# Cache processed files to avoid redundant operations
FILE_CACHE: Dict[str, Any] = {}
RESOLVED_PATHS: Dict[str, str] = {}


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

    # Create handlers only if they don't exist to avoid duplicates
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Create file handler
        log_file = Path(output_dir) / 'parser.log'
        file_handler = logging.FileHandler(log_file)
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


@lru_cache(maxsize=1024)
def resolve_path(reference_path: str, base_dir: str, base_taxonomy_dir: str, url_mappings: Dict[str, str]) -> str:
    """
    Resolve a relative path against a base directory with caching for performance.

    Args:
        reference_path: The relative path to resolve
        base_dir: The base directory
        base_taxonomy_dir: The base taxonomy directory
        url_mappings: Mappings from URL prefixes to local directories

    Returns:
        The resolved absolute path
    """
    # Check if we already resolved this path
    cache_key = f"{reference_path}|{base_dir}"
    if cache_key in RESOLVED_PATHS:
        return RESOLVED_PATHS[cache_key]

    # Handle URLs by converting to a local path if possible
    if reference_path.startswith(('http://', 'https://')):
        local_path = map_url_to_local_path(reference_path, base_taxonomy_dir, url_mappings)
        if local_path:
            RESOLVED_PATHS[cache_key] = local_path
            return local_path
        else:
            RESOLVED_PATHS[cache_key] = reference_path
            return reference_path

    # Handle relative paths
    if not os.path.isabs(reference_path):
        resolved_path = os.path.normpath(os.path.join(base_dir, reference_path))
        RESOLVED_PATHS[cache_key] = resolved_path
        return resolved_path

    resolved_path = os.path.normpath(reference_path)
    RESOLVED_PATHS[cache_key] = resolved_path
    return resolved_path


@lru_cache(maxsize=1024)
def map_url_to_local_path(url: str, base_taxonomy_dir: str, url_mappings: Dict[str, str]) -> Optional[str]:
    """
    Map a URL to a local file path based on known patterns with improved repository structure support.

    Args:
        url: The URL to map
        base_taxonomy_dir: The base directory for taxonomy files
        url_mappings: Mappings from URL prefixes to local directories

    Returns:
        The local file path if mapping is possible, None otherwise
    """
    # First check URL mappings from configuration
    for prefix, local_dir in url_mappings.items():
        if url.startswith(prefix):
            relative_path = url[len(prefix):]
            # Normalize slashes for local filesystem
            relative_path = relative_path.replace('/', os.path.sep)
            return os.path.join(local_dir, relative_path)

    # Handle the resources folder structure (resources -> http -> www.xbrl.org -> 2003 -> xsd files)
    if url.startswith(('http://', 'https://')):
        # Remove protocol
        url_without_protocol = url.split('://', 1)[1]

        # Check if we have a resources directory
        repo_dir = os.path.join(base_taxonomy_dir, "resources")
        if os.path.exists(repo_dir):
            # Map to the structure: resources/http/domain/path
            protocol = "http"  # Default to http folder
            if url.startswith('https://'):
                protocol = "https"

            # Create the expected path
            repo_path = os.path.join(repo_dir, protocol, url_without_protocol)

            # Check if path exists, if not try the alternate protocol
            if not os.path.exists(repo_path) and protocol == "https":
                alt_repo_path = os.path.join(repo_dir, "http", url_without_protocol)
                if os.path.exists(alt_repo_path):
                    return alt_repo_path
            elif not os.path.exists(repo_path) and protocol == "http":
                alt_repo_path = os.path.join(repo_dir, "https", url_without_protocol)
                if os.path.exists(alt_repo_path):
                    return alt_repo_path

            return repo_path

    return None


def clear_caches() -> None:
    """Clear all internal caches to free memory."""
    FILE_CACHE.clear()
    RESOLVED_PATHS.clear()
    resolve_path.cache_clear()
    map_url_to_local_path.cache_clear()