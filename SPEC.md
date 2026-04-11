# SolarQuoter — Tasmanian Commercial Solar Lead Generation Platform

## Overview
SolarQuoter identifies commercial properties suitable for solar installations by analyzing spatial data from Tasmania's TheLIST (Land Information System Tasmania).

## Architecture

### Pipeline Stages
1. **Phase 1: Lead Discovery** — Query TheLIST spatial layers for industrial/warehouse buildings
2. **Phase 2: Lead Scoring** — Score leads by roof area, zoning compliance, and proximity factors
3. **Phase 3: Lead Qualification** — Human-in-the-loop review and enrichment
4. **Phase 4: Outreach Generation** — Generate personalized outreach communications

## Data Sources

### TheLIST WFS Services
- **Endpoint**: https://services.thelist.tas.gov.au/arcgis/rest/services/Public/OpenDataWFS/MapServer/
- **Building Polygons** (Layer 13): `OBJECTID`, `BUILD_ID`, `BUILD_TY`, `BUILD_NAME`, `BLD_PUR`, `SHAPE.AREA`, `SHAPE`
- **Zoning** (Layer 4): `ZONE` field — values include 'General Industrial', 'Light Industrial', 'Commercial'
- **Address Points** (Layer 9): `ST_NO_FROM`, `STREET`, `ST_TYPE`, `LOCALITY`, `POSTCODE`, `PROP_NAME`, `SHAPE`

### Building Purpose Values (BLD_PUR field)
- Industrial, Warehouse, Factory, Cold Store, Commercial (manual review), Agricultural (large sheds)

## Regional Configuration

### NW Tasmania Bounding Box
- North: -40.0, South: -41.5, East: 145.8, West: 145.0

### Building Footprint Requirements
- Minimum: 200m² (configurable)
- Preferred: >500m²

## Output Schema

### raw_leads.parquet
| Column | Type | Description |
|--------|------|-------------|
| objectid | int64 | TheLIST OBJECTID |
| build_id | string | Building ID |
| build_ty | string | Building type |
| build_name | string | Building name |
| bld_pur | string | Building purpose |
| footprint_m2 | float64 | Footprint area in m² |
| geometry | geometry | Building polygon |
| centroid_lat | float64 | Centroid latitude |
| centroid_lon | float64 | Centroid longitude |
| zone | string | Zoning classification |
| street_number | string | Street number |
| street_name | string | Street name |
| street_type | string | Street type |
| locality | string | Locality |
| postcode | string | Postcode |
| full_address | string | Formatted full address |
| region | string | Region name |

### scored_leads.parquet
Additional columns: `solar_score`, `roof_area_est_m2`, `priority_tier`

### qualified_leads.parquet
Additional columns: `contact_name`, `contact_phone`, `contact_email`, `qualification_notes`

### outreach.parquet
Additional columns: `email_subject`, `email_body`, `sms_body`

## Configuration
All settings managed via `config.yaml` — no hardcoded values.

## Requirements
- pandas, geopandas, shapely, pyarrow, requests, pyyaml, owslib
- Python 3.x with osmnx 2.1.0
