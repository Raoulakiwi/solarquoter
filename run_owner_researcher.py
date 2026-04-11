#!/usr/bin/env python3
"""Test script for owner_researcher module.

Run Phase 3 owner research on scored_leads_northwest.parquet.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from owner_researcher import research_batch

def main():
    # Paths
    input_path = "data/scored/scored_leads_northwest.parquet"
    output_path = "data/qualified/qualified_leads_northwest.parquet"
    
    print("=" * 60)
    print("SolarQuoter Phase 3: Owner Research")
    print("=" * 60)
    print()
    
    # Run research
    summary = research_batch(input_path, output_path)
    
    # Print summary
    print()
    print("=" * 60)
    print("RESEARCH SUMMARY")
    print("=" * 60)
    print(f"Total leads processed:     {summary['total']}")
    print(f"ABN found:                 {summary['abn_found']}")
    print(f"Business name found:       {summary['business_name_found']}")
    print(f"Contact info (email/phone): {summary['contact_info']}")
    print(f"No information found:       {summary['no_info']}")
    print()
    print(f"Output saved to: {output_path}")
    print()

if __name__ == "__main__":
    main()