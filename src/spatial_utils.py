"""Spatial utility functions for SolarQuoter lead processing.

Provides geometry operations for building-address matching,
zoning filtering, and coordinate extraction.
"""

import logging
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)


def spatial_join_buildings_addresses(
    buildings_gdf: gpd.GeoDataFrame,
    addresses_gdf: gpd.GeoDataFrame,
    max_distance_m: float = 50
) -> gpd.GeoDataFrame:
    """Perform spatial join between buildings and addresses.
    
    Matches each building to its nearest address point within
    the specified maximum distance.
    
    Args:
        buildings_gdf: GeoDataFrame of building polygons.
        addresses_gdf: GeoDataFrame of address points.
        max_distance_m: Maximum distance in meters to consider a match.
        
    Returns:
        GeoDataFrame of buildings with matched address fields.
        Buildings without a nearby address will have null address fields.
    """
    if len(buildings_gdf) == 0:
        logger.warning("No buildings to join")
        return buildings_gdf
    
    if len(addresses_gdf) == 0:
        logger.warning("No addresses to join with")
        # Return buildings with empty address columns
        result = buildings_gdf.copy()
        address_cols = ['street_number', 'street_name', 'street_type', 
                        'locality', 'postcode', 'full_address']
        for col in address_cols:
            if col not in result.columns:
                result[col] = None
        return result
    
    # Project to a metric CRS for accurate distance calculations
    # Tasmania uses EPSG:32755 (UTM zone 55S) or EPSG:28355 (GDA94 / MGA zone 55)
    buildings_proj = buildings_gdf.to_crs('EPSG:32755')
    addresses_proj = addresses_gdf.to_crs('EPSG:32755')
    
    # Create centroids for buildings
    buildings_proj['centroid'] = buildings_proj.geometry.centroid
    
    # Nearest neighbor join using sindex
    buildings_proj['nearest_idx'] = None
    buildings_proj['nearest_dist'] = None
    
    sindex = addresses_proj.sindex
    
    for idx, building in buildings_proj.iterrows():
        centroid = building['centroid']
        # Search within bounding box + buffer
        possible_matches_idx = list(sindex.intersection(centroid.buffer(max_distance_m).bounds))
        
        if not possible_matches_idx:
            continue
        
        # Find nearest address
        min_dist = float('inf')
        nearest_idx = None
        
        for addr_idx in possible_matches_idx:
            dist = centroid.distance(addresses_proj.iloc[addr_idx].geometry)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = addr_idx
        
        if nearest_idx is not None and min_dist <= max_distance_m:
            buildings_proj.at[idx, 'nearest_idx'] = nearest_idx
            buildings_proj.at[idx, 'nearest_dist'] = min_dist
    
    # Join address data
    addresses_flat = addresses_proj.copy()
    addresses_flat = addresses_flat.reset_index(drop=True)
    
    # Create result by merging
    result = buildings_gdf.copy()
    
    # Initialize address columns
    for col in ['street_number', 'street_name', 'street_type', 
                'locality', 'postcode', 'full_address']:
        if col not in result.columns:
            result[col] = None
    
    # Map matched addresses
    matched_count = 0
    for idx, building in buildings_proj.iterrows():
        if building['nearest_idx'] is not None:
            addr = addresses_flat.iloc[int(building['nearest_idx'])]
            result.at[idx, 'street_number'] = str(addr.get('ST_NO_FROM', ''))
            result.at[idx, 'street_name'] = addr.get('STREET', '')
            result.at[idx, 'street_type'] = addr.get('ST_TYPE', '')
            result.at[idx, 'locality'] = addr.get('LOCALITY', '')
            result.at[idx, 'postcode'] = str(addr.get('POSTCODE', ''))
            matched_count += 1
    
    logger.info(f"Matched {matched_count}/{len(buildings_gdf)} buildings to addresses")
    
    # Drop temporary columns
    if 'centroid' in result.columns:
        result.drop(columns=['centroid'], inplace=True)
    if 'nearest_idx' in result.columns:
        result.drop(columns=['nearest_idx'], inplace=True)
    if 'nearest_dist' in result.columns:
        result.drop(columns=['nearest_dist'], inplace=True)
    
    return result


def filter_by_zones(
    buildings_gdf: gpd.GeoDataFrame,
    zones_gdf: gpd.GeoDataFrame,
    allowed_zones: list[str]
) -> gpd.GeoDataFrame:
    """Filter buildings by zoning classification using spatial overlay.
    
    Args:
        buildings_gdf: GeoDataFrame of building polygons.
        zones_gdf: GeoDataFrame of zoning polygons with ZONE field.
        allowed_zones: List of acceptable zone names.
        
    Returns:
        GeoDataFrame of buildings within allowed zoning areas.
    """
    if len(buildings_gdf) == 0:
        logger.warning("No buildings to filter")
        return buildings_gdf
    
    if len(zones_gdf) == 0:
        logger.warning("No zoning data - cannot filter")
        return gpd.GeoDataFrame()
    
    # Ensure both are in the same CRS
    if buildings_gdf.crs != zones_gdf.crs:
        zones_gdf = zones_gdf.to_crs(buildings_gdf.crs)
    
    # Filter zones to only allowed ones
    zones_filtered = zones_gdf[zones_gdf['ZONE'].isin(allowed_zones)]
    
    if len(zones_filtered) == 0:
        logger.warning(f"No zones found matching: {allowed_zones}")
        return gpd.GeoDataFrame()
    
    logger.info(f"Filtering buildings by {len(zones_filtered)} zone polygons")
    
    # Spatial overlay - keep buildings that intersect with allowed zones
    try:
        joined = gpd.overlay(buildings_gdf, zones_filtered, how='intersection', keep_geom_type=True)
        
        # If multiple zones overlap a building, keep the first (or best match)
        # For simplicity, take the first zone match
        joined = joined.drop_duplicates(subset=buildings_gdf.columns.tolist(), keep='first')
        
        # Rename ZONE column to zone (for consistency)
        if 'ZONE' in joined.columns:
            joined.rename(columns={'ZONE': 'zone'}, inplace=True)
        
        logger.info(f"Buildings within allowed zones: {len(joined)}")
        return joined
        
    except Exception as e:
        logger.error(f"Spatial overlay failed: {e}")
        # Fallback: point-in-polygon test using centroids
        logger.info("Falling back to centroid-based zoning check")
        
        buildings_proj = buildings_gdf.to_crs('EPSG:32755')
        zones_proj = zones_filtered.to_crs('EPSG:32755')
        
        buildings_proj['centroid'] = buildings_proj.geometry.centroid
        buildings_proj['centroid_point'] = buildings_proj['centroid']
        
        result_list = []
        for idx, building in buildings_proj.iterrows():
            centroid = building['centroid_point']
            for _, zone in zones_proj.iterrows():
                if zone.geometry.contains(centroid):
                    new_row = building.copy()
                    new_row['zone'] = zone['ZONE']
                    result_list.append(new_row)
                    break
        
        if result_list:
            result = gpd.GeoDataFrame(result_list)
            result.drop(columns=['centroid', 'centroid_point'], inplace=True)
            return result
        else:
            return gpd.GeoDataFrame()


def add_centroid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add centroid_lat and centroid_lon columns to GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame with geometry column.
        
    Returns:
        GeoDataFrame with centroid_lat and centroid_lon columns added.
    """
    result = gdf.copy()
    
    # Ensure we have a geometry column
    if result.geometry.name is None:
        raise ValueError("No geometry column set")
    
    # Calculate centroids in WGS84
    if result.crs and result.crs != 'EPSG:4326':
        gdf_4326 = result.to_crs('EPSG:4326')
    else:
        gdf_4326 = result
    
    centroids = gdf_4326.geometry.centroid
    
    result['centroid_lat'] = centroids.y
    result['centroid_lon'] = centroids.x
    
    logger.debug(f"Added centroid coordinates to {len(result)} features")
    
    return result


def building_to_address_string(row: pd.Series) -> str:
    """Format full street address from address components.
    
    Args:
        row: Series with street_number, street_name, street_type,
             locality, postcode fields.
             
    Returns:
        Formatted address string (e.g., "123 Main St, Devonport TAS 7310").
    """
    parts = []
    
    # Street number and name
    if pd.notna(row.get('street_number')) and str(row.get('street_number')).strip():
        parts.append(str(row.get('street_number')).strip())
    
    if pd.notna(row.get('street_name')) and str(row.get('street_name')).strip():
        street = str(row.get('street_name')).strip()
        if pd.notna(row.get('street_type')) and str(row.get('street_type')).strip():
            street += f" {str(row.get('street_type')).strip()}"
        parts.append(street)
    
    # Locality
    if pd.notna(row.get('locality')) and str(row.get('locality')).strip():
        parts.append(str(row.get('locality')).strip())
    
    # Postcode
    if pd.notna(row.get('postcode')) and str(row.get('postcode')).strip():
        parts.append(f"TAS {str(row.get('postcode')).strip()}")
    
    if parts:
        return ', '.join(parts)
    else:
        return ''


def format_addresses(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add full_address column to GeoDataFrame by formatting address components.
    
    Args:
        gdf: GeoDataFrame with address component columns.
        
    Returns:
        GeoDataFrame with full_address column added.
    """
    result = gdf.copy()
    
    if 'full_address' not in result.columns:
        result['full_address'] = result.apply(building_to_address_string, axis=1)
    
    logger.debug(f"Formatted {len(result)} addresses")
    
    return result
