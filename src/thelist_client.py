"""TheLIST WFS client for querying spatial data.

TheLIST (Land Information System Tasmania) provides WFS access to
building polygons, zoning, and address data via ArcGIS REST API.
"""

import logging
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape

logger = logging.getLogger(__name__)


class TheLISTClient:
    """Client for TheLIST WFS ArcGIS REST API."""
    
    def __init__(self, wfs_url: str, timeout: int = 60):
        """Initialize TheLIST WFS client.
        
        Args:
            wfs_url: Base WFS URL (e.g., 'https://services.thelist.tas.gov.au/arcgis/rest/services/Public/OpenDataWFS/MapServer').
            timeout: Request timeout in seconds.
        """
        self.wfs_url = wfs_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def _query_layer(
        self,
        layer_id: int,
        bbox: Optional[dict[str, float]] = None,
        where: Optional[str] = None,
        out_fields: Optional[list[str]] = None,
        return_geometry: bool = True
    ) -> gpd.GeoDataFrame:
        """Query a WFS layer and return features as GeoDataFrame.
        
        Args:
            layer_id: TheLIST layer ID.
            bbox: Bounding box dict with north, south, east, west keys.
            where: WHERE clause filter.
            out_fields: List of fields to return.
            return_geometry: Whether to include geometry.
            
        Returns:
            GeoDataFrame of features.
        """
        url = f"{self.wfs_url}/{layer_id}/query"
        
        params = {
            'f': 'geojson',
            'returnGeometry': 'true' if return_geometry else 'false',
            'outSR': '4326'  # WGS84
        }
        
        if bbox:
            # Format: 'south,west,north,east'
            bbox_str = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
            params['geometry'] = bbox_str
            params['geometryType'] = 'esriGeometryEnvelope'
            params['spatialRel'] = 'esriSpatialRelIntersects'
        
        if where:
            params['where'] = where
        
        if out_fields:
            params['outFields'] = ','.join(out_fields)
        
        logger.debug(f"Querying layer {layer_id}: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if 'features' not in data or len(data['features']) == 0:
                logger.info(f"No features returned from layer {layer_id}")
                return gpd.GeoDataFrame()
            
            # Convert to GeoDataFrame
            features = data['features']
            records = []
            
            for feature in features:
                props = feature.get('properties', {})
                geom = shape(feature.get('geometry')) if return_geometry else None
                records.append({**props, 'geometry': geom})
            
            gdf = gpd.GeoDataFrame.from_records(records)
            if return_geometry:
                gdf.set_geometry('geometry', inplace=True)
            
            # Set CRS if available
            if 'crs' in data:
                # Extract CRS from response
                crs = data['crs']['properties']['name']
                gdf.set_crs(crs, inplace=True, allow_override=True)
            else:
                # Default to WGS84
                gdf.set_crs('EPSG:4326', inplace=True, allow_override=True)
            
            logger.info(f"Retrieved {len(gdf)} features from layer {layer_id}")
            return gdf
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WFS query failed for layer {layer_id}: {e}")
            raise
    
    def query_buildings(
        self,
        bbox: dict[str, float],
        building_types: Optional[list[str]] = None,
        min_area_m2: Optional[float] = None
    ) -> gpd.GeoDataFrame:
        """Query building polygons from TheLIST.
        
        Note: TheLIST WFS bbox/spatial filters have limited effectiveness.
        We query with WHERE clause (which works reliably) and filter by
        bounding box in pandas after retrieval.
        
        Args:
            bbox: Bounding box with north, south, east, west keys.
            building_types: List of BLD_PUR values to filter.
            min_area_m2: Minimum building footprint area in m².
            
        Returns:
            GeoDataFrame of building polygons.
        """
        out_fields = ['OBJECTID', 'BUILD_ID', 'BUILD_TY', 'BUILD_NAME', 'BLD_PUR', 'SHAPE.AREA']
        
        # Build WHERE clause
        where_parts = []
        
        if building_types:
            type_list = "', '".join(building_types)
            where_parts.append(f"BLD_PUR IN ('{type_list}')")
        
        if min_area_m2 is not None:
            where_parts.append(f"SHAPE.AREA >= {min_area_m2}")
        
        where = ' AND '.join(where_parts) if where_parts else None
        
        # Query without bbox filter (bbox filter doesn't work reliably on this WFS)
        gdf = self._query_layer(
            layer_id=13,
            where=where,
            out_fields=out_fields
        )
        
        # Rename SHAPE.AREA to footprint_m2
        if len(gdf) > 0 and 'SHAPE.AREA' in gdf.columns:
            gdf.rename(columns={'SHAPE.AREA': 'footprint_m2'}, inplace=True)
        
        # Filter by bounding box in pandas (since WFS bbox filter doesn't work)
        if len(gdf) > 0 and bbox:
            gdf = gdf.cx[bbox['west']:bbox['east'], bbox['south']:bbox['north']]
            logger.info(f"Filtered to bbox: {len(gdf)} buildings remaining")
        
        return gdf
    
    def query_zoning(
        self,
        bbox: dict[str, float]
    ) -> gpd.GeoDataFrame:
        """Query zoning polygons from TheLIST.
        
        Note: WFS geometry/bbox filter has limited effectiveness on this service.
        We query all zones (filtered by WHERE if possible) and filter by bbox in pandas.
        
        Args:
            bbox: Bounding box with north, south, east, west keys.
            
        Returns:
            GeoDataFrame of zoning polygons with ZONE field.
        """
        out_fields = ['OBJECTID', 'ZONE', 'SHAPE.AREA']
        
        # Query without bbox (bbox filter doesn't work on this WFS)
        gdf = self._query_layer(
            layer_id=4,
            where="ZONE IS NOT NULL",  # Get all zones
            out_fields=out_fields
        )
        
        # Filter by bounding box in pandas
        if len(gdf) > 0 and bbox:
            gdf = gdf.cx[bbox['west']:bbox['east'], bbox['south']:bbox['north']]
            logger.info(f"Filtered zoning to bbox: {len(gdf)} zones remaining")
        
        return gdf
    
    def query_addresses(
        self,
        bbox: dict[str, float]
    ) -> gpd.GeoDataFrame:
        """Query address points from TheLIST.
        
        Note: WFS geometry/bbox filter has limited effectiveness on this service.
        We query all addresses and filter by bbox in pandas.
        
        Args:
            bbox: Bounding box with north, south, east, west keys.
            
        Returns:
            GeoDataFrame of address points.
        """
        out_fields = ['ST_NO_FROM', 'STREET', 'ST_TYPE', 'LOCALITY', 'POSTCODE', 'PROP_NAME']
        
        # Query without bbox (bbox filter doesn't work reliably)
        gdf = self._query_layer(
            layer_id=9,
            out_fields=out_fields
        )
        
        # Filter by bounding box in pandas
        if len(gdf) > 0 and bbox:
            gdf = gdf.cx[bbox['west']:bbox['east'], bbox['south']:bbox['north']]
            logger.info(f"Filtered addresses to bbox: {len(gdf)} addresses remaining")
        
        return gdf


def create_thelist_client(config: dict) -> TheLISTClient:
    """Factory function to create TheLIST client from config.
    
    Args:
        config: SolarQuoter configuration dictionary.
        
    Returns:
        Configured TheLISTClient instance.
    """
    thelist_config = config['thelist']
    wfs_url = thelist_config['wfs_url']
    
    return TheLISTClient(wfs_url=wfs_url)
