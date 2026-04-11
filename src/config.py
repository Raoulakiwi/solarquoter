"""Configuration loader for SolarQuoter."""

import os
from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml. Defaults to project root config.yaml.
        
    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        # Default to config.yaml in project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    return config


def get_region_bbox(config: dict[str, Any], region: str) -> dict[str, float]:
    """Get bounding box for a region.
    
    Args:
        config: Configuration dictionary.
        region: Region name (e.g., 'northwest').
        
    Returns:
        Dictionary with north, south, east, west keys.
    """
    return config["regions"][region]["bbox"]


def get_region_postcodes(config: dict[str, Any], region: str) -> list[int]:
    """Get postcodes for a region.
    
    Args:
        config: Configuration dictionary.
        region: Region name.
        
    Returns:
        List of postcode integers.
    """
    return config["regions"][region]["postcodes"]


def get_thelist_config(config: dict[str, Any]) -> dict[str, Any]:
    """Get TheLIST WFS configuration.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        Dictionary with WFS URL and layer IDs.
    """
    return config["thelist"]


def get_building_types(config: dict[str, Any]) -> list[str]:
    """Get building type filters.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        List of building purpose types to filter.
    """
    return config["building_types"]


def get_min_footprint(config: dict[str, Any]) -> float:
    """Get minimum footprint threshold in m².
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        Minimum footprint in square meters.
    """
    return config["min_footprint_m2"]


def get_allowed_zones(config: dict[str, Any]) -> list[str]:
    """Get allowed zoning classifications.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        List of allowed zone names.
    """
    return config["allowed_zones"]


def get_output_path(config: dict[str, Any], stage: str, region: str) -> Path:
    """Get output path for a pipeline stage.
    
    Args:
        config: Configuration dictionary.
        stage: Pipeline stage ('raw_leads', 'scored_leads', etc.).
        region: Region name.
        
    Returns:
        Path object for the output file.
    """
    project_root = Path(__file__).parent.parent
    output_template = config["output"][stage]
    filename = output_template.format(region=region)
    return project_root / filename
