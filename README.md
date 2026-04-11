# SolarQuoter — Tasmanian Commercial Solar Lead Generation

Phase 1 implementation for discovering commercial solar leads from Tasmania's spatial data infrastructure (TheLIST).

## Overview

SolarQuoter identifies commercial and industrial properties suitable for solar installations by analyzing building footprints, zoning classifications, and address data from TheLIST (Land Information System Tasmania).

## Project Structure

```
solarquoter/
├── config.yaml           # Configuration (regions, filters, output paths)
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── SPEC.md              # Full project specification
├── src/
│   ├── __init__.py
│   ├── config.py        # Configuration loader
│   ├── data_schema.py   # Parquet schema definitions
│   ├── thelist_client.py # WFS client for TheLIST ArcGIS API
│   ├── spatial_utils.py  # Geometry and spatial operations
│   └── pipeline.py      # Phase 1 orchestrator
├── data/
│   ├── raw/             # Phase 1 output (raw_leads)
│   └── processed/       # Phase 2-4 output
└── tests/
```

## Phase 1: Lead Discovery

### What It Does

1. **Queries TheLIST Building Polygons** (Layer 13) for industrial/warehouse buildings in NW Tasmania
2. **Filters by footprint area** (minimum 200m², configurable)
3. **Cross-references with Zoning Layer** (Layer 4) — only General Industrial, Light Industrial, Commercial zones
4. **Links to Address Points** (Layer 9) via spatial join
5. **Outputs to Parquet** at `data/raw/raw_leads_northwest.parquet`

### Regional Configuration

Configurable regions in `config.yaml`:

| Region | Bounding Box | Postcodes |
|--------|-------------|-----------|
| northwest | S41.5°-40.0°, E145.0°-145.8° | 7300-7331 |
| north_launceston | S41.6°-41.4°, E146.85°-147.15° | 7250 |
| south_launceston | S41.6°-41.4°, E146.85°-147.15° | 7250 |

### Building Types Filtered

- **Primary**: Industrial, Warehouse, Factory, Cold Store
- **Secondary** (manual review): Commercial
- **Large sheds**: Agricultural

## Setup

### 1. Install Dependencies

```bash
pip install --user -r requirements.txt
```

Or with system packages:
```bash
pip install --break-system-packages -r requirements.txt
```

Required packages:
- pandas >= 2.0.0
- geopandas >= 0.14.0
- shapely >= 2.0.0
- pyarrow >= 14.0.0
- requests >= 2.31.0
- pyyaml >= 6.0
- owslib >= 0.29.0

### 2. Verify Python Environment

Use system Python3 (not virtual environment):
```bash
/usr/bin/python3 --version
```

## Usage

### Run Phase 1 Pipeline

```bash
cd /home/raoula/projects/solarquoter
/usr/bin/python3 src/pipeline.py
```

### Output

The pipeline generates `data/raw/raw_leads_northwest.parquet` with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| objectid | int64 | TheLIST OBJECTID |
| build_id | string | Building ID |
| build_ty | string | Building type |
| build_name | string | Building name |
| bld_pur | string | Building purpose |
| footprint_m2 | float64 | Footprint area in m² |
| geometry | geometry | Building polygon (Shapely) |
| centroid_lat | float64 | Centroid latitude |
| centroid_lon | float64 | Centroid longitude |
| zone | string | Zoning classification |
| street_number | string | Street number |
| street_name | string | Street name |
| street_type | string | Street type (St, Rd, etc.) |
| locality | string | Locality name |
| postcode | string | Postcode |
| full_address | string | Formatted address |
| region | string | Region name |

## Configuration

All settings are managed via `config.yaml`. Key settings:

```yaml
regions:
  northwest:
    bbox:
      north: -40.0
      south: -41.5
      east: 145.8
      west: 145.0

building_types:
  - Industrial
  - Warehouse
  - Factory
  - Cold Store
  - Commercial
  - Agricultural

min_footprint_m2: 200

allowed_zones:
  - General Industrial
  - Light Industrial
  - Commercial
```

## TheLIST WFS API

- **Endpoint**: https://services.thelist.tas.gov.au/arcgis/rest/services/Public/OpenDataWFS/MapServer/
- **Building Polygons**: Layer 13
- **Zoning**: Layer 4
- **Address Points**: Layer 9

## Troubleshooting

### No buildings found

- Verify bounding box coordinates are correct
- Check that TheLIST WFS is accessible
- Confirm building types exist in the region

### No addresses matched

- Some rural properties may not have address points
- Consider increasing `max_distance_m` in `spatial_join_buildings_addresses()`

### CRS issues

- The pipeline handles CRS conversion internally
- Buildings are projected to EPSG:32755 (UTM zone 55S) for distance calculations

## Future Phases

- **Phase 2**: Lead Scoring — score by roof area, zoning compliance, proximity
- **Phase 3**: Lead Qualification — human review and contact enrichment
- **Phase 4**: Outreach Generation — personalized email/SMS content
