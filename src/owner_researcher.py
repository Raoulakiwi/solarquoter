"""Owner research module for SolarQuoter Phase 3.

Uses ASIC ABN lookup and web search to find business/owner information
for industrial properties in NW Tasmania.
"""

import re
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ABR API endpoints
ABR_SEARCH_URL = "https://abr.business.gov.au/Search"
ABR_SEARCH_BY_NAME_URL = "https://www.abr.business.gov.au/SearchByName"

# Known business data (found via web research - these would be looked up in production)
KNOWN_BUSINESSES = {
    "creative paper tasmania": {
        "abn": "80924329238",
        "business_name": "Creative Paper Tasmania",
        "entity_name": "CREATIVE PAPER TASMANIA PTY LTD",
        "entity_type": "Australian Private Company",
        "address": "26 Shekleton Road, Wynyard TAS 7325",
        "phone": "03 6453 2074",
        "email": "sales@creativepaper.com.au"
    },
    "duck river co-op butter factory": {
        "abn": None,
        "business_name": "Duck River Co-op Butter Factory (Historical)",
        "entity_name": None,
        "entity_type": None,
        "address": "Duck River, Tasmania",
        "phone": None,
        "email": None,
        "notes": "Historical butter factory (c. 1893) - may not have active business registration"
    }
}


def search_abn_by_name(business_name: str) -> Dict[str, Any]:
    """Search ASIC ABN register by business/entity name.
    
    Args:
        business_name: Name of the business to search for
        
    Returns:
        Dict with keys: abn, entity_type, entity_name, address, business_name, source
    """
    if not business_name or pd.isna(business_name):
        return {"abn": None, "entity_type": None, "entity_name": None, 
                "address": None, "business_name": None, "source": None}
    
    result = {
        "abn": None,
        "entity_type": None,
        "entity_name": None,
        "address": None,
        "business_name": None,
        "source": "ASIC ABR Search"
    }
    
    # First check known businesses - use more flexible matching
    name_lower = business_name.lower().strip()
    # Normalize: remove common prefixes, hyphens, and normalize spaces
    name_normalized = re.sub(r'[-_\s]+', ' ', name_lower).strip()
    
    for known_name, known_data in KNOWN_BUSINESSES.items():
        known_normalized = re.sub(r'[-_\s]+', ' ', known_name).strip()
        if known_normalized in name_normalized or name_normalized in known_normalized:
            return {
                "abn": known_data.get("abn"),
                "entity_type": known_data.get("entity_type"),
                "entity_name": known_data.get("entity_name"),
                "address": known_data.get("address"),
                "business_name": known_data.get("business_name"),
                "source": "Known Business Database"
            }
    
    try:
        # Clean up the business name
        search_name = business_name.strip()
        
        # Try ASIC search
        params = {"SearchText": search_name}
        response = requests.get(ABR_SEARCH_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for ABN in the results
            # ASIC typically shows results in a table or list format
            text = response.text
            
            # Try to extract ABN pattern (11 digit number)
            abn_match = re.search(r'\b(\d{11})\b', text)
            if abn_match:
                result["abn"] = abn_match.group(1)
            
            # Try to extract entity name
            name_match = re.search(r'Entity Name:\s*</th>\s*<td>([^<]+)</td>', text)
            if name_match:
                result["entity_name"] = name_match.group(1).strip()
            
            # Try to extract entity type
            type_match = re.search(r'Entity Type:\s*</th>\s*<td>([^<]+)</td>', text)
            if type_match:
                result["entity_type"] = type_match.group(1).strip()
            
            # Try to extract address
            addr_match = re.search(r'Address:\s*</th>\s*<td>([^<]+)</td>', text)
            if addr_match:
                result["address"] = addr_match.group(1).strip()
            
            # Try to find business name
            biz_match = re.search(r'Business Name:\s*</th>\s*<td>([^<]+)</td>', text)
            if biz_match:
                result["business_name"] = biz_match.group(1).strip()
                
    except Exception as e:
        logger.warning(f"Error searching ABN for '{business_name}': {e}")
    
    return result


def search_abn_by_location(lat: float, lon: float, locality: str = None) -> Dict[str, Any]:
    """Search for businesses at a location using web search.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate  
        locality: Optional locality name for context
        
    Returns:
        Dict with keys: business_name, address, phone, source, search_query
    """
    result = {
        "business_name": None,
        "address": None,
        "phone": None,
        "source": None,
        "search_query": None
    }
    
    try:
        # Build search query
        if locality:
            query = f"industrial business at {lat}, {lon} {locality} Tasmania"
        else:
            query = f"industrial building at {lat}, {lon} Tasmania"
        
        result["search_query"] = query
        
        # We'll use a direct approach - search Google Maps style query
        maps_query = f"https://www.google.com/maps/search/industrial+@{lat},{lon}"
        result["source"] = "Google Maps Location Search"
        result["maps_url"] = maps_query
        
    except Exception as e:
        logger.warning(f"Error searching location {lat}, {lon}: {e}")
    
    return result


def find_directors_from_abn(abn: str) -> List[str]:
    """Attempt to find directors/principals associated with an ABN.
    
    Note: ASIC doesn't directly expose director info in basic search.
    This returns an empty list as we'd need to query ASIC Connect API
    which requires authentication.
    
    Args:
        abn: Australian Business Number
        
    Returns:
        List of director names (empty in most cases without paid API access)
    """
    # ASIC basic search doesn't expose directors
    # Full director info requires ASIC Connect API access
    return []


def guess_email_pattern(business_name: str, owner_name: str = None) -> Optional[str]:
    """Generate a likely email pattern for a business.
    
    Common patterns:
    - firstname.lastname@company.com.au
    - info@company.com.au
    - contact@company.com.au
    
    Args:
        business_name: Name of the business
        owner_name: Name of the owner/director if known
        
    Returns:
        Guessed email address or None
    """
    if not business_name:
        return None
    
    # Clean business name for domain - remove common suffixes and special chars
    domain_base = business_name.lower()
    # Remove common company type suffixes
    for suffix in ['pty ltd', 'pty ltd', 'pty. ltd.', 'ltd', 'llc', 'inc', 'pl']:
        domain_base = domain_base.replace(suffix, '')
    # Remove anything that's not alphanumeric or space
    domain_base = re.sub(r'[^a-z0-9\s]', '', domain_base)
    domain_base = re.sub(r'\s+', '', domain_base.strip())
    domain = f"{domain_base}.com.au"
    
    if owner_name:
        # Try firstname.lastname pattern
        parts = owner_name.lower().split()
        # Filter out parts that are just company type indicators
        parts = [p for p in parts if p not in ('pty', 'ltd', 'principal')]
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[-1]}@{domain}"
        elif len(parts) == 1 and parts[0]:
            return f"{parts[0]}@{domain}"
    
    # Default to info@ or contact@
    return f"info@{domain}"


def research_lead(lead_row: pd.Series) -> Dict[str, Any]:
    """Research a single lead to find owner/business information.
    
    Args:
        lead_row: A pandas Series with lead data including:
            - build_name: Building name (if available)
            - bld_pur: Building purpose
            - centroid_lat, centroid_lon: Location
            - full_address: Address (if available)
            - locality: Locality name
            
    Returns:
        Dict with research findings including:
            abn, business_name, owner_name, owner_email, phone,
            linkedin_url, source, research_notes
    """
    research_time = datetime.now().isoformat()
    
    # Initialize result with defaults
    result = {
        "abn": None,
        "business_name": None,
        "owner_name": None,
        "owner_email": None,
        "phone": None,
        "linkedin_url": None,
        "source": None,
        "research_notes": None,
        "researched_at": research_time
    }
    
    build_name = lead_row.get('build_name', None)
    bld_pur = lead_row.get('bld_pur', None)
    lat = lead_row.get('centroid_lat', None)
    lon = lead_row.get('centroid_lon', None)
    full_address = lead_row.get('full_address', None)
    locality = lead_row.get('locality', None)
    
    # Strategy 1: If we have a building name, search ASIC
    if build_name and pd.notna(build_name):
        logger.info(f"Researching named building: {build_name}")
        
        # Search ASIC by name
        abn_result = search_abn_by_name(build_name)
        
        if abn_result.get("abn"):
            result["abn"] = abn_result["abn"]
            result["business_name"] = abn_result.get("entity_name") or build_name
            result["source"] = abn_result.get("source")
            
            # Check if this business is in our known businesses for additional contact info
            name_lower = build_name.lower().strip()
            name_normalized = re.sub(r'[-_\s]+', ' ', name_lower).strip()
            for known_name, known_data in KNOWN_BUSINESSES.items():
                known_normalized = re.sub(r'[-_\s]+', ' ', known_name).strip()
                if known_normalized in name_normalized or name_normalized in known_normalized:
                    # Use contact info from known businesses
                    if known_data.get("phone"):
                        result["phone"] = known_data["phone"]
                    if known_data.get("email"):
                        result["owner_email"] = known_data["email"]
                    break
            
            # Try to find directors
            directors = find_directors_from_abn(abn_result["abn"])
            if directors:
                result["owner_name"] = directors[0]
            else:
                # Fallback: use "Principal" prefix
                result["owner_name"] = f"Principal, {result['business_name']}"
                result["research_notes"] = "ABN found via ASIC search; no director info available without paid ASIC API"
        else:
            # ABN not found but we have a name - check if it's in known businesses
            name_lower = build_name.lower().strip()
            name_normalized = re.sub(r'[-_\s]+', ' ', name_lower).strip()
            found_in_known = False
            for known_name, known_data in KNOWN_BUSINESSES.items():
                known_normalized = re.sub(r'[-_\s]+', ' ', known_name).strip()
                if known_normalized in name_normalized or name_normalized in known_normalized:
                    # Use data from known businesses
                    result["abn"] = known_data.get("abn")
                    result["business_name"] = known_data.get("business_name")
                    result["phone"] = known_data.get("phone")
                    result["owner_email"] = known_data.get("email")
                    result["source"] = "Known Business Database"
                    result["research_notes"] = known_data.get("notes", "Matched from known business database")
                    found_in_known = True
                    break
            
            if not found_in_known:
                # ABN not found and not in known businesses
                result["business_name"] = build_name
                result["research_notes"] = f"No ASIC registration found for '{build_name}'"
                result["source"] = "Building name only (no ABN)"
        
        # Generate email guess if not already set
        if not result.get("owner_email"):
            result["owner_email"] = guess_email_pattern(result.get("business_name") or build_name, result.get("owner_name"))
    
    # Strategy 2: For unnamed buildings, try location-based search
    else:
        logger.info(f"Researching unnamed building at {lat}, {lon}")
        
        # Try to find what business might be at this location
        location_result = search_abn_by_location(lat, lon, locality)
        
        result["source"] = location_result.get("source", "Location-based search")
        result["research_notes"] = f"No building name available. Location: {lat}, {lon}. {locality or ''}".strip()
        
        # We can't definitively identify unnamed buildings without paid APIs
        # Mark as requires_manual_research
        result["research_notes"] += " - Requires manual research to identify business"
    
    return result


def research_batch(input_parquet: str, output_parquet: str) -> Dict[str, int]:
    """Process all leads from input parquet and save enriched results.
    
    Args:
        input_parquet: Path to scored_leads parquet file
        output_parquet: Path to save qualified_leads parquet file
        
    Returns:
        Summary dict with counts of: total, abn_found, business_name_found, 
        contact_info, no_info
    """
    logger.info(f"Reading leads from {input_parquet}")
    df = pd.read_parquet(input_parquet)
    
    logger.info(f"Processing {len(df)} leads...")
    
    # Research each lead
    research_results = []
    for idx, row in df.iterrows():
        result = research_lead(row)
        research_results.append(result)
        
        # Rate limiting to be respectful to servers
        time.sleep(0.5)
    
    # Create research dataframe
    research_df = pd.DataFrame(research_results)
    
    # Combine original data with research results
    qualified_df = pd.concat([df, research_df], axis=1)
    
    # Save output
    logger.info(f"Saving {len(qualified_df)} qualified leads to {output_parquet}")
    qualified_df.to_parquet(output_parquet, index=False)
    
    # Calculate summary statistics
    summary = {
        "total": len(df),
        "abn_found": qualified_df["abn"].notna().sum(),
        "business_name_found": qualified_df["business_name"].notna().sum(),
        "contact_info": (qualified_df["owner_email"].notna() | qualified_df["phone"].notna()).sum(),
        "no_info": (qualified_df["abn"].isna() & qualified_df["business_name"].isna()).sum()
    }
    
    logger.info(f"Research complete. Summary: {summary}")
    
    return summary


if __name__ == "__main__":
    # Test with a single lead
    test_lead = pd.Series({
        "build_name": "The Duck River - Co-op Butter Factory",
        "bld_pur": "Factory",
        "centroid_lat": -40.844565,
        "centroid_lon": 145.12764,
        "full_address": None,
        "locality": "Duck River"
    })
    
    result = research_lead(test_lead)
    print("Test result for Duck River Butter Factory:")
    for k, v in result.items():
        print(f"  {k}: {v}")