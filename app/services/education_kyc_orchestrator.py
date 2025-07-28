# app/services/education_kyc_orchestrator.py
# Fixed version with proper logging configuration

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from enum import Enum
import json
import logging

# Web scraping imports with error handling
try:
    import aiohttp
    from bs4 import BeautifulSoup
    import re
    SCRAPING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Web scraping dependencies not available: {e}")
    SCRAPING_AVAILABLE = False
    # Create dummy classes to prevent NameError
    class BeautifulSoup:
        pass
    aiohttp = None
    re = None

# Use standard logging instead of structlog to avoid configuration issues
logger = logging.getLogger(__name__)

class ProviderType(Enum):
    TRAINING_PROVIDER = "training_provider"
    FE_COLLEGE = "fe_college"
    HE_INSTITUTION = "he_institution"
    APPRENTICESHIP_PROVIDER = "apprenticeship_provider"
    PRIVATE_TRAINING = "private_training"
    ADULT_COMMUNITY = "adult_community"
    TRUST = "trust"
    SCHOOL = "school"
    CHARITY = "charity"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EducationalProviderRequest:
    organisation_name: str
    trading_name: Optional[str]
    company_number: str
    urn: str  # Ofsted Unique Reference Number - now mandatory
    ukprn: Optional[str]  # UK Provider Reference Number - now optional
    provider_type: ProviderType
    contact_email: str
    address: str
    postcode: str
    qualifications_offered: List[str] = None

@dataclass
class EducationalVerificationResult:
    check_type: str
    status: str  # passed, failed, flagged, not_applicable
    risk_score: float
    data_source: str
    timestamp: datetime
    details: Dict
    recommendations: List[str] = None

class UKEducationalKYCOrchestrator:
    """Main orchestrator for UK Educational Provider KYC"""
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.educational_checks = [
            "company_registration",
            "ukprn_validation", 
            "postcode_validation",
            "ofqual_recognition",
            "ofsted_rating",
            "esfa_funding_status",
            "qualification_validation",
            "safeguarding_assessment",
            "financial_stability",
            "sanctions_screening",
            "risk_assessment"
        ]
    
    async def process_educational_kyc(self, request: EducationalProviderRequest) -> List[EducationalVerificationResult]:
        """Process comprehensive educational provider KYC"""
        logger.info(f"Starting educational KYC process for {request.organisation_name}")
        
        results = []
        
        try:
            # Phase 1: Basic validation (parallel execution)
            basic_checks = await asyncio.gather(
                self.verify_company_registration(request),
                self.validate_ukprn(request),
                self.validate_postcode(request),
                self.check_sanctions(request),
                return_exceptions=True
            )
            
            # Filter out exceptions and add successful results
            for result in basic_checks:
                if isinstance(result, EducationalVerificationResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Basic check failed: {str(result)}")
            
            # Phase 2: Educational regulatory checks (parallel)
            educational_checks = await asyncio.gather(
                self.check_ofqual_recognition(request),
                self.assess_ofsted_rating(request),
                self.verify_esfa_status(request),
                return_exceptions=True
            )
            
            for result in educational_checks:
                if isinstance(result, EducationalVerificationResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Educational check failed: {str(result)}")
            
            # Phase 3: Qualification validation
            if request.qualifications_offered:
                qual_results = await self.validate_qualifications(request.qualifications_offered)
                results.extend(qual_results)
            
            # Phase 4: Risk assessment
            risk_result = await self.assess_educational_risk(results, request)
            results.append(risk_result)
            
            logger.info(f"Educational KYC process completed for {request.organisation_name}, checks: {len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Educational KYC process failed for {request.organisation_name}: {str(e)}")
            raise
    
    async def verify_company_registration(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Verify company registration with Companies House"""
        try:
            # Import the enhanced Companies House service
            from app.services.companies_house_enhanced import get_enhanced_companies_house_result
            
            # Use the enhanced Companies House service for real API calls
            companies_house_result = await get_enhanced_companies_house_result(
                request.company_number,
                request.organisation_name
            )
            
            # Convert the enhanced result to our format
            if companies_house_result:
                return EducationalVerificationResult(
                    check_type="company_registration",
                    status=companies_house_result.get("status", "error"),
                    risk_score=companies_house_result.get("risk_score", 0.7),
                    data_source=companies_house_result.get("data_source", "Companies House"),
                    timestamp=datetime.now(),
                    details=companies_house_result.get("details", {}),
                    recommendations=companies_house_result.get("recommendations", [])
                )
            else:
                # Fallback to mock if enhanced service fails
                response = await self._mock_companies_house_check(request.company_number)
                
                is_active = response.get("company_status") == "active"
                directors_ok = not any(
                    director.get("disqualified", False) 
                    for director in response.get("officers", [])
                )
                
                status = "passed" if is_active and directors_ok else "failed"
                risk_score = 0.1 if status == "passed" else 0.8
                
                return EducationalVerificationResult(
                    check_type="company_registration",
                    status=status,
                    risk_score=risk_score,
                    data_source="Companies House (Mock)",
                    timestamp=datetime.now(),
                    details=response,
                    recommendations=[] if status == "passed" else ["Review company status and directors"]
                )
            
        except Exception as e:
            logger.error(f"Companies House verification failed: {str(e)}")
            return self._create_error_result("company_registration", str(e))
    
    async def validate_ukprn(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Validate UKPRN with UK Register of Learning Providers"""
        if not request.ukprn:
            return EducationalVerificationResult(
                check_type="ukprn_validation",
                status="not_applicable",
                risk_score=0.3,
                data_source="UKRLP",
                timestamp=datetime.now(),
                details={"message": "No UKPRN provided"},
                recommendations=["Consider UKPRN registration for credibility"]
            )
        
        try:
            # Try to get real UKRLP data first
            ukrlp_data = await self._get_real_ukrlp_data(request.ukprn)
            
            if ukrlp_data and not ukrlp_data.get("error"):
                # Use real UKRLP data
                response = ukrlp_data
                data_source = "UKRLP (Real Data)"
            else:
                # Fall back to mock if real data unavailable
                logger.warning(f"UKRLP data unavailable for {request.ukprn}: {ukrlp_data.get('error', 'Unknown error')}")
                response = await self._mock_ukprn_check(request.ukprn)
                data_source = "UKRLP (Simulated)"
            
            # Determine verification status
            verification_status = response.get("verification_status", "Unknown")
            provider_status = response.get("provider_status", "Unknown")
            
            # Risk scoring based on UKRLP status
            if verification_status == "Verified" and provider_status == "Active":
                status = "passed"
                risk_score = 0.1
            elif verification_status == "Verified" and provider_status in ["Inactive", "Deactivated"]:
                status = "flagged"
                risk_score = 0.6
            elif verification_status == "Not Verified":
                status = "failed"
                risk_score = 0.8
            else:
                status = "flagged"
                risk_score = 0.5
            
            # Add recommendations based on status
            recommendations = []
            if provider_status == "Inactive":
                recommendations.append("Provider is inactive in UKRLP - verify current operational status")
            elif provider_status == "Deactivated":
                recommendations.append("Provider has been deactivated - check compliance status")
            elif verification_status == "Not Verified":
                recommendations.append("UKPRN is not verified - may indicate registration issues")
            
            return EducationalVerificationResult(
                check_type="ukprn_validation",
                status=status,
                risk_score=risk_score,
                data_source=data_source,
                timestamp=datetime.now(),
                details=response,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"UKPRN validation failed: {str(e)}")
            return self._create_error_result("ukprn_validation", str(e))
    
    async def _get_real_ukrlp_data(self, ukprn: str) -> Dict:
        """Get real UKRLP data using web scraping"""
        try:
            # Check if scraping dependencies are available
            if not self._check_scraping_dependencies():
                return {"error": "Web scraping dependencies not available (beautifulsoup4, lxml)"}
            
            # Validate UKPRN format first
            if not ukprn or not ukprn.isdigit() or len(ukprn) != 8 or not ukprn.startswith('10'):
                return {"error": "Invalid UKPRN format - should be 8 digits starting with 10"}
            
            logger.info(f"Retrieving UKRLP data for UKPRN: {ukprn}")
            
            # Get UKRLP provider details
            ukrlp_data = await self._scrape_ukrlp_provider(ukprn)
            
            return ukrlp_data
            
        except Exception as e:
            logger.error(f"Real UKRLP data lookup failed: {str(e)}")
            return {"error": str(e)}
    
    async def _scrape_ukrlp_provider(self, ukprn: str) -> Dict:
        """Scrape UKRLP provider details from the website"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            # Construct UKRLP URL using the pattern from the example
            ukrlp_url = f"https://www.ukrlp.co.uk/ukrlp/ukrlp_provider.page_pls_provDetails?x=&pn_p_id={ukprn}&pv_status=VERIFIED&pv_vis_code=L"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-GB,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(ukrlp_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"Unable to fetch UKRLP page: HTTP {response.status}"}
                    
                    html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check if the page shows "No records found" or similar error
            error_indicators = [
                "No records found",
                "Provider not found",
                "Invalid provider",
                "Error"
            ]
            
            page_text = soup.get_text().lower()
            for indicator in error_indicators:
                if indicator.lower() in page_text:
                    return {"error": f"UKPRN {ukprn} not found in UKRLP database"}
            
            # Extract provider information from the page
            provider_data = self._extract_ukrlp_data(soup, ukprn)
            
            if not provider_data.get("provider_name"):
                return {"error": "Could not extract provider information from UKRLP page"}
            
            return provider_data
            
        except ImportError as e:
            logger.error(f"Missing dependencies for UKRLP scraping: {str(e)}")
            return {"error": "Web scraping dependencies not available"}
        except Exception as e:
            logger.error(f"UKRLP scraping failed: {str(e)}")
            return {"error": str(e)}
    
    def _extract_ukrlp_data(self, soup: BeautifulSoup, ukprn: str) -> Dict:
        """Extract provider data from UKRLP page HTML"""
        try:
            data = {
                "ukprn": ukprn,
                "data_source": "UKRLP Web Scraping"
            }
            
            # Look for provider name - usually in a header or title
            provider_name_selectors = [
                "h1.govuk-heading-l",
                "h1",
                "h2",
                ".provider-name",
                ".heading",
                "td:contains('Provider Name')",
                "th:contains('Provider Name')"
            ]
            
            provider_name = None
            for selector in provider_name_selectors:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if text:
                        match = re.search(r"Provider Details for\s*(.+)", text, re.I)
                        if match:
                            text = match.group(1)
                    # Filter out generic text
                    if text and len(text) > 5 and not any(x in text.lower() for x in ['ukrlp', 'provider details', 'search']):
                        provider_name = text
                        break
            
            # If provider name not found in headers, look in table cells
            if not provider_name:
                # Look for table structure with provider details
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            if 'provider name' in label or 'organisation' in label:
                                provider_name = value
                                break
                    if provider_name:
                        break
            
            data["provider_name"] = provider_name or "Unknown"

            # Extract fields from GOV.UK summary lists
            for row in soup.select("dl.govuk-summary-list div.govuk-summary-list__row"):
                key_elem = row.select_one("dt.govuk-summary-list__key")
                value_elem = row.select_one("dd.govuk-summary-list__value")
                if not key_elem or not value_elem:
                    continue
                label = key_elem.get_text(" ", strip=True).lower()
                value = value_elem.get_text(" ", strip=True)

                if "address" in label and "address" not in data:
                    data["address"] = value
                elif any(term in label for term in ["telephone", "phone", "contact"]):
                    data.setdefault("contact_number", value)
                elif "email" in label:
                    data.setdefault("email", value)
                elif "website" in label or "web" in label:
                    data.setdefault("website", value)
                elif "trading name" in label:
                    data.setdefault("trading_name", value)
                elif "legal name" in label:
                    data.setdefault("legal_name", value)
                elif "status" in label:
                    data.setdefault("provider_status", value)
                elif "registration" in label and "date" in label:
                    data.setdefault("registration_date", value)

            # Extract other common fields from tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        # Map common fields
                        if 'status' in label:
                            # Determine provider status
                            if 'active' in value.lower():
                                data["provider_status"] = "Active"
                                data["verification_status"] = "Verified"
                            elif 'inactive' in value.lower() or 'deactivated' in value.lower():
                                data["provider_status"] = "Inactive"
                                data["verification_status"] = "Verified"
                            else:
                                data["provider_status"] = value
                                data["verification_status"] = "Verified"
                        
                        elif 'type' in label or 'category' in label:
                            data["provider_type"] = value
                        
                        elif 'address' in label or 'location' in label:
                            data["address"] = value
                        
                        elif 'contact' in label or 'phone' in label or 'telephone' in label:
                            data["contact_number"] = value
                        
                        elif 'email' in label:
                            data["email"] = value
                        
                        elif 'website' in label or 'web' in label:
                            data["website"] = value
                        
                        elif 'legal name' in label:
                            data["legal_name"] = value
                        
                        elif 'trading name' in label:
                            data["trading_name"] = value
                        
                        elif 'verification' in label:
                            data["verification_status"] = value
                        
                        elif 'registration' in label and 'date' in label:
                            data["registration_date"] = value
            
            # Set default values if not found
            if "verification_status" not in data:
                # If we got this far, the UKPRN exists in the system
                data["verification_status"] = "Verified"
            
            if "provider_status" not in data:
                # Default to Active if we can access the page
                data["provider_status"] = "Active"
            
            # Look for any additional provider information
            # Check for any div or span elements with relevant content
            for elem in soup.find_all(['div', 'span', 'p']):
                text = elem.get_text(strip=True)
                if len(text) > 10 and any(keyword in text.lower() for keyword in ['qualification', 'education', 'training', 'provider']):
                    if "description" not in data:
                        data["description"] = text[:200] + "..." if len(text) > 200 else text
                        break
            
            return data
            
        except Exception as e:
            logger.error(f"UKRLP data extraction failed: {str(e)}")
            return {"error": f"Data extraction failed: {str(e)}"}
    
    async def _mock_ukrlp_check(self, ukprn: str) -> Dict:
        """Mock UKRLP check for development"""
        return {
            "verification_status": "Verified",
            "provider_status": "Active",
            "provider_name": "Example Training Provider",
            "ukprn": ukprn,
            "mock_data": True,
            "note": "Mock data - real UKRLP integration attempted but failed"
        }
    
    async def validate_postcode(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Validate UK postcode using postcodes.io service"""
        if not request.postcode:
            return EducationalVerificationResult(
                check_type="postcode_validation",
                status="failed",
                risk_score=0.5,
                data_source="Postcodes.io",
                timestamp=datetime.now(),
                details={"error": "No postcode provided"},
                recommendations=["Postcode is required for location verification"]
            )
        
        try:
            # Clean postcode (remove spaces and convert to uppercase)
            clean_postcode = request.postcode.replace(" ", "").upper()
            
            # Call postcodes.io API
            url = f"https://api.postcodes.io/postcodes/{clean_postcode}"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == 200:
                            result_data = data.get("result", {})
                            
                            return EducationalVerificationResult(
                                check_type="postcode_validation",
                                status="passed",
                                risk_score=0.05,
                                data_source="Postcodes.io",
                                timestamp=datetime.now(),
                                details={
                                    "postcode": result_data.get("postcode"),
                                    "country": result_data.get("country"),
                                    "region": result_data.get("region"),
                                    "admin_district": result_data.get("admin_district"),
                                    "admin_county": result_data.get("admin_county"),
                                    "parliamentary_constituency": result_data.get("parliamentary_constituency"),
                                    "coordinates": {
                                        "latitude": result_data.get("latitude"),
                                        "longitude": result_data.get("longitude")
                                    },
                                    "quality": result_data.get("quality"),
                                    "eastings": result_data.get("eastings"),
                                    "northings": result_data.get("northings")
                                },
                                recommendations=[]
                            )
                        else:
                            return EducationalVerificationResult(
                                check_type="postcode_validation",
                                status="failed",
                                risk_score=0.7,
                                data_source="Postcodes.io",
                                timestamp=datetime.now(),
                                details={"error": "Invalid postcode format", "postcode": request.postcode},
                                recommendations=["Verify postcode format and resubmit"]
                            )
                    
                    elif response.status == 404:
                        return EducationalVerificationResult(
                            check_type="postcode_validation",
                            status="failed",
                            risk_score=0.8,
                            data_source="Postcodes.io",
                            timestamp=datetime.now(),
                            details={"error": "Postcode not found", "postcode": request.postcode},
                            recommendations=["Verify postcode exists and is correctly formatted"]
                        )
                    
                    else:
                        return EducationalVerificationResult(
                            check_type="postcode_validation",
                            status="error",
                            risk_score=0.4,
                            data_source="Postcodes.io",
                            timestamp=datetime.now(),
                            details={"error": f"API error: {response.status}", "postcode": request.postcode},
                            recommendations=["Retry postcode validation later"]
                        )
            
        except Exception as e:
            return self._create_error_result("postcode_validation", str(e))
    
    
    async def check_ofqual_recognition(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Check Ofqual recognition for awarding qualifications"""
        try:
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="ofqual-register",
                    tool="awarding_body_verification",
                    args={"organisation_name": request.organisation_name}
                )
            else:
                response = await self._mock_ofqual_check(request.organisation_name)
            
            is_recognised = response.get("recognised", False)
            
            if not is_recognised and request.qualifications_offered:
                status = "flagged"
                risk_score = 0.4
                recommendations = ["Verify qualifications are delivered through recognised awarding organisations"]
            elif is_recognised:
                status = "passed"
                risk_score = 0.1
                recommendations = []
            else:
                status = "not_applicable"
                risk_score = 0.2
                recommendations = []
            
            return EducationalVerificationResult(
                check_type="ofqual_recognition",
                status=status,
                risk_score=risk_score,
                data_source="Ofqual Register",
                timestamp=datetime.now(),
                details=response,
                recommendations=recommendations
            )
            
        except Exception as e:
            return self._create_error_result("ofqual_recognition", str(e))
    
    async def assess_ofsted_rating(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Assess Ofsted inspection rating using real Ofsted data"""
        try:
            # Try to get real Ofsted data first
            ofsted_data = await self._get_real_ofsted_data(request)
            
            if ofsted_data and not ofsted_data.get("error"):
                # Use real Ofsted data
                response = ofsted_data
                data_source = "Ofsted (Real Data)"
            else:
                # Fall back to mock if real data unavailable
                logger.warning(f"Ofsted API unavailable for {request.organisation_name}: {ofsted_data.get('error', 'Unknown error')}")
                response = await self._mock_ofsted_check(request.organisation_name)
                data_source = "Ofsted (Simulated)"
            
            # Extract ratings from real or mock data
            latest_rating = response.get("latest_overall_effectiveness") or response.get("rating")
            safeguarding = response.get("safeguarding_effectiveness", "Unknown")
            
            # Risk scoring based on Ofsted grades
            risk_mapping = {
                "Outstanding": 0.05,
                "Good": 0.15,
                "Requires improvement": 0.5,
                "Requires Improvement": 0.5,  # Handle different case
                "Inadequate": 0.9
            }
            
            risk_score = risk_mapping.get(latest_rating, 0.7)
            
            # Additional risk if safeguarding issues
            if safeguarding in ["Requires improvement", "Requires Improvement", "Inadequate"]:
                risk_score = min(risk_score + 0.3, 1.0)
            
            status = "passed" if risk_score < 0.3 else "flagged" if risk_score < 0.7 else "failed"
            
            recommendations = []
            if latest_rating in ["Requires improvement", "Requires Improvement", "Inadequate"]:
                recommendations.append("Monitor improvement plan progress")
            if safeguarding in ["Requires improvement", "Requires Improvement", "Inadequate"]:
                recommendations.append("Enhanced safeguarding due diligence required")
            
            # Add recommendations based on real data
            if response.get("timeline") and len(response.get("timeline", [])) > 0:
                recent_events = [event for event in response.get("timeline", []) if event.get("timeline_date")]
                if recent_events:
                    recommendations.append("Review recent inspection timeline for compliance updates")
            
            return EducationalVerificationResult(
                check_type="ofsted_rating",
                status=status,
                risk_score=risk_score,
                data_source=data_source,
                timestamp=datetime.now(),
                details=response,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Ofsted assessment failed: {str(e)}")
            return self._create_error_result("ofsted_rating", str(e))
    
    async def _get_real_ofsted_data(self, request: EducationalProviderRequest) -> Dict:
        """Get real Ofsted data using the provided URN directly"""
        try:
            # Check if scraping dependencies are available
            if not self._check_scraping_dependencies():
                return {"error": "Web scraping dependencies not available (beautifulsoup4, lxml)"}
            
            # Use the URN directly - no need to search for it
            if not request.urn:
                return {"error": "URN is required for Ofsted verification"}
            
            logger.info(f"Using provided URN {request.urn} for {request.organisation_name}")
            
            # Get the full Ofsted report using the provided URN
            ofsted_report = await self._get_ofsted_report_by_urn(request.urn)
            
            return ofsted_report
            
        except Exception as e:
            logger.error(f"Real Ofsted data lookup failed: {str(e)}")
            return {"error": str(e)}
    
    async def _find_ofsted_urn(self, request: EducationalProviderRequest) -> Optional[str]:
        """Find Ofsted URN by searching for the organization"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re
            
            # Search Ofsted using organization name and postcode  
            search_query = f"{request.organisation_name} {request.postcode}"
            search_url = f"https://reports.ofsted.gov.uk/search?q={search_query}"
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Look for search results
                        results = soup.select("li.search-result")
                        
                        for result in results:
                            # Extract title and check if it matches our organization
                            title_elem = result.select_one("h3.search-result__title a")
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                
                                # Check if this result matches our organization
                                if self._is_organization_match(title, request.organisation_name):
                                    # Extract URN from the URL or data attributes
                                    href = title_elem.get('href', '')
                                    
                                    # URN is typically in the URL like /provider/123456
                                    urn_match = re.search(r'/provider/(\d+)', href)
                                    if urn_match:
                                        return urn_match.group(1)
                                    
                                    # Also check for URN in the result text or metadata
                                    urn_text = result.get_text()
                                    urn_match = re.search(r'URN:?\s*(\d{6,7})', urn_text)
                                    if urn_match:
                                        return urn_match.group(1)
            
            return None
            
        except ImportError as e:
            logger.error(f"Missing dependencies for Ofsted scraping: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"URN search failed: {str(e)}")
            return None
    
    def _is_organization_match(self, ofsted_title: str, org_name: str) -> bool:
        """Check if Ofsted result matches our organization"""
        # Normalize names for comparison
        ofsted_clean = ofsted_title.lower().strip()
        org_clean = org_name.lower().strip()
        
        # Direct match
        if ofsted_clean == org_clean:
            return True
        
        # Check if organization name is contained in Ofsted title
        if org_clean in ofsted_clean:
            return True
        
        # Check if Ofsted title is contained in organization name
        if ofsted_clean in org_clean:
            return True
        
        # Word-based matching (at least 60% of words match)
        ofsted_words = set(ofsted_clean.split())
        org_words = set(org_clean.split())
        
        if org_words and ofsted_words:
            overlap = len(org_words.intersection(ofsted_words))
            total_unique = len(org_words.union(ofsted_words))
            
            if total_unique > 0 and (overlap / total_unique) >= 0.6:
                return True
        
        return False
    
    async def _get_ofsted_report_by_urn(self, urn: str) -> Dict:
        """Get Ofsted report by URN using web scraping (async version of provided code)"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            # First resolve the URN to get the actual report URL
            resolved_url = await self._resolve_ofsted_url(urn)
            if not resolved_url:
                return {"error": "URN not found or URL resolution failed"}
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(resolved_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"Unable to fetch Ofsted page: HTTP {response.status}"}
                    
                    html = await response.text()
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract data using the same logic as provided code
            title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Not found"
            
            grade_div = soup.find("div", class_="inspection-grade")
            rating = grade_div.get_text(strip=True) if grade_div else "Not found"
            
            date_div = soup.find("div", class_="inspection-date")
            inspection_date = date_div.get_text(strip=True) if date_div else "Not found"
            
            report_link_tag = soup.find("a", href=True, text=lambda t: t and "Download full report" in t)
            report_url = f"https://reports.ofsted.gov.uk{report_link_tag['href']}" if report_link_tag else "Not available"
            
            # Find address from the Ofsted page
            address_tag = soup.find("address", class_="title-block__address")
            address = None
            if address_tag:
                address_text = address_tag.get_text(strip=True)
                address = address_text.replace("Address:", "").strip()
            
            # Extract timeline
            timeline = []
            timeline_items = soup.select("ol.timeline > li.timeline__day")
            for item in timeline_items:
                date_tag = item.select_one("p.timeline__date time")
                timeline_date = date_tag.get_text(strip=True) if date_tag else None
                
                event_title_container = item.select_one("span.event__title")
                if event_title_container:
                    # Remove non-visual spans as in original code
                    for s in event_title_container.select("span.nonvisual"):
                        s.decompose()
                    event_title = event_title_container.get_text(strip=True)
                else:
                    event_title = None
                
                timeline.append({
                    "timeline_date": timeline_date,
                    "event_title": event_title
                })
            
            # Convert to our expected format
            return {
                "title": title,
                "latest_overall_effectiveness": rating,
                "safeguarding_effectiveness": "Unknown",  # May need additional parsing
                "latest_inspection_date": inspection_date,
                "report_url": report_url,
                "address": address,
                "timeline": timeline,
                "urn": urn,
                "data_source": "Ofsted Web Scraping"
            }
            
        except ImportError as e:
            logger.error(f"Missing dependencies for Ofsted scraping: {str(e)}")
            return {"error": "Web scraping dependencies not available"}
        except Exception as e:
            logger.error(f"Ofsted report extraction failed: {str(e)}")
            return {"error": str(e)}
    
    async def _resolve_ofsted_url(self, urn: str) -> Optional[str]:
        """Resolve URN to Ofsted report URL (async version of provided code)"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            
            search_url = f"https://reports.ofsted.gov.uk/search?q={urn}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        result = soup.select_one("li.search-result h3.search-result__title a[href]")
                        if result:
                            return f"https://reports.ofsted.gov.uk{result['href']}"
            
            return None
            
        except ImportError as e:
            logger.error(f"Missing dependencies for Ofsted scraping: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"URL resolution failed: {str(e)}")
            return None
    
    async def verify_esfa_status(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Verify ESFA funding status and RoATP listing"""
        try:
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="esfa-roatp",
                    tool="roatp_status_check",
                    args={
                        "ukprn": request.ukprn,
                        "organisation_name": request.organisation_name
                    }
                )
            else:
                response = await self._mock_esfa_check(request.ukprn)
            
            roatp_status = response.get("provider_status")
            funding_restrictions = response.get("funding_restrictions", [])
            
            # Risk assessment based on ESFA status
            status_risk_mapping = {
                "Main provider": 0.1,
                "Supporting provider": 0.2,
                "Employer provider": 0.15
            }
            
            risk_score = status_risk_mapping.get(roatp_status, 0.6)
            
            # Additional risk for funding restrictions
            if funding_restrictions:
                risk_score = min(risk_score + 0.3, 1.0)
            
            status = "passed" if risk_score < 0.3 else "flagged"
            
            recommendations = []
            if funding_restrictions:
                recommendations.append("Review funding restriction details and remediation plans")
            if not roatp_status:
                recommendations.append("Consider RoATP application for apprenticeship delivery")
            
            return EducationalVerificationResult(
                check_type="esfa_funding_status",
                status=status,
                risk_score=risk_score,
                data_source="ESFA",
                timestamp=datetime.now(),
                details=response,
                recommendations=recommendations
            )
            
        except Exception as e:
            return self._create_error_result("esfa_funding_status", str(e))
    
    async def validate_qualifications(self, qualifications: List[str]) -> List[EducationalVerificationResult]:
        """Validate offered qualifications against Ofqual register"""
        results = []
        
        for qualification in qualifications:
            try:
                if self.mcp_client:
                    response = await self.mcp_client.call_tool(
                        server="ofqual-register",
                        tool="qualification_search",
                        args={"qualification_title": qualification}
                    )
                else:
                    response = await self._mock_qualification_check(qualification)
                
                is_regulated = response.get("regulated", False)
                is_current = response.get("operational_end_date") is None
                
                if is_regulated and is_current:
                    status = "passed"
                    risk_score = 0.1
                    recommendations = []
                elif is_regulated and not is_current:
                    status = "flagged"
                    risk_score = 0.4
                    recommendations = ["Qualification may be withdrawn - verify current status"]
                else:
                    status = "flagged"
                    risk_score = 0.5
                    recommendations = ["Unregulated qualification - verify quality assurance"]
                
                results.append(EducationalVerificationResult(
                    check_type=f"qualification_validation_{qualification[:20]}",
                    status=status,
                    risk_score=risk_score,
                    data_source="Ofqual Register",
                    timestamp=datetime.now(),
                    details={"qualification": qualification, **response},
                    recommendations=recommendations
                ))
                
            except Exception as e:
                results.append(self._create_error_result(f"qualification_validation_{qualification[:20]}", str(e)))
        
        return results
    
    async def check_sanctions(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Check sanctions lists for organisation"""
        try:
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="uk-sanctions",
                    tool="sanctions_check",
                    args={
                        "name": request.organisation_name,
                        "entity_type": "entity"
                    }
                )
            else:
                response = await self._mock_sanctions_check(request.organisation_name)
            
            has_matches = bool(response.get("matches"))
            status = "flagged" if has_matches else "passed"
            risk_score = 0.9 if has_matches else 0.05
            
            return EducationalVerificationResult(
                check_type="sanctions_screening",
                status=status,
                risk_score=risk_score,
                data_source="UK Treasury Sanctions",
                timestamp=datetime.now(),
                details=response,
                recommendations=["Enhanced due diligence required"] if has_matches else []
            )
            
        except Exception as e:
            return self._create_error_result("sanctions_screening", str(e))
    
    async def assess_educational_risk(self, verification_results: List[EducationalVerificationResult], 
                                   request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Assess overall educational provider risk"""
        total_risk_score = 0.0
        risk_factors = []
        critical_issues = []
        
        for result in verification_results:
            total_risk_score += result.risk_score
            
            if result.status == "failed":
                critical_issues.append(result.check_type)
            elif result.status == "flagged":
                risk_factors.append(result.check_type)
        
        # Average risk score
        avg_risk_score = total_risk_score / len(verification_results) if verification_results else 0.5
        
        # Additional risk factors specific to education
        if request.provider_type == ProviderType.PRIVATE_TRAINING:
            avg_risk_score += 0.1
        
        # Determine overall risk level
        if avg_risk_score < 0.25:
            risk_level = RiskLevel.LOW
            overall_status = "approved"
        elif avg_risk_score < 0.5:
            risk_level = RiskLevel.MEDIUM
            overall_status = "approved_with_monitoring"
        elif avg_risk_score < 0.75:
            risk_level = RiskLevel.HIGH
            overall_status = "enhanced_due_diligence_required"
        else:
            risk_level = RiskLevel.CRITICAL
            overall_status = "rejected"
        
        recommendations = []
        if critical_issues:
            recommendations.append("Address critical compliance issues before proceeding")
        if risk_factors:
            recommendations.append("Implement enhanced monitoring procedures")
        if avg_risk_score > 0.5:
            recommendations.append("Consider site visit and detailed review")
        
        return EducationalVerificationResult(
            check_type="educational_risk_assessment",
            status=overall_status,
            risk_score=avg_risk_score,
            data_source="Internal Educational Risk Engine",
            timestamp=datetime.now(),
            details={
                "risk_level": risk_level.value,
                "risk_factors": risk_factors,
                "critical_issues": critical_issues,
                "total_checks": len(verification_results)
            },
            recommendations=recommendations
        )
    
# Mock methods for development/testing when MCP client is not available
    
    def _check_scraping_dependencies(self) -> bool:
        """Check if web scraping dependencies are available"""
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            return True
        except ImportError as e:
            logger.error(f"Web scraping dependencies not available: {str(e)}")
            return False
    
    async def _mock_companies_house_check(self, company_number: str) -> Dict:
        """Mock Companies House check for development"""
        return {
            "company_status": "active",
            "company_name": "Example Education Ltd",
            "incorporation_date": "2020-01-01",
            "officers": []
        }
    
    async def _mock_ukprn_check(self, ukprn: str) -> Dict:
        """Mock UKPRN check for development"""
        return {
            "verification_status": "Verified",
            "provider_status": "Active",
            "provider_name": "Example Training Provider"
        }
    
    async def _mock_ofqual_check(self, organisation_name: str) -> Dict:
        """Mock Ofqual check for development"""
        return {
            "recognised": False,
            "note": "Mock response - not a recognised awarding organisation"
        }
    
    async def _mock_ofsted_check(self, organisation_name: str) -> Dict:
        """Mock Ofsted check for development"""
        return {
            "latest_overall_effectiveness": "Good",
            "safeguarding_effectiveness": "Good",
            "latest_inspection_date": "2023-01-01",
            "mock_data": True,
            "note": "Mock data - URN required for real Ofsted verification"
        }
    
    async def _mock_esfa_check(self, ukprn: str) -> Dict:
        """Mock ESFA check for development"""
        return {
            "provider_status": "Main provider",
            "funding_restrictions": []
        }
    
    async def _mock_qualification_check(self, qualification: str) -> Dict:
        """Mock qualification check for development"""
        return {
            "regulated": True,
            "operational_end_date": None,
            "awarding_organisation": "Example Awarding Body"
        }
    
    async def _mock_sanctions_check(self, organisation_name: str) -> Dict:
        """Mock sanctions check for development"""
        return {
            "matches": False,
            "checked_lists": ["UK Treasury", "OFAC", "EU"]
        }
    
    def _create_error_result(self, check_type: str, error_message: str) -> EducationalVerificationResult:
        """Create error result for failed checks"""
        return EducationalVerificationResult(
            check_type=check_type,
            status="error",
            risk_score=0.7,
            data_source="System Error",
            timestamp=datetime.now(),
            details={"error": error_message},
            recommendations=["Manual verification required due to system error"]
        )
