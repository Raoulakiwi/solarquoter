#!/usr/bin/env python3
"""Test script for Phase 2: Solar Scoring.

Runs the solar scorer on raw_leads_northwest.parquet and prints results.
"""

import sys
import os

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from solar_scorer import score_batch_leads

if __name__ == "__main__":
    input_path = "data/raw/raw_leads_northwest.parquet"
    output_path = "data/scored/scored_leads_northwest.parquet"
    
    # Run scorer
    df = score_batch_leads(input_path, output_path)
    
    # Print detailed score breakdown
    print("\n" + "=" * 50)
    print("DETAILED RESULTS")
    print("=" * 50)
    
    # Score distribution
    print("\nSolar Score Distribution:")
    score_counts = df['solar_score'].value_counts().sort_index()
    for score, count in score_counts.items():
        bar = '█' * count
        print(f"  {score:5.1f} | {bar} ({count})")
    
    # Irradiance stats
    print(f"\nIrradiance Statistics (kWh/m²/day):")
    print(f"  Min: {df['irradiance'].min():.3f}")
    print(f"  Max: {df['irradiance'].max():.3f}")
    print(f"  Mean: {df['irradiance'].mean():.3f}")
    print(f"  Std: {df['irradiance'].std():.3f}")
    
    # Zone distribution in qualified leads
    qualified = df[(df['solar_score'] >= 6) & (df['footprint_m2'] >= 500)]
    print(f"\nQualified Leads: {len(qualified)}")
    if len(qualified) > 0:
        print("\nQualified leads by zone:")
        zone_counts = qualified['zone'].value_counts()
        for zone, count in zone_counts.items():
            print(f"  {zone}: {count}")
        
        print("\nQualified leads by priority tier:")
        tier_counts = qualified['priority_tier'].value_counts()
        for tier, count in tier_counts.items():
            print(f"  Tier {tier}: {count}")
    
    print(f"\nOutput saved to: {output_path}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")