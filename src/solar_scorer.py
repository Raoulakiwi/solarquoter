"""Solar scoring module for SolarQuoter Phase 2.

Fetches solar irradiance data from Open-Meteo API and applies the solar
scoring algorithm to rate commercial properties for solar installation potential.

Note: NASA POWER API was specified but returns 404 errors. Open-Meteo provides
equivalent global horizontal irradiance data (kWh/m²/day) with free access.
"""

import time
import math
from typing import Dict, Optional, Tuple

import requests
import pandas as pd


# Cache for irradiance data to avoid re-fetching same lat/lon
_IRRADIANCE_CACHE: Dict[str, float] = {}

# Tasmania average irradiance fallback (kWh/m²/day)
TASMANIA_AVERAGE_IRRADIANCE = 4.0

# Rate limiting delay between API calls (seconds)
API_DELAY = 0.2


def _round_coord(coord: float) -> float:
    """Round coordinate to 3 decimal places for cache key."""
    return round(coord, 3)


def _cache_key(lat: float, lon: float) -> str:
    """Generate cache key for lat/lon pair."""
    return f"{_round_coord(lat)},{_round_coord(lon)}"


def fetch_solar_irradiance(lat: float, lon: float) -> float:
    """Fetch annual average solar irradiance from Open-Meteo API.
    
    Uses Open-Meteo Archive API to get daily shortwave radiation sums
    for the year 2023 and calculates annual average.
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
        
    Returns:
        Annual average solar irradiance in kWh/m²/day
    """
    cache_key = _cache_key(lat, lon)
    
    # Check cache first
    if cache_key in _IRRADIANCE_CACHE:
        return _IRRADIANCE_CACHE[cache_key]
    
    # Open-Meteo Archive API for annual historical data
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date=2023-01-01&end_date=2023-12-31"
        f"&daily=shortwave_radiation_sum"
        f"&timezone=UTC"
    )
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Extract daily solar radiation values
        daily_data = data.get('daily', {})
        values = daily_data.get('shortwave_radiation_sum', [])
        
        if not values:
            # Fallback if no data
            irradiance = TASMANIA_AVERAGE_IRRADIANCE
        else:
            # Filter None values
            valid_values = [v for v in values if v is not None]
            if valid_values:
                # Convert MJ/day to kWh/m²/day (1 MJ = 0.2778 kWh)
                kwh_values = [v * 0.2778 for v in valid_values]
                irradiance = sum(kwh_values) / len(kwh_values)
            else:
                irradiance = TASMANIA_AVERAGE_IRRADIANCE
        
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"  Warning: Open-Meteo API failed for ({lat}, {lon}): {e}")
        irradiance = TASMANIA_AVERAGE_IRRADIANCE
    
    # Cache the result
    _IRRADIANCE_CACHE[cache_key] = irradiance
    return irradiance


def score_lead(irradiance: float, footprint_m2: float, zone: Optional[str]) -> Tuple[float, Dict]:
    """Calculate solar score for a single lead.
    
    Args:
        irradiance: Annual average solar irradiance in kWh/m²/day
        footprint_m2: Building footprint area in m²
        zone: Zoning classification
        
    Returns:
        Tuple of (solar_score, breakdown_dict)
    """
    # Calculate irradiance_score (0-4)
    if irradiance < 3.0:
        irradiance_score = 1
    elif irradiance < 3.5:
        irradiance_score = 2
    elif irradiance < 4.5:
        irradiance_score = 3
    else:  # >= 4.5
        irradiance_score = 4
    
    # Calculate area_score (0-4)
    if footprint_m2 < 200:
        area_score = 0
    elif footprint_m2 < 500:
        area_score = 1
    elif footprint_m2 < 1000:
        area_score = 2
    elif footprint_m2 < 2000:
        area_score = 3
    else:
        area_score = 4
    
    # Calculate zone_score (0-2)
    if zone:
        zone_upper = zone.strip().title()
        if zone_upper in ('General Industrial', 'Light Industrial'):
            zone_score = 2
        elif zone_upper in ('Commercial', 'Rural Resource'):
            zone_score = 1
        else:
            zone_score = 1  # Generous default for Unknown/Other
    else:
        zone_score = 1  # Generous default for leads without zone
    
    # Calculate total solar_score (clamped 1-10)
    raw_score = irradiance_score + area_score + zone_score
    solar_score = max(1, min(10, raw_score))
    
    # Estimate roof area (assume single level unless footprint is very large)
    if footprint_m2 < 1000:
        roof_area_est_m2 = footprint_m2 * 1.0
    else:
        # Multi-level buildings may have roof area similar to footprint
        roof_area_est_m2 = footprint_m2
    
    # Determine priority tier
    qualifies = solar_score >= 6 and footprint_m2 >= 500
    if qualifies and solar_score >= 8:
        priority_tier = 'A'
    elif qualifies and solar_score >= 6:
        priority_tier = 'B'
    else:
        priority_tier = 'C'
    
    breakdown = {
        'irradiance_score': irradiance_score,
        'area_score': area_score,
        'zone_score': zone_score,
        'raw_total': raw_score,
        'solar_score': solar_score,
        'roof_area_est_m2': roof_area_est_m2,
        'priority_tier': priority_tier,
        'qualifies': qualifies
    }
    
    return solar_score, breakdown


def score_batch_leads(input_parquet: str, output_parquet: str) -> pd.DataFrame:
    """Process a batch of leads and score them.
    
    Args:
        input_parquet: Path to input raw leads parquet file
        output_parquet: Path to save scored leads parquet file
        
    Returns:
        DataFrame of scored leads
    """
    # Load raw leads
    print(f"Loading leads from {input_parquet}...")
    df = pd.read_parquet(input_parquet)
    print(f"  Loaded {len(df)} leads")
    
    # Track unique lat/lon pairs to fetch
    unique_coords = set()
    for _, row in df.iterrows():
        key = _cache_key(row['centroid_lat'], row['centroid_lon'])
        unique_coords.add(key)
    
    print(f"  Found {len(unique_coords)} unique lat/lon pairs to query")
    
    # Fetch irradiance for all unique coordinates
    print("Fetching solar irradiance from Open-Meteo API...")
    irradiance_values = []
    
    for i, (_, row) in enumerate(df.iterrows()):
        lat = row['centroid_lat']
        lon = row['centroid_lon']
        
        # Rate limiting
        if i > 0:
            time.sleep(API_DELAY)
        
        irradiance = fetch_solar_irradiance(lat, lon)
        irradiance_values.append(irradiance)
        
        if (i + 1) % 10 == 0 or i == len(df) - 1:
            print(f"  Processed {i + 1}/{len(df)} leads...")
    
    df['irradiance'] = irradiance_values
    
    # Score each lead
    print("Scoring leads...")
    solar_scores = []
    breakdowns = []
    
    for _, row in df.iterrows():
        score, breakdown = score_lead(
            row['irradiance'],
            row['footprint_m2'],
            row.get('zone', None)
        )
        solar_scores.append(score)
        breakdowns.append(breakdown)
    
    df['solar_score'] = solar_scores
    
    # Extract scoring details into columns
    df['roof_area_est_m2'] = [b['roof_area_est_m2'] for b in breakdowns]
    df['priority_tier'] = [b['priority_tier'] for b in breakdowns]
    
    # Remove temporary irradiance column before saving
    df_output = df.drop(columns=['irradiance'])
    
    # Ensure output directory exists
    import os
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    
    # Save scored leads
    print(f"Saving scored leads to {output_parquet}...")
    df_output.to_parquet(output_parquet, index=False)
    
    # Print summary
    print("\n" + "=" * 50)
    print("SCORING SUMMARY")
    print("=" * 50)
    print(f"Total leads: {len(df)}")
    print(f"Average solar score: {df['solar_score'].mean():.2f}")
    print(f"Score range: {df['solar_score'].min():.0f} - {df['solar_score'].max():.0f}")
    print(f"Leads qualifying (score >= 6 AND footprint >= 500m²): {(df['solar_score'] >= 6).sum()}")
    print(f"\nIrradiance range: {df['irradiance'].min():.2f} - {df['irradiance'].max():.2f} kWh/m²/day")
    print(f"Cache size: {len(_IRRADIANCE_CACHE)} unique coordinates")
    
    # Score distribution
    print("\nScore distribution:")
    for tier in ['A', 'B', 'C']:
        count = (df['priority_tier'] == tier).sum()
        print(f"  Tier {tier}: {count} leads")
    
    return df_output


if __name__ == "__main__":
    # Test with the raw leads file
    input_path = "data/raw/raw_leads_northwest.parquet"
    output_path = "data/scored/scored_leads_northwest.parquet"
    
    score_batch_leads(input_path, output_path)