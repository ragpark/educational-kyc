# app/services/companies_house_enhanced.py
# Enhanced Companies House API integration with comprehensive checks

import aiohttp
import asyncio
import base64
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnhancedCompaniesHouseAPI:
    """Enhanced Companies House API integration with comprehensive checks"""
    
    def __init__(self):
        self.api_key = os.getenv('COMPANIES_HOUSE_API_KEY')
        if not self.api_key:
            print("Warning: COMPANIES_HOUSE_API_KEY not found in environment variables")
        self.base_url = "https://api.company-information.service.gov.uk"
        self.timeout = 10
        self.max_retries = 3
    
    def is_configured(self) -> bool:
        """Check if API is properly configured"""
        return bool(self.api_key and self.api_key != 'your_key_here')
    
    def _create_auth_header(self) -> str:
        """Create Basic Auth header"""
        credentials = f"{self.api_key}:"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def verify_company_comprehensive(self, company_number: str, expected_name: str = None) -> Dict:
        """Comprehensive company verification with enhanced checks"""
        
        if not self.is_configured():
            return {
                "status": "not_configured",
                "risk_score": 0.3,
                "data_source": "Companies House API",
                "details": {"error": "API key not configured"},
                "recommendations": ["Configure Companies House API key for full verification"],
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Get basic company information
            company_data = await self._get_company_data(company_number)
            
            if company_data.get("error"):
                return company_data
            
            # Get officers information
            officers_data = await self._get_officers_data(company_number)
            
            # Get filing history
            filing_data = await self._get_filing_history(company_number)
            
            # Get charges information
            charges_data = await self._get_charges_data(company_number)
            
            # Get PSC information
            psc_data = await self._get_psc_data(company_number)
            
            # Perform comprehensive analysis
            return await self._analyze_company_data(
                company_data, officers_data, filing_data, charges_data, psc_data, expected_name
            )
            
        except Exception as e:
            return {
                "status": "error",
                "risk_score": 0.7,
                "data_source": "Companies House API",
                "details": {"error": str(e)},
                "recommendations": ["Manual company verification required"],
                "confidence": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    
    async def quick_company_check(self, company_number: str) -> Dict:
        """Quick company check - just verify existence and active status"""
        if not self.is_configured():
            return {
                "exists": False,
                "active": False,
                "error": "API not configured"
            }
        
        company_data = await self._get_company_data(company_number)
        
        if company_data.get("error"):
            return {
                "exists": False,
                "active": False,
                "error": company_data.get("error")
            }
        
        return {
            "exists": True,
            "active": company_data.get("company_status", "").lower() == "active",
            "company_name": company_data.get("company_name"),
            "company_type": company_data.get("type"),
            "incorporation_date": company_data.get("date_of_incorporation")
        }
    
    async def _get_company_data(self, company_number: str) -> Dict:
        """Get basic company information"""
        headers = {
            "Authorization": self._create_auth_header(),
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/company/{company_number.upper()}"
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            return {
                                "error": "Company not found",
                                "status": "failed",
                                "risk_score": 0.9,
                                "details": {"company_number": company_number, "http_status": 404}
                            }
                        elif response.status == 401:
                            return {
                                "error": "API authentication failed",
                                "status": "error", 
                                "risk_score": 0.5,
                                "details": {"company_number": company_number, "http_status": 401}
                            }
                        else:
                            error_text = await response.text()
                            if attempt == self.max_retries - 1:  # Last attempt
                                return {
                                    "error": f"API error: {response.status} - {error_text}",
                                    "status": "error",
                                    "risk_score": 0.6,
                                    "details": {"company_number": company_number, "http_status": response.status}
                                }
                            
                            # Wait before retry
                            await asyncio.sleep(2 ** attempt)
                            
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    return {
                        "error": "API timeout",
                        "status": "error",
                        "risk_score": 0.5,
                        "details": {"company_number": company_number}
                    }
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return {
                        "error": str(e),
                        "status": "error",
                        "risk_score": 0.6,
                        "details": {"company_number": company_number}
                    }
                await asyncio.sleep(2 ** attempt)
        
        return {"error": "Max retries exceeded"}
    
    async def _get_officers_data(self, company_number: str) -> Dict:
        """Get company officers information"""
        headers = {
            "Authorization": self._create_auth_header(),
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/company/{company_number}/officers"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Officers API error: {response.status}"}
        except Exception as e:
            return {"error": f"Officers lookup failed: {str(e)}"}
    
    async def _get_filing_history(self, company_number: str) -> Dict:
        """Get recent filing history"""
        headers = {
            "Authorization": self._create_auth_header(),
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/company/{company_number}/filing-history"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Return only recent filings (last 10)
                        items = data.get("items", [])[:10]
                        return {"items": items, "total_count": data.get("total_count", 0)}
                    else:
                        return {"error": f"Filing history API error: {response.status}"}
        except Exception as e:
            return {"error": f"Filing history lookup failed: {str(e)}"}
    
    async def _get_charges_data(self, company_number: str) -> Dict:
        """Get company charges/security information"""
        headers = {
            "Authorization": self._create_auth_header(),
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/company/{company_number}/charges"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Charges API error: {response.status}"}
        except Exception as e:
            return {"error": f"Charges lookup failed: {str(e)}"}
    
    async def _get_psc_data(self, company_number: str) -> Dict:
        """Get persons with significant control"""
        headers = {
            "Authorization": self._create_auth_header(),
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/company/{company_number}/persons-with-significant-control"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"PSC API error: {response.status}"}
        except Exception as e:
            return {"error": f"PSC lookup failed: {str(e)}"}
    
    async def _analyze_company_data(self, company_data: Dict, officers_data: Dict, 
                                  filing_data: Dict, charges_data: Dict, 
                                  psc_data: Dict, expected_name: str = None) -> Dict:
        """Comprehensive analysis of company data"""
        
        # Basic company information
        company_status = company_data.get("company_status", "").lower()
        company_name = company_data.get("company_name", "")
        company_type = company_data.get("type", "")
        incorporation_date = company_data.get("date_of_incorporation")
        
        # Initialize risk factors
        risk_score = 0.1  # Base score for active company
        risk_factors = []
        recommendations = []
        
        # 1. Company Status Analysis
        status_risk = self._analyze_company_status(company_status)
        risk_score += status_risk["risk_addition"]
        risk_factors.extend(status_risk["factors"])
        recommendations.extend(status_risk["recommendations"])
        
        # 2. Name Matching Analysis
        if expected_name:
            name_match = self._analyze_name_match(company_name, expected_name)
            risk_score += name_match["risk_addition"]
            risk_factors.extend(name_match["factors"])
            recommendations.extend(name_match["recommendations"])
        
        # 3. Officers Analysis
        officers_analysis = self._analyze_officers(officers_data)
        risk_score += officers_analysis["risk_addition"]
        risk_factors.extend(officers_analysis["factors"])
        recommendations.extend(officers_analysis["recommendations"])
        
        # 4. Company Age Analysis
        age_analysis = self._analyze_company_age(incorporation_date)
        risk_score += age_analysis["risk_addition"]
        risk_factors.extend(age_analysis["factors"])
        recommendations.extend(age_analysis["recommendations"])
        
        # 5. Filing History Analysis
        filing_analysis = self._analyze_filing_history(filing_data)
        risk_score += filing_analysis["risk_addition"]
        risk_factors.extend(filing_analysis["factors"])
        recommendations.extend(filing_analysis["recommendations"])
        
        # 6. Company Type Analysis
        type_analysis = self._analyze_company_type(company_type)
        risk_score += type_analysis["risk_addition"]
        risk_factors.extend(type_analysis["factors"])
        recommendations.extend(type_analysis["recommendations"])
        
        # 7. Charges Analysis
        charges_analysis = self._analyze_charges(charges_data)
        risk_score += charges_analysis["risk_addition"]
        risk_factors.extend(charges_analysis["factors"])
        recommendations.extend(charges_analysis["recommendations"])
        
        # 8. PSC Analysis
        psc_analysis = self._analyze_psc(psc_data)
        risk_score += psc_analysis["risk_addition"]
        risk_factors.extend(psc_analysis["factors"])
        recommendations.extend(psc_analysis["recommendations"])
        
        # Determine overall status
        final_risk_score = min(risk_score, 1.0)
        
        if final_risk_score < 0.3:
            status = "passed"
        elif final_risk_score < 0.7:
            status = "flagged"
        else:
            status = "failed"
        
        # Calculate confidence based on data availability
        confidence = 0.9
        if officers_data.get("error"):
            confidence -= 0.1
        if filing_data.get("error"):
            confidence -= 0.1
        if charges_data.get("error"):
            confidence -= 0.05
        if psc_data.get("error"):
            confidence -= 0.05
        
        return {
            "status": status,
            "risk_score": final_risk_score,
            "data_source": "Companies House API (Enhanced)",
            "confidence": confidence,
            "details": {
                "company_name": company_name,
                "company_status": company_status,
                "company_type": company_type,
                "incorporation_date": incorporation_date,
                "registered_office": company_data.get("registered_office_address"),
                "sic_codes": company_data.get("sic_codes", []),
                "officers_count": len(officers_data.get("items", [])) if not officers_data.get("error") else "unknown",
                "recent_filings": len(filing_data.get("items", [])) if not filing_data.get("error") else "unknown",
                "outstanding_charges": len([c for c in charges_data.get("items", []) if c.get("status") == "outstanding"]) if not charges_data.get("error") else "unknown",
                "has_psc_data": bool(psc_data.get("items")) if not psc_data.get("error") else "unknown",
                "risk_factors": risk_factors,
                "name_match": expected_name is None or self._fuzzy_name_match(company_name, expected_name)
            },
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _analyze_company_status(self, status: str) -> Dict:
        """Analyze company status for risk factors"""
        if status == "active":
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
        elif status in ["liquidation", "dissolved", "converted-closed"]:
            return {
                "risk_addition": 0.8,
                "factors": ["company_not_active"],
                "recommendations": [f"Company status is '{status}' - not operational"]
            }
        elif status in ["administration", "receivership"]:
            return {
                "risk_addition": 0.6,
                "factors": ["company_distressed"],
                "recommendations": [f"Company in {status} - financial difficulties"]
            }
        else:
            return {
                "risk_addition": 0.4,
                "factors": ["company_status_uncertain"],
                "recommendations": [f"Company status '{status}' requires review"]
            }
    
    def _analyze_name_match(self, company_name: str, expected_name: str) -> Dict:
        """Analyze name matching"""
        if self._fuzzy_name_match(company_name, expected_name):
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
        else:
            return {
                "risk_addition": 0.3,
                "factors": ["name_mismatch"],
                "recommendations": [f"Company name '{company_name}' does not match expected '{expected_name}'"]
            }
    
    def _analyze_officers(self, officers_data: Dict) -> Dict:
        """Analyze company officers for risk factors"""
        if officers_data.get("error"):
            return {
                "risk_addition": 0.1,
                "factors": ["officers_data_unavailable"],
                "recommendations": ["Could not verify company officers"]
            }
        
        officers = officers_data.get("items", [])
        active_officers = [o for o in officers if not o.get("resigned_on")]
        
        risk_factors = []
        recommendations = []
        risk_addition = 0.0
        
        # Check for minimum officers
        if len(active_officers) == 0:
            risk_addition += 0.4
            risk_factors.append("no_active_officers")
            recommendations.append("No active officers found")
        elif len(active_officers) < 2 and any("private-limited" in officers_data.get("kind", "") for o in officers):
            risk_addition += 0.2
            risk_factors.append("minimal_officers")
            recommendations.append("Very few active officers for company type")
        
        # Check for recent officer changes
        recent_resignations = 0
        for officer in officers:
            if officer.get("resigned_on"):
                try:
                    resignation_date = datetime.fromisoformat(officer["resigned_on"].replace("Z", "+00:00"))
                    if datetime.now() - resignation_date < timedelta(days=180):  # Last 6 months
                        recent_resignations += 1
                except:
                    pass
        
        if recent_resignations > 2:
            risk_addition += 0.2
            risk_factors.append("recent_officer_changes")
            recommendations.append("Multiple recent officer resignations")
        
        return {
            "risk_addition": risk_addition,
            "factors": risk_factors,
            "recommendations": recommendations
        }
    
    def _analyze_company_age(self, incorporation_date: str) -> Dict:
        """Analyze company age for risk assessment"""
        if not incorporation_date:
            return {
                "risk_addition": 0.1,
                "factors": ["incorporation_date_unknown"],
                "recommendations": ["Incorporation date not available"]
            }
        
        try:
            inc_date = datetime.fromisoformat(incorporation_date)
            age_years = (datetime.now() - inc_date).days / 365.25
            
            if age_years < 1:
                return {
                    "risk_addition": 0.3,
                    "factors": ["very_new_company"],
                    "recommendations": ["Company incorporated less than 1 year ago - enhanced monitoring recommended"]
                }
            elif age_years < 2:
                return {
                    "risk_addition": 0.2,
                    "factors": ["new_company"],
                    "recommendations": ["Relatively new company - monitor performance"]
                }
            elif age_years > 50:
                return {
                    "risk_addition": -0.1,  # Slight bonus for established companies
                    "factors": ["established_company"],
                    "recommendations": []
                }
            else:
                return {
                    "risk_addition": 0.0,
                    "factors": [],
                    "recommendations": []
                }
        except:
            return {
                "risk_addition": 0.1,
                "factors": ["incorporation_date_invalid"],
                "recommendations": ["Could not parse incorporation date"]
            }
    
    def _analyze_filing_history(self, filing_data: Dict) -> Dict:
        """Analyze filing history for compliance"""
        if filing_data.get("error"):
            return {
                "risk_addition": 0.1,
                "factors": ["filing_history_unavailable"],
                "recommendations": ["Could not verify filing history"]
            }
        
        filings = filing_data.get("items", [])
        
        if not filings:
            return {
                "risk_addition": 0.2,
                "factors": ["no_recent_filings"],
                "recommendations": ["No recent filings found"]
            }
        
        # Check for overdue filings or compliance issues
        overdue_indicators = ["overdue", "late", "default", "penalty"]
        recent_compliance_issues = 0
        
        for filing in filings[:5]:  # Check last 5 filings
            description = filing.get("description", "").lower()
            if any(indicator in description for indicator in overdue_indicators):
                recent_compliance_issues += 1
        
        if recent_compliance_issues > 2:
            return {
                "risk_addition": 0.3,
                "factors": ["filing_compliance_issues"],
                "recommendations": ["Multiple compliance issues in filing history"]
            }
        elif recent_compliance_issues > 0:
            return {
                "risk_addition": 0.1,
                "factors": ["minor_filing_issues"],
                "recommendations": ["Some filing irregularities noted"]
            }
        else:
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
    
    def _analyze_company_type(self, company_type: str) -> Dict:
        """Analyze company type for educational context"""
        educational_types = [
            "private-limited-guarant-nsc-limited-exemption",  # Often used by educational orgs
            "private-limited-guarant-nsc",
            "community-interest-company"
        ]
        
        risky_types = [
            "private-unlimited",
            "old-public-company",
            "other"
        ]
        
        if company_type in educational_types:
            return {
                "risk_addition": -0.05,  # Slight bonus for appropriate structure
                "factors": ["suitable_company_type"],
                "recommendations": []
            }
        elif company_type in risky_types:
            return {
                "risk_addition": 0.2,
                "factors": ["unusual_company_type"],
                "recommendations": [f"Unusual company type '{company_type}' for educational provider"]
            }
        else:
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
    
    def _analyze_charges(self, charges_data: Dict) -> Dict:
        """Analyze company charges for financial risk"""
        if charges_data.get("error"):
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
        
        charges = charges_data.get("items", [])
        outstanding_charges = [c for c in charges if c.get("status") == "outstanding"]
        
        if len(outstanding_charges) > 5:
            return {
                "risk_addition": 0.3,
                "factors": ["multiple_charges"],
                "recommendations": ["Multiple outstanding charges against company assets"]
            }
        elif len(outstanding_charges) > 0:
            return {
                "risk_addition": 0.1,
                "factors": ["has_charges"],
                "recommendations": ["Company has secured debts"]
            }
        else:
            return {
                "risk_addition": 0.0,
                "factors": [],
                "recommendations": []
            }
    
    def _analyze_psc(self, psc_data: Dict) -> Dict:
        """Analyze PSC data for transparency"""
        if psc_data.get("error"):
            return {
                "risk_addition": 0.1,
                "factors": ["psc_data_unavailable"],
                "recommendations": ["Could not verify persons with significant control"]
            }
        
        items = psc_data.get("items", [])
        
        if not items:
            return {
                "risk_addition": 0.2,
                "factors": ["no_psc_data"],
                "recommendations": ["No PSC information available - lack of transparency"]
            }
        
        # Check for PSC statements (often indicate exemptions or investigations)
        psc_statements = [i for i in items if i.get("kind", "").endswith("-statement")]
        if psc_statements:
            return {
                "risk_addition": 0.15,
                "factors": ["psc_statements"],
                "recommendations": ["PSC statements present - may indicate ownership complexity"]
            }
        
        return {
            "risk_addition": 0.0,
            "factors": [],
            "recommendations": []
        }
    
    def _fuzzy_name_match(self, name1: str, name2: str) -> bool:
        """Fuzzy match company names"""
        if not name1 or not name2:
            return False
        
        def normalize_name(name):
            name = name.lower()
            # Remove common company suffixes
            suffixes = ['ltd', 'limited', 'plc', 'llp', 'lp', 'cic', 'cio', 'company']
            for suffix in suffixes:
                name = re.sub(r'\b' + suffix + r'\b', '', name)
            # Remove punctuation and extra spaces
            name = re.sub(r'[^\w\s]', '', name)
            name = ' '.join(name.split())
            return name
        
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        
        # Exact match
        if norm1 == norm2:
            return True
        
        # Substring match
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Word overlap (at least 60% of words match)
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if words1 and words2:
            overlap = len(words1.intersection(words2))
            total_unique = len(words1.union(words2))
            overlap_ratio = overlap / total_unique
            return overlap_ratio >= 0.6
        
        return False


# Usage example:
async def test_enhanced_companies_house():
    """Test the enhanced Companies House integration"""
    api = EnhancedCompaniesHouseAPI()
    
    if api.is_configured():
        print("Testing comprehensive company verification...")
        # Test with Companies House's own company number
        result = await api.verify_company_comprehensive("08242665", "Companies House")
        print(f"Status: {result['status']}")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Recommendations: {result['recommendations']}")
        print(f"Details: {json.dumps(result['details'], indent=2)}")
        
        print("\n" + "="*50 + "\n")
        
        print("Testing quick company check...")
        quick_result = await api.quick_company_check("08242665")
        print(f"Quick check result: {json.dumps(quick_result, indent=2)}")
    else:
        print("Companies House API not configured")
        print("Please set COMPANIES_HOUSE_API_KEY environment variable")


# Integration with main KYC system
async def get_enhanced_companies_house_result(company_number: str, company_name: str = None) -> Dict:
    """Get enhanced Companies House verification result"""
    api = EnhancedCompaniesHouseAPI()
    return await api.verify_company_comprehensive(company_number, company_name)


# Main entry point
if __name__ == "__main__":
    # Run the test
    asyncio.run(test_enhanced_companies_house())
