# app/main.py - Updated with Enhanced Companies House Integration

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os
from typing import Dict, List, Optional
from datetime import datetime
import json
import asyncio
import uuid
import aiohttp
import requests

# Import the enhanced Companies House service
from app.services.companies_house_enhanced import EnhancedCompaniesHouseAPI, get_enhanced_companies_house_result

# In-memory storage for demo
providers_db = []
processing_queue = {}

def check_api_configuration() -> Dict[str, bool]:
    """Check which APIs are properly configured"""
    companies_house_api = EnhancedCompaniesHouseAPI()
    
    return {
        "companies_house_api": companies_house_api.is_configured(),
        "basic_verification": True,  # Always available
        "jcq_simulation": True,      # Simulated JCQ checks
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Educational KYC application (Railway-safe version)")
    
    # Check Companies House API configuration
    api_status = check_api_configuration()
    if api_status["companies_house_api"]:
        print("✓ Companies House API configured")
    else:
        print("⚠ Companies House API not configured - using limited verification")
    
    # Add sample data
    sample_providers = [
        {
            "id": 1,
            "organisation_name": "Excellent Training Academy",
            "provider_type": "Training Provider",
            "company_number": "12345678",
            "ukprn": "10012345",
            "jcq_centre_number": "12345",
            "postcode": "M1 1AA",
            "status": "approved",
            "risk_level": "low",
            "created_at": "2025-07-18",
            "kyc_results": {
                "basic_checks": {"status": "passed", "risk_score": 0.2},
                "companies_house": {"status": "passed", "risk_score": 0.1},
                "jcq_verification": {"status": "passed", "risk_score": 0.1},
                "overall_risk": 0.15
            }
        }
    ]
    
    providers_db.extend(sample_providers)
    
    yield
    
    print("Shutting down Educational KYC application")

app = FastAPI(
    title="UK Educational Provider KYC (Railway-Safe)",
    description="Enhanced KYC verification for UK educational providers with Companies House integration",
    version="2.1-enhanced",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates setup
templates = Jinja2Templates(directory="templates")

# Static files (will be created)
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except RuntimeError:
    pass

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    stats = {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending", "processing"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "jcq_verified": len([p for p in providers_db if p.get("jcq_centre_number")])
    }
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "providers": providers_db, "stats": stats}
    )

@app.get("/onboard", response_class=HTMLResponse)
async def onboard_form(request: Request):
    """Provider onboarding form"""
    api_status = check_api_configuration()
    return templates.TemplateResponse(
        "onboard_with_jcq.html", 
        {"request": request, "api_status": api_status}
    )

@app.post("/onboard")
async def onboard_provider(request: Request, background_tasks: BackgroundTasks):
    """Process provider onboarding with enhanced verification"""
    form_data = await request.form()
    
    verification_id = str(uuid.uuid4())
    
    provider_data = {
        "verification_id": verification_id,
        "organisation_name": form_data.get("organisation_name"),
        "provider_type": form_data.get("provider_type"),
        "company_number": form_data.get("company_number"),
        "ukprn": form_data.get("ukprn"),
        "jcq_centre_number": form_data.get("jcq_centre_number"),
        "postcode": form_data.get("postcode"),
        "contact_email": form_data.get("contact_email"),
        "address": form_data.get("address")
    }
    
    new_provider = {
        "id": len(providers_db) + 1,
        "verification_id": verification_id,
        "organisation_name": provider_data["organisation_name"],
        "provider_type": provider_data["provider_type"],
        "company_number": provider_data.get("company_number"),
        "ukprn": provider_data.get("ukprn"),
        "jcq_centre_number": provider_data.get("jcq_centre_number"),
        "postcode": provider_data["postcode"],
        "status": "processing",
        "risk_level": "unknown",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kyc_results": {},
        "processing_started": datetime.now().isoformat()
    }
    
    providers_db.append(new_provider)
    processing_queue[verification_id] = "started"
    
    # Start enhanced KYC verification
    background_tasks.add_task(process_enhanced_kyc, verification_id, provider_data)
    
    return templates.TemplateResponse(
        "processing_with_jcq.html", 
        {
            "request": request, 
            "provider": new_provider,
            "verification_id": verification_id
        }
    )

async def process_enhanced_kyc(verification_id: str, provider_data: Dict):
    """Enhanced KYC verification with comprehensive Companies House checks"""
    print(f"Starting enhanced KYC verification: {verification_id}")
    
    try:
        processing_queue[verification_id] = "in_progress"
        
        # Simulate initial processing
        await asyncio.sleep(2)
        
        # Find provider
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        
        if provider:
            # Enhanced verification results
            kyc_results = {}
            
            # Basic format validation
            kyc_results["basic_validation"] = {
                "status": "passed",
                "risk_score": 0.1,
                "data_source": "Format Validation",
                "details": {"organisation_name": provider_data["organisation_name"]},
                "timestamp": datetime.now().isoformat()
            }
            
            # Enhanced Companies House check
            if provider_data.get("company_number"):
                print(f"Running enhanced Companies House check for: {provider_data['company_number']}")
                ch_result = await get_enhanced_companies_house_result(
                    provider_data["company_number"],
                    provider_data.get("organisation_name")
                )
                
                # Transform the enhanced result to fit our schema
                kyc_results["companies_house"] = {
                    "status": ch_result.get("status", "error"),
                    "risk_score": ch_result.get("risk_score", 0.5),
                    "data_source": ch_result.get("data_source", "Companies House API"),
                    "confidence": ch_result.get("confidence", 0.0),
                    "details": ch_result.get("details", {}),
                    "recommendations": ch_result.get("recommendations", []),
                    "timestamp": ch_result.get("timestamp", datetime.now().isoformat())
                }
                
                # Add any specific risk factors from Companies House
                if ch_result.get("details", {}).get("risk_factors"):
                    print(f"Risk factors identified: {ch_result['details']['risk_factors']}")
            
            # JCQ simulation
            if provider_data.get("jcq_centre_number"):
                jcq_result = simulate_jcq_check(provider_data["jcq_centre_number"])
                kyc_results["jcq_verification"] = jcq_result
            
            # UKPRN format check
            if provider_data.get("ukprn"):
                ukprn_result = validate_ukprn_format(provider_data["ukprn"])
                kyc_results["ukprn_validation"] = ukprn_result
            
            # Basic sanctions simulation
            sanctions_result = simulate_sanctions_check(provider_data["organisation_name"])
            kyc_results["sanctions_screening"] = sanctions_result
            
            # Calculate overall risk using weighted scoring
            risk_scores = []
            risk_weights = {
                "companies_house": 0.35,  # Higher weight for Companies House
                "jcq_verification": 0.25,
                "ukprn_validation": 0.15,
                "sanctions_screening": 0.15,
                "basic_validation": 0.10
            }
            
            weighted_risk = 0.0
            total_weight = 0.0
            
            for check_name, result in kyc_results.items():
                weight = risk_weights.get(check_name, 0.1)
                if "risk_score" in result:
                    weighted_risk += result["risk_score"] * weight
                    total_weight += weight
            
            overall_risk_score = weighted_risk / total_weight if total_weight > 0 else 0.5
            
            # Determine status based on risk and Companies House result
            if overall_risk_score < 0.3:
                overall_status = "approved"
                risk_level = "low"
            elif overall_risk_score < 0.6:
                overall_status = "review_required"
                risk_level = "medium"
            else:
                overall_status = "rejected"
                risk_level = "high"
            
            # Override if Companies House check failed completely
            if kyc_results.get("companies_house", {}).get("status") == "failed":
                overall_status = "review_required"
                risk_level = "medium" if risk_level == "low" else risk_level
            
            # Risk assessment summary
            kyc_results["risk_assessment"] = {
                "status": "completed",
                "risk_score": overall_risk_score,
                "data_source": "Enhanced Risk Engine",
                "details": {
                    "total_checks": len(kyc_results) - 1,  # Exclude risk_assessment itself
                    "risk_calculation": "weighted_average",
                    "primary_factors": []
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add primary risk factors from Companies House
            if kyc_results.get("companies_house", {}).get("recommendations"):
                kyc_results["risk_assessment"]["details"]["primary_factors"].extend(
                    kyc_results["companies_house"]["recommendations"]
                )
            
            # Update provider
            provider.update({
                "status": overall_status,
                "risk_level": risk_level,
                "kyc_results": kyc_results,
                "overall_risk_score": overall_risk_score,
                "processing_completed": datetime.now().isoformat(),
                "verification_summary": {
                    "total_checks": len(kyc_results) - 1,
                    "includes_jcq": bool(provider_data.get("jcq_centre_number")),
                    "includes_companies_house": bool(provider_data.get("company_number")),
                    "enhanced_verification": True
                }
            })
            
            processing_queue[verification_id] = "completed"
            print(f"Enhanced KYC completed: {verification_id} - Status: {overall_status}, Risk: {risk_level}")
        
    except Exception as e:
        print(f"KYC verification error: {verification_id} - {str(e)}")
        
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        if provider:
            provider.update({
                "status": "error",
                "risk_level": "unknown",
                "error_message": str(e),
                "processing_completed": datetime.now().isoformat()
            })
        
        processing_queue[verification_id] = "error"

@app.get("/companies-house/quick-check/{company_number}")
async def quick_companies_house_check(company_number: str):
    """Quick Companies House check endpoint"""
    api = EnhancedCompaniesHouseAPI()
    
    if not api.is_configured():
        return {
            "error": "Companies House API not configured",
            "exists": False,
            "active": False
        }
    
    result = await api.quick_company_check(company_number)
    return result

def simulate_jcq_check(centre_number: str) -> Dict:
    """Simulate JCQ centre verification"""
    if not centre_number or len(centre_number) != 5 or not centre_number.isdigit():
        return {
            "status": "failed",
            "risk_score": 0.8,
            "data_source": "JCQ Simulation",
            "details": {"error": "Invalid JCQ centre number format"},
            "timestamp": datetime.now().isoformat()
        }
    
    # Simulate known good centres
    if centre_number in ["12345", "23456", "34567"]:
        return {
            "status": "passed",
            "risk_score": 0.1,
            "data_source": "JCQ Simulation",
            "details": {
                "centre_number": centre_number,
                "centre_name": f"Educational Centre {centre_number}",
                "centre_type": "Secondary School",
                "active": True,
                "qualifications": ["GCSE", "A Level"]
            },
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "flagged",
            "risk_score": 0.4,
            "data_source": "JCQ Simulation",
            "details": {
                "centre_number": centre_number,
                "message": "Centre not found in simulation database"
            },
            "timestamp": datetime.now().isoformat()
        }

def validate_ukprn_format(ukprn: str) -> Dict:
    """Validate UKPRN format"""
    if not ukprn or len(ukprn) != 8 or not ukprn.isdigit() or not ukprn.startswith('10'):
        return {
            "status": "failed",
            "risk_score": 0.6,
            "data_source": "UKPRN Format Validation",
            "details": {"error": "Invalid UKPRN format"},
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "status": "passed",
        "risk_score": 0.1,
        "data_source": "UKPRN Format Validation",
        "details": {"ukprn": ukprn, "format_valid": True},
        "timestamp": datetime.now().isoformat()
    }

def simulate_sanctions_check(organisation_name: str) -> Dict:
    """Simulate sanctions screening"""
    # Simple word-based check
    flagged_words = ["banned", "sanctioned", "prohibited", "blocked"]
    
    if any(word in organisation_name.lower() for word in flagged_words):
        return {
            "status": "flagged",
            "risk_score": 0.9,
            "data_source": "Sanctions Simulation",
            "details": {"matches": True, "organisation_name": organisation_name},
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "status": "passed",
        "risk_score": 0.05,
        "data_source": "Sanctions Simulation",
        "details": {"matches": False, "organisation_name": organisation_name},
        "timestamp": datetime.now().isoformat()
    }

@app.get("/verification/{verification_id}")
async def get_verification_status(verification_id: str):
    """Get verification status"""
    provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
    
    if not provider:
        return {"error": "Verification not found"}
    
    processing_status = processing_queue.get(verification_id, "unknown")
    
    return {
        "verification_id": verification_id,
        "status": provider["status"],
        "processing_status": processing_status,
        "risk_level": provider.get("risk_level"),
        "organisation_name": provider["organisation_name"],
        "jcq_centre_number": provider.get("jcq_centre_number"),
        "created_at": provider["created_at"],
        "kyc_results": provider.get("kyc_results", {}),
        "verification_summary": provider.get("verification_summary", {}),
        "progress": {
            "started": processing_status in ["started", "in_progress", "completed", "error"],
            "in_progress": processing_status == "in_progress",
            "completed": processing_status == "completed",
            "error": processing_status == "error"
        }
    }

@app.get("/jcq/centre/{centre_number}")
async def lookup_jcq_centre(centre_number: str):
    """JCQ centre lookup"""
    result = simulate_jcq_check(centre_number)
    return {
        "centre_number": centre_number,
        "verification": result,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/results/{verification_id}", response_class=HTMLResponse)
async def verification_results(verification_id: str, request: Request):
    """Results page"""
    provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
    
    if not provider:
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "message": "Verification not found"}
        )
    
    return templates.TemplateResponse(
        "results.html", 
        {"request": request, "provider": provider}
    )

@app.get("/api/stats")
async def get_stats():
    """Dashboard statistics"""
    api_status = check_api_configuration()
    
    return {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending", "processing"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "processing": len([p for p in providers_db if p["status"] == "processing"]),
        "api_status": api_status,
        "verification_queue": len(processing_queue),
        "version": "enhanced"
    }

@app.get("/health")
async def health_check():
    """Health check with enhanced status"""
    api_status = check_api_configuration()
    
    return {
        "status": "healthy",
        "service": "educational-kyc-enhanced",
        "version": "2.1-enhanced",
        "providers_count": len(providers_db),
        "api_configurations": api_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
