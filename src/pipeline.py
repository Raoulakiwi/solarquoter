"""Phase 1: Lead Discovery Pipeline for SolarQuoter.

Orchestrates the lead discovery process:
1. Query TheLIST Building Polygons for NW Tasmania
2. Filter by building type and footprint area
3. Cross-reference with zoning layer
4. Link to addresses via spatial join
5. Output to Parquet format
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.config import (
    load_config,
    get_region_bbox,
    get_building_types,
    get_min_footprint,
    get_allowed_zones,
    get_output_path,
    create_thelist_client,
)
from src.data_schema import RAW_LEAD_COLUMNS
from src.spatial_utils import (
    spatial_join_buildings_addresses,
    filter_by_zones,
    add_centroid,
    format_addresses,
)


def setup_logging(config: dict) -> None:
    """Configure logging based on config settings."""
    log_config = config.get('logging', {})
    level = log_config.get('level', 'INFO')
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    logging.basicConfig(
        level=getattr(logging, level),
        format=format_str,
        stream=sys.stdout
    )


def print_pipeline_header():
    """Print pipeline startup header."""
    print("=" * 70)
    print("SolarQuoter Phase 1: Lead Discovery")
    print("=" * 70)


def print_summary_stats(
    buildings_count: int,
    filtered_count: int,
    zoned_count: int,
    addressed_count: int,
    output_path: Path
) -> None:
    """Print summary statistics of the pipeline run."""
    print("\n" + "=" * 70)
    print("PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Initial buildings queried:    {buildings_count:,}")
    print(f"After type/area filtering:    {filtered_count:,}")
    print(f"After zoning filter:         {zoned_count:,}")
    print(f"After address join:           {addressed_count:,}")
    print("-" * 70)
    print(f"Output file: {output_path}")
    print("=" * 70)


def run_phase1(config: dict, region: str = 'northwest') -> gpd.GeoDataFrame:
    """Execute Phase 1: Lead Discovery pipeline.
    
    Args:
        config: SolarQuoter configuration dictionary.
        region: Region name (e.g., 'northwest').
        
    Returns:
        GeoDataFrame of discovered leads.
    """
    logger = logging.getLogger(__name__)
    
    region_config = config['regions'].get(region)
    if not region_config:
        raise ValueError(f"Unknown region: {region}")
    
    region_name = region_config['name']
    bbox = get_region_bbox(config, region)
    building_types = get_building_types(config)
    min_area = get_min_footprint(config)
    allowed_zones = get_allowed_zones(config)
    
    print(f"\nRegion: {region_name}")
    print(f"BBOX: S{bbox['south']:.2f} W{bbox['west']:.2f} -> N{bbox['north']:.2f} E{bbox['east']:.2f}")
    print(f"Building types: {', '.join(building_types)}")
    print(f"Min footprint: {min_area}m²")
    print(f"Allowed zones: {', '.join(allowed_zones)}")
    
    # Initialize TheLIST client
    print("\n[1/6] Connecting to TheLIST WFS...")
    client = create_thelist_client(config)
    logger.info(f"Connected to TheLIST WFS: {config['thelist']['wfs_url']}")
    
    # Query buildings
    print("\n[2/6] Querying building polygons...")
    buildings_gdf = client.query_buildings(
        bbox=bbox,
        building_types=building_types,
        min_area_m2=min_area
    )
    initial_count = len(buildings_gdf)
    print(f"Found {initial_count:,} buildings in region")
    
    if initial_count == 0:
        logger.warning("No buildings found - check bbox and filters")
        return gpd.GeoDataFrame()
    
    # Apply additional filtering in pandas (since WFS WHERE has limitations)
    print("\n[3/6] Filtering by building type and footprint...")
    filtered_gdf = buildings_gdf.copy()
    
    # Filter by building type
    if building_types:
        filtered_gdf = filtered_gdf[filtered_gdf['BLD_PUR'].isin(building_types)]
    
    # Filter by minimum area (more precise than WFS query)
    filtered_gdf = filtered_gdf[filtered_gdf['footprint_m2'] >= min_area]
    
    filtered_count = len(filtered_gdf)
    print(f"After type/area filter: {filtered_count:,} buildings")
    
    if filtered_count == 0:
        logger.warning("No buildings after filtering")
        return gpd.GeoDataFrame()
    
    # Query zoning
    print("\n[4/6] Querying zoning layer...")
    zones_gdf = client.query_zoning(bbox)
    print(f"Retrieved {len(zones_gdf):,} zone polygons")
    
    # Filter buildings by zones
    print("\n[5/6] Filtering by zoning classification...")
    zoned_gdf = filter_by_zones(filtered_gdf, zones_gdf, allowed_zones)
    zoned_count = len(zoned_gdf)
    print(f"Buildings in allowed zones: {zoned_count:,}")
    
    if zoned_count == 0:
        logger.warning("No buildings in allowed zones")
        return gpd.GeoDataFrame()
    
    # Query addresses
    print("\n[6/6] Querying address points...")
    addresses_gdf = client.query_addresses(bbox)
    print(f"Retrieved {len(addresses_gdf):,} address points")
    
    # Spatial join with addresses
    print("\n[7/7] Performing spatial join with addresses...")
    joined_gdf = spatial_join_buildings_addresses(
        zoned_gdf,
        addresses_gdf,
        max_distance_m=50
    )
    addressed_count = len(joined_gdf)
    
    # Add centroids
    print("\nAdding centroid coordinates...")
    joined_gdf = add_centroid(joined_gdf)
    
    # Format full addresses
    print("Formatting addresses...")
    joined_gdf = format_addresses(joined_gdf)
    
    # Add region column
    joined_gdf['region'] = region_name
    
    # Standardize column names to match schema
    # TheLIST uses different casing
    column_mapping = {
        'OBJECTID': 'objectid',
        'BUILD_ID': 'build_id',
        'BUILD_TY': 'build_ty',
        'BUILD_NAME': 'build_name',
        'BLD_PUR': 'bld_pur',
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in joined_gdf.columns:
            joined_gdf.rename(columns={old_col: new_col}, inplace=True)
    
    # Select and order columns to match schema
    output_columns = [col for col in RAW_LEAD_COLUMNS if col in joined_gdf.columns]
    # Add any extra columns that exist
    for col in joined_gdf.columns:
        if col not in output_columns and col not in ['geometry']:
            output_columns.append(col)
    
    # Ensure geometry is last
    if 'geometry' in output_columns:
        output_columns.remove('geometry')
        output_columns.append('geometry')
    
    final_gdf = joined_gdf[output_columns].copy()
    
    # Save to Parquet
    output_path = get_output_path(config, 'raw_leads', region)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSaving to {output_path}...")
    final_gdf.to_parquet(output_path, index=False)
    
    print_summary_stats(
        initial_count,
        filtered_count,
        zoned_count,
        addressed_count,
        output_path
    )
    
    return final_gdf


def main():
    """Main entry point for Phase 1 pipeline."""
    print_pipeline_header()
    
    # Load configuration
    config = load_config()
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting SolarQuoter Phase 1: Lead Discovery")
    
    try:
        # Run for NW Tasmania
        leads_gdf = run_phase1(config, region='northwest')
        
        if len(leads_gdf) > 0:
            print(f"\n✓ Phase 1 complete. {len(leads_gdf)} leads discovered.")
            
            # Print sample of results
            print("\nSample leads (first 5):")
            print("-" * 70)
            for i, row in leads_gdf.head().iterrows():
                addr = row.get('full_address', 'No address')
                area = row.get('footprint_m2', 0)
                bldg_pur = row.get('bld_pur', 'Unknown')
                zone = row.get('zone', 'Unknown')
                print(f"  • {addr}")
                print(f"    {bldg_pur}, {area:.0f}m², Zone: {zone}")
                print()
        else:
            print("\n✗ No leads discovered. Check logs for details.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n✗ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
