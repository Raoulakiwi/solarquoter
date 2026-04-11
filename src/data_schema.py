"""Parquet schema definitions for SolarQuoter pipeline stages.

These schemas define the expected column types for each pipeline stage,
ensuring consistency across the lead generation workflow.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RawLeadSchema:
    """Schema for raw_leads.parquet (Phase 1 output)."""
    
    # TheLIST Building fields
    objectid: int
    build_id: str
    build_ty: str
    build_name: str
    bld_pur: str
    footprint_m2: float
    
    # Geometry
    geometry: object  # shapely geometry
    
    # Centroid coordinates
    centroid_lat: float
    centroid_lon: float
    
    # Zoning
    zone: str
    
    # Address fields
    street_number: str
    street_name: str
    street_type: str
    locality: str
    postcode: str
    full_address: str
    
    # Metadata
    region: str


@dataclass
class ScoredLeadSchema:
    """Schema for scored_leads.parquet (Phase 2 output).
    
    Extends RawLeadSchema with scoring fields.
    """
    
    # Inherited from RawLeadSchema
    objectid: int
    build_id: str
    build_ty: str
    build_name: str
    bld_pur: str
    footprint_m2: float
    geometry: object
    centroid_lat: float
    centroid_lon: float
    zone: str
    street_number: str
    street_name: str
    street_type: str
    locality: str
    postcode: str
    full_address: str
    region: str
    
    # Phase 2 additions
    solar_score: float  # 0-100 score
    roof_area_est_m2: float  # Estimated roof area (may exceed footprint for multi-level)
    priority_tier: str  # 'A', 'B', or 'C'


@dataclass
class QualifiedLeadSchema:
    """Schema for qualified_leads.parquet (Phase 3 output).
    
    Extends ScoredLeadSchema with contact and qualification fields.
    """
    
    # Inherited from ScoredLeadSchema
    objectid: int
    build_id: str
    build_ty: str
    build_name: str
    bld_pur: str
    footprint_m2: float
    geometry: object
    centroid_lat: float
    centroid_lon: float
    zone: str
    street_number: str
    street_name: str
    street_type: str
    locality: str
    postcode: str
    full_address: str
    region: str
    solar_score: float
    roof_area_est_m2: float
    priority_tier: str
    
    # Phase 3 additions
    contact_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    qualification_notes: str


@dataclass
class OutreachSchema:
    """Schema for outreach.parquet (Phase 4 output).
    
    Extends QualifiedLeadSchema with personalized outreach content.
    """
    
    # Inherited from QualifiedLeadSchema
    objectid: int
    build_id: str
    build_ty: str
    build_name: str
    bld_pur: str
    footprint_m2: float
    geometry: object
    centroid_lat: float
    centroid_lon: float
    zone: str
    street_number: str
    street_name: str
    street_type: str
    locality: str
    postcode: str
    full_address: str
    region: str
    solar_score: float
    roof_area_est_m2: float
    priority_tier: str
    contact_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    qualification_notes: str
    
    # Phase 4 additions
    email_subject: str
    email_body: str
    sms_body: str


# Column lists for each stage (useful for DataFrame operations)
RAW_LEAD_COLUMNS = [
    'objectid', 'build_id', 'build_ty', 'build_name', 'bld_pur',
    'footprint_m2', 'geometry', 'centroid_lat', 'centroid_lon',
    'zone', 'street_number', 'street_name', 'street_type',
    'locality', 'postcode', 'full_address', 'region'
]

SCORED_LEAD_COLUMNS = RAW_LEAD_COLUMNS + [
    'solar_score', 'roof_area_est_m2', 'priority_tier'
]

QUALIFIED_LEAD_COLUMNS = SCORED_LEAD_COLUMNS + [
    'contact_name', 'contact_phone', 'contact_email', 'qualification_notes'
]

OUTREACH_COLUMNS = QUALIFIED_LEAD_COLUMNS + [
    'email_subject', 'email_body', 'sms_body'
]
