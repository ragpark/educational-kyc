# app/services/education_kyc_orchestrator.py
# Complete implementation for Railway deployment

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
from enum import Enum
import json
import structlog

logger = structlog.get_logger()

class ProviderType(Enum):
    TRAINING_PROVIDER = "training_provider"
    FE_COLLEGE = "fe_college"
    HE_INSTITUTION = "he_institution"
    APPRENTICESHIP_PROVIDER = "apprenticeship_provider"
    PRIVATE_TRAINING = "private_training"
    ADULT_COMMUNITY = "adult_community"

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
    ukprn: Optional[str]
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
        logger.info("Starting educational KYC process", provider=request.organisation_name)
        
        results = []
        
        try:
            # Phase 1: Basic validation (parallel execution)
            basic_checks = await asyncio.gather(
                self.verify_company_registration(request),
                self.validate_ukprn(request),
                self.check_sanctions(request),
                return_exceptions=True
            )
            
            # Filter out exceptions and add successful results
            for result in basic_checks:
                if isinstance(result, EducationalVerificationResult):
                    results.append(result)
                elif isinstance(result, Exception):
                    logger.error("Basic check failed", error=str(result))
            
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
                    logger.error("Educational check failed", error=str(result))
            
            # Phase 3: Qualification validation
            if request.qualifications_offered:
                qual_results = await self.validate_qualifications(request.qualifications_offered)
                results.extend(qual_results)
            
            # Phase 4: Risk assessment
            risk_result = await self.assess_educational_risk(results, request)
            results.append(risk_result)
            
            logger.info("Educational KYC process completed", 
                       provider=request.organisation_name, 
                       checks_completed=len(results))
            
            return results
            
        except Exception as e:
            logger.error("Educational KYC process failed", 
                        provider=request.organisation_name, 
                        error=str(e))
            raise
    
    async def verify_company_registration(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        """Verify company registration with Companies House"""
        try:
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="companies-house-uk",
                    tool="company_search",
                    args={
                        "company_number": request.company_number,
                        "company_name": request.organisation_name
                    }
                )
            else:
                # Fallback for development/testing
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
                data_source="Companies House",
                timestamp=datetime.now(),
                details=response,
                recommendations=[] if status == "passed" else ["Review company status and directors"]
            )
            
        except Exception as e:
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
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="ukrlp",
                    tool="provider_lookup",
                    args={"ukprn": request.ukprn}
                )
            else:
                response = await self._mock_ukprn_check(request.ukprn)
            
            is_verified = response.get("verification_status") == "Verified"
            is_active = response.get("provider_status") == "Active"
            
            status = "passed" if is_verified and is_active else "flagged"
            risk_score = 0.1 if status == "passed" else 0.6
            
            return EducationalVerificationResult(
                check_type="ukprn_validation",
                status=status,
                risk_score=risk_score,
                data_source="UKRLP",
                timestamp=datetime.now(),
                details=response
            )
            
        except Exception as e:
            return self._create_error_result("ukprn_validation", str(e))
    
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
        """Assess Ofsted inspection rating"""
        try:
            if self.mcp_client:
                response = await self.mcp_client.call_tool(
                    server="ofsted-reports",
                    tool="provider_inspection_history",
                    args={
                        "provider_name": request.organisation_name,
                        "ukprn": request.ukprn,
                        "postcode": request.postcode
                    }
                )
            else:
                response = await self._mock_ofsted_check(request.organisation_name)
            
            latest_rating = response.get("latest_overall_effectiveness")
            safeguarding = response.get("safeguarding_effectiveness")
            
            # Risk scoring based on Ofsted grades
            risk_mapping = {
                "Outstanding": 0.05,
                "Good": 0.15,
                "Requires improvement": 0.5,
                "Inadequate": 0.9
            }
            
            risk_score = risk_mapping.get(latest_rating, 0.7)
            
            # Additional risk if safeguarding issues
            if safeguarding in ["Requires improvement", "Inadequate"]:
                risk_score = min(risk_score + 0.3, 1.0)
            
            status = "passed" if risk_score < 0.3 else "flagged" if risk_score < 0.7 else "failed"
            
            recommendations = []
            if latest_rating in ["Requires improvement", "Inadequate"]:
                recommendations.append("Monitor improvement plan progress")
            if safeguarding in ["Requires improvement", "Inadequate"]:
                recommendations.append("Enhanced safeguarding due diligence required")
            
            return EducationalVerificationResult(
                check_type="ofsted_rating",
                status=status,
                risk_score=risk_score,
                data_source="Ofsted",
                timestamp=datetime.now(),
                details=response,
                recommendations=recommendations
            )
            
        except Exception as e:
            return self._create_error_result("ofsted_rating", str(e))
    
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
            "latest_inspection_date": "2023-01-01"
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
