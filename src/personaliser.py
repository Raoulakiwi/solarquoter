"""Personalisation module for SolarQuoter Phase 4.

Generates personalized email, SMS, and microsite HTML for qualified leads.
"""

import re
import os
from typing import Dict, Optional, Any

import pandas as pd


def calculate_savings_estimate(footprint_m2: float, irradiance: float = 4.5) -> Dict[str, float]:
    """Calculate estimated annual savings and installation size.
    
    Args:
        footprint_m2: Roof footprint area in square metres
        irradiance: Solar irradiance estimate (kWh/m²/year, default 4.5 for NW Tasmania)
    
    Returns:
        Dict with kwh_estimate, savings_estimate, kw_installed
    """
    # Formula from spec: footprint_m2 × irradiance × 0.15 × 0.25 as rough kWh
    efficiency_factor = 0.15  # Panel efficiency
    panel_coverage = 0.25    # What fraction of roof is panel-covered
    
    kwh_estimate = footprint_m2 * irradiance * efficiency_factor * panel_coverage
    savings_estimate = kwh_estimate * 0.30  # $0.30/kWh electricity cost
    
    # Solar installation: 100W per m² panel density, $800-$1200 per kW
    kw_installed = (footprint_m2 * panel_coverage * 0.1) / 1000  # kW
    
    return {
        'kwh_estimate': round(kwh_estimate, 0),
        'savings_estimate': round(savings_estimate, 0),
        'kw_installed': round(kw_installed, 2)
    }


def make_slug(text: str) -> str:
    """Convert text to URL-safe slug.
    
    Args:
        text: Text to slugify
    
    Returns:
        URL-safe slug
    """
    if not text:
        return "lead"
    # Lowercase, replace spaces with hyphens, strip special chars
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_first_name(owner_name: Optional[str]) -> str:
    """Extract first name from owner_name.
    
    Args:
        owner_name: Full owner name
    
    Returns:
        First name or 'there' as fallback
    """
    if not owner_name or pd.isna(owner_name):
        return "there"
    parts = str(owner_name).strip().split()
    if parts:
        return parts[0]
    return "there"


def get_company_name(business_name: Optional[str], address: Optional[str], full_address: Optional[str]) -> str:
    """Get company name with fallback.
    
    Args:
        business_name: Business name if available
        address: Building address
        full_address: Full formatted address
    
    Returns:
        Company name or fallback string
    """
    if business_name and not pd.isna(business_name):
        return str(business_name)
    if address and not pd.isna(address):
        return f"the business at {address}"
    if full_address and not pd.isna(full_address):
        return f"the business at {full_address}"
    return "your business"


def generate_personalised_email(lead_row: pd.Series, config: Dict[str, Any]) -> Dict[str, str]:
    """Generate personalized email content for a lead.
    
    Args:
        lead_row: Row from qualified_leads DataFrame
        config: Configuration dict with agent and microsite settings
    
    Returns:
        Dict with subject, body, first_name
    """
    first_name = get_first_name(lead_row.get('owner_name'))
    company_name = get_company_name(
        lead_row.get('business_name'),
        lead_row.get('full_address'),
        None
    )
    
    address = lead_row.get('full_address') or "the identified site"
    footprint_m2 = lead_row.get('footprint_m2', 0)
    locality = lead_row.get('locality') or "local"
    if pd.isna(locality):
        locality = "local"
    
    # Generate microsite URL
    business_name = lead_row.get('business_name')
    if business_name and not pd.isna(business_name):
        slug = make_slug(business_name)
    else:
        slug = make_slug(str(lead_row.get('build_id', 'lead')))
    
    lead_id = str(lead_row.get('objectid', '001'))
    microsite_filename = f"{lead_id}_{slug}.html"
    site_url = config.get('microsite_base_url', '') + microsite_filename
    
    # Build email
    agent_name = config.get('agent', {}).get('name', 'Ben')
    agent_email = config.get('agent', {}).get('email', 'ben@solaranalytics.com.au')
    
    subject = f"{first_name}, {company_name} rooftop could cut your power bills significantly"
    
    body = f"""Hi {first_name},

I'm reaching out because our solar analysis identified {company_name}'s
rooftop at {address} as one of Tasmania's most viable commercial
solar sites.

Based on {footprint_m2:.0f}m² of north-facing roof space and Tasmania's
best solar irradiance in the {locality} area, a solar installation
here could generate significant savings on your energy bills.

We've already prepared a personalised analysis for {company_name}:
{site_url}

Are you the right person to speak with about energy costs for
{company_name}? Happy to share more details.

Regards,
{agent_name}
Solar Analytics Tasmania
{agent_email}"""
    
    return {
        'subject': subject,
        'body': body,
        'first_name': first_name
    }


def generate_personalised_sms(lead_row: pd.Series, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Generate personalized SMS for a lead.
    
    Args:
        lead_row: Row from qualified_leads DataFrame
        config: Configuration dict with agent settings
    
    Returns:
        Dict with sms_text, phone, or None if no phone available
    """
    phone = lead_row.get('phone')
    if not phone or pd.isna(phone):
        return None
    
    first_name = get_first_name(lead_row.get('owner_name'))
    company_name = get_company_name(
        lead_row.get('business_name'),
        lead_row.get('full_address'),
        None
    )
    footprint_m2 = lead_row.get('footprint_m2', 0)
    agent_phone = config.get('agent', {}).get('phone', '+61 400 000 000')
    
    sms_text = f"{first_name} — quick follow-up on the solar analysis we sent to {company_name}. {footprint_m2:.0f}m² roof, strong sun, no upfront cost option available. Happy to chat? {agent_phone}"
    
    return {
        'sms_text': sms_text,
        'phone': str(phone)
    }


def generate_microsite_html(lead_row: pd.Series, config: Dict[str, Any]) -> str:
    """Generate personalized microsite HTML for a lead.
    
    Args:
        lead_row: Row from qualified_leads DataFrame
        config: Configuration dict with agent settings
    
    Returns:
        Complete HTML string
    """
    company_name = get_company_name(
        lead_row.get('business_name'),
        lead_row.get('full_address'),
        None
    )
    
    address = lead_row.get('full_address') or "the identified site"
    footprint_m2 = lead_row.get('footprint_m2', 0)
    locality = lead_row.get('locality') or "North West Tasmania"
    if pd.isna(locality):
        locality = "North West Tasmania"
    
    irradiance = 4.5  # NW Tasmania average
    savings = calculate_savings_estimate(footprint_m2, irradiance)
    
    agent_name = config.get('agent', {}).get('name', 'Ben')
    agent_phone = config.get('agent', {}).get('phone', '+61 400 000 000')
    agent_email = config.get('agent', {}).get('email', 'ben@solaranalytics.com.au')
    agent_website = config.get('agent', {}).get('website', 'https://solaranalytics.com.au')
    
    # Generate slug for filename
    business_name = lead_row.get('business_name')
    if business_name and not pd.isna(business_name):
        slug = make_slug(business_name)
    else:
        slug = make_slug(str(lead_row.get('build_id', 'lead')))
    lead_id = str(lead_row.get('objectid', '001'))
    microsite_filename = f"{lead_id}_{slug}.html"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Solar Analysis | Solar Analytics Tasmania</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #FF6B35 0%, #FF8C42 100%); color: white; padding: 40px 20px; text-align: center; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ font-size: 18px; opacity: 0.9; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 40px 20px; }}
        .property-card {{ background: #f8f9fa; border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .property-card h2 {{ color: #FF6B35; margin-bottom: 15px; font-size: 24px; }}
        .property-details {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
        .detail-item {{ background: white; padding: 15px; border-radius: 8px; }}
        .detail-label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        .detail-value {{ font-size: 18px; font-weight: 600; color: #333; margin-top: 5px; }}
        .savings-section {{ background: linear-gradient(135deg, #2E7D32 0%, #4CAF50 100%); color: white; border-radius: 12px; padding: 30px; margin-bottom: 30px; text-align: center; }}
        .savings-section h3 {{ font-size: 16px; opacity: 0.9; margin-bottom: 10px; }}
        .savings-amount {{ font-size: 48px; font-weight: 700; }}
        .savings-note {{ font-size: 14px; opacity: 0.8; margin-top: 10px; }}
        .installation-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
        .installation-item {{ background: #e8f5e9; padding: 20px; border-radius: 8px; text-align: center; }}
        .installation-item .value {{ font-size: 24px; font-weight: 600; color: #2E7D32; }}
        .installation-item .label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .cta-section {{ background: #333; color: white; border-radius: 12px; padding: 40px; text-align: center; }}
        .cta-section h3 {{ font-size: 24px; margin-bottom: 15px; }}
        .cta-section p {{ opacity: 0.8; margin-bottom: 25px; }}
        .cta-phone {{ font-size: 28px; font-weight: 700; color: #FF8C42; text-decoration: none; }}
        .cta-email {{ font-size: 18px; color: #FF8C42; text-decoration: none; display: block; margin-top: 10px; }}
        .footer {{ text-align: center; padding: 30px; color: #666; font-size: 14px; }}
        .footer a {{ color: #FF6B35; text-decoration: none; }}
        @media (max-width: 600px) {{ .property-details, .installation-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{company_name}</h1>
        <p>Personalised Solar Analysis for {address}</p>
    </div>
    
    <div class="container">
        <div class="property-card">
            <h2>Your Property Details</h2>
            <div class="property-details">
                <div class="detail-item">
                    <div class="detail-label">Address</div>
                    <div class="detail-value">{address}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Locality</div>
                    <div class="detail-value">{locality}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Rooftop Size</div>
                    <div class="detail-value">{footprint_m2:,.0f} m²</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Region</div>
                    <div class="detail-value">North West Tasmania</div>
                </div>
            </div>
        </div>
        
        <div class="savings-section">
            <h3>Estimated Annual Savings</h3>
            <div class="savings-amount">${savings['savings_estimate']:,.0f}</div>
            <div class="savings-note">Based on {savings['kwh_estimate']:,.0f} kWh annual production at $0.30/kWh</div>
        </div>
        
        <div class="installation-grid">
            <div class="installation-item">
                <div class="value">{savings['kw_installed']:.1f} kW</div>
                <div class="label">Estimated System Size</div>
            </div>
            <div class="installation-item">
                <div class="value">$0</div>
                <div class="label">No Upfront Cost Option</div>
            </div>
        </div>
        
        <div class="cta-section">
            <h3>Ready to Learn More?</h3>
            <p>Our team at Solar Analytics Tasmania is ready to discuss your solar opportunities.</p>
            <a href="tel:{agent_phone.replace(' ', '')}" class="cta-phone">{agent_phone}</a>
            <a href="mailto:{agent_email}" class="cta-email">{agent_email}</a>
        </div>
        
        <div class="footer">
            <p>Prepared by <a href="{agent_website}">Solar Analytics Tasmania</a></p>
            <p>Serving NW Tasmania including {locality}</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


def personalise_batch(
    input_parquet: str,
    output_parquet: str,
    microsites_dir: str,
    config: Dict[str, Any]
) -> Dict[str, int]:
    """Process all leads from a qualified leads parquet file.
    
    Args:
        input_parquet: Path to input qualified_leads.parquet
        output_parquet: Path to output outreach parquet
        microsites_dir: Directory to write microsite HTML files
        config: Configuration dict
    
    Returns:
        Dict with counts: emails_generated, sms_generated, microsites_created
    """
    # Load qualified leads
    df = pd.read_parquet(input_parquet)
    
    emails_generated = 0
    sms_generated = 0
    microsites_created = 0
    
    results = []
    
    for idx, row in df.iterrows():
        lead_result = row.to_dict()
        
        # Generate email
        email_data = generate_personalised_email(row, config)
        lead_result['email_subject'] = email_data['subject']
        lead_result['email_body'] = email_data['body']
        emails_generated += 1
        
        # Check if outreach should include email (owner_email required)
        if row.get('owner_email') and not pd.isna(row.get('owner_email')):
            lead_result['email_outreach'] = True
        else:
            lead_result['email_outreach'] = False
        
        # Generate SMS (only if phone available)
        sms_data = generate_personalised_sms(row, config)
        if sms_data:
            lead_result['sms_body'] = sms_data['sms_text']
            sms_generated += 1
        else:
            lead_result['sms_body'] = None
        
        # Generate microsite HTML
        html = generate_microsite_html(row, config)
        
        # Create microsite filename
        business_name = row.get('business_name')
        if business_name and not pd.isna(business_name):
            slug = make_slug(business_name)
        else:
            slug = make_slug(str(row.get('build_id', 'lead')))
        lead_id = str(row.get('objectid', str(idx).zfill(3)))
        microsite_filename = f"{lead_id}_{slug}.html"
        
        # Write microsite HTML
        os.makedirs(microsites_dir, exist_ok=True)
        microsite_path = os.path.join(microsites_dir, microsite_filename)
        with open(microsite_path, 'w', encoding='utf-8') as f:
            f.write(html)
        microsites_created += 1
        
        results.append(lead_result)
    
    # Create output DataFrame
    output_df = pd.DataFrame(results)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    output_df.to_parquet(output_parquet, index=False)
    
    return {
        'emails_generated': emails_generated,
        'sms_generated': sms_generated,
        'microsites_created': microsites_created
    }
