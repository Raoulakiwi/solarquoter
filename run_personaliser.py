#!/usr/bin/env python3
"""Test script for the personaliser module."""

import os
import yaml

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.personaliser import (
    personalise_batch,
    generate_personalised_email,
    generate_personalised_sms,
    generate_microsite_html,
    calculate_savings_estimate,
    make_slug,
    get_first_name,
    get_company_name
)


def load_config():
    """Load configuration from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def test_helpers():
    """Test helper functions."""
    print("Testing helper functions...")
    
    # Test make_slug
    assert make_slug("CREATIVE PAPER TASMANIA PTY LTD") == "creative-paper-tasmania-pty-ltd"
    assert make_slug("Duck River Co-op") == "duck-river-co-op"
    assert make_slug("Test  Special!@#Chars") == "test-specialchars"
    assert make_slug(None) == "lead"
    print("  make_slug: OK")
    
    # Test get_first_name
    assert get_first_name("John Smith") == "John"
    assert get_first_name("Jane") == "Jane"
    assert get_first_name(None) == "there"
    assert get_first_name("") == "there"
    print("  get_first_name: OK")
    
    # Test get_company_name
    assert "CREATIVE PAPER" in get_company_name("CREATIVE PAPER TASMANIA PTY LTD", None, None)
    assert "business at" in get_company_name(None, "123 Main St", None)
    assert get_company_name(None, None, None) == "your business"
    print("  get_company_name: OK")
    
    # Test calculate_savings_estimate
    savings = calculate_savings_estimate(1000, 4.5)
    assert savings['kwh_estimate'] == 169.0  # 1000 * 4.5 * 0.15 * 0.25
    assert savings['savings_estimate'] == 51.0  # 168.75 * 0.30
    assert savings['kw_installed'] == 0.03  # (1000 * 0.25 * 0.1) / 1000
    print("  calculate_savings_estimate: OK")
    
    print("All helper tests passed!")


def test_personaliser():
    """Test the personaliser on sample data."""
    print("\nTesting personaliser...")
    
    config = load_config()
    
    # Use qualified leads file
    input_parquet = 'data/qualified/qualified_leads_northwest.parquet'
    output_parquet = 'data/outreach/ready_leads_northwest.parquet'
    microsites_dir = 'microsites'
    
    # Ensure data directory exists for output
    os.makedirs('data/outreach', exist_ok=True)
    
    result = personalise_batch(
        input_parquet=input_parquet,
        output_parquet=output_parquet,
        microsites_dir=microsites_dir,
        config=config
    )
    
    print(f"\nResults:")
    print(f"  Emails generated: {result['emails_generated']}")
    print(f"  SMS generated: {result['sms_generated']}")
    print(f"  Microsites created: {result['microsites_created']}")
    
    return result


if __name__ == '__main__':
    test_helpers()
    test_personaliser()
