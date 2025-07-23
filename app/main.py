# app/main.py - Updated with Educational KYC Orchestrator Integration

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

# Import the enhanced Companies House service (for quick checks)
from app.services.companies_house_enhanced import EnhancedCompaniesHouseAPI, get_enhanced_companies_house_result

# Import the Educational KYC Orchestrator
from app.services.education_kyc_orchestrator import (
    UKEducationalKYCOrchestrator, 
    EducationalProviderRequest,
    ProviderType,
    EducationalVerificationResult
)

# In-memory storage for demo
providers_db = []
processing_queue = {}

def check_api_configuration() -> Dict[str, bool]:
    """Check which APIs are properly configured"""
    companies_house_api = EnhancedCompaniesHouseAPI()
    
    return {
        "companies_house_api": companies_house_api.is_configured(),
        "orchestrator_available": True,  # Orchestrator is always available
        "basic_verification": True,      # Always available
        "jcq_simulation": True,          # Simulated JCQ checks
    }

def map_provider_type(provider_type_str: str) -> ProviderType:
    """Map form provider type to orchestrator enum"""
    mapping = {
        "Training Provider": ProviderType.TRAINING_PROVIDER,
        "FE College": ProviderType.FE_COLLEGE,
        "HE Institution": ProviderType.HE_INSTITUTION,
        "Apprenticeship Provider": ProviderType.APPRENTICESHIP_PROVIDER,
        "Private Training": ProviderType.PRIVATE_TRAINING,
        "Adult Community": ProviderType.ADULT_COMMUNITY
    }
    return mapping.get(provider_type_str, ProviderType.TRAINING_PROVIDER)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Educational KYC application with Orchestrator")
    
    # Check API configuration
    api_status = check_api_configuration()
    if api_status["companies_house_api"]:
        print("✓ Companies House API configured")
    else:
        print("⚠ Companies House API not configured - using limited verification")
    
    if api_status["orchestrator_available"]:
        print("✓ Educational KYC Orchestrator available")
    
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
                "company_registration": {"status": "passed", "risk_score": 0.1},
                "ukprn_validation": {"status": "passed", "risk_score": 0.1},
                "educational_risk_assessment": {"status": "approved", "risk_score": 0.15},
                "overall_risk": 0.15
            }
        }
    ]
    
    providers_db.extend(sample_providers)
    
    yield
    
    print("Shutting down Educational KYC application")

app = FastAPI(
    title="UK Educational Provider KYC (With Orchestrator)",
    description="Comprehensive KYC verification for UK educational providers using orchestrated workflow",
    version="3.0-orchestrator",
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
    """Process provider onboarding with orchestrated verification"""
    form_data = await request.form()
    
    verification_id = str(uuid.uuid4())
    
    provider_data = {
        "verification_id": verification_id,
        "organisation_name": form_data.get("organisation_name"),
        "trading_name": form_data.get("trading_name"),
        "provider_type": form_data.get("provider_type"),
        "company_number": form_data.get("company_number"),
        "ukprn": form_data.get("ukprn"),
        "jcq_centre_number": form_data.get("jcq_centre_number"),
        "postcode": form_data.get("postcode"),
        "contact_email": form_data.get("contact_email"),
        "address": form_data.get("address"),
        "qualifications_offered": form_data.get("qualifications_offered", "").split(",") if form_data.get("qualifications_offered") else []
    }
    
    new_provider = {
        "id": len(providers_db) + 1,
        "verification_id": verification_id,
        "organisation_name": provider_data["organisation_name"],
        "trading_name": provider_data.get("trading_name"),
        "provider_type": provider_data["provider_type"],
        "company_number": provider_data.get("company_number"),
        "ukprn": provider_data.get("ukprn"),
        "jcq_centre_number": provider_data.get("jcq_centre_number"),
        "postcode": provider_data["postcode"],
        "contact_email": provider_data["contact_email"],
        "status": "processing",
        "risk_level": "unknown",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kyc_results": {},
        "processing_started": datetime.now().isoformat()
    }
    
    providers_db.append(new_provider)
    processing_queue[verification_id] = "started"
    
    # Start orchestrated KYC verification
    background_tasks.add_task(process_orchestrated_kyc, verification_id, provider_data)
    
    return templates.TemplateResponse(
        "processing_with_jcq.html", 
        {
            "request": request, 
            "provider": new_provider,
            "verification_id": verification_id
        }
    )

async def process_orchestrated_kyc(verification_id: str, provider_data: Dict):
    """Orchestrated KYC verification using the educational KYC orchestrator"""
    print(f"Starting orchestrated KYC verification: {verification_id}")
    
    try:
        processing_queue[verification_id] = "in_progress"
        
        # Find provider
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        
        if not provider:
            print(f"Provider not found for verification: {verification_id}")
            return
        
        # Create orchestrator
        orchestrator = UKEducationalKYCOrchestrator()
        
        # Create educational provider request
        educational_request = EducationalProviderRequest(
            organisation_name=provider_data["organisation_name"],
            trading_name=provider_data.get("trading_name"),
            company_number=provider_data["company_number"],
            ukprn=provider_data.get("ukprn"),
            provider_type=map_provider_type(provider_data.get("provider_type", "Training Provider")),
            contact_email=provider_data["contact_email"],
            address=provider_data["address"],
            postcode=provider_data["postcode"],
            qualifications_offered=provider_data.get("qualifications_offered", [])
        )
        
        print(f"Running orchestrated educational KYC for: {provider_data['organisation_name']}")
        
        # Run orchestrated verification
        verification_results = await orchestrator.process_educational_kyc(educational_request)
        
        # Convert orchestrator results to our existing format
        kyc_results = {}
        overall_risk_score = 0.0
        total_checks = 0
        risk_factors = []
        recommendations = []
        
        for result in verification_results:
            # Convert each verification result
            kyc_results[result.check_type] = {
                "status": result.status,
                "risk_score": result.risk_score,
                "data_source": result.data_source,
                "confidence": 0.9,  # Default confidence for orchestrator results
                "details": result.details,
                "recommendations": result.recommendations or [],
                "timestamp": result.timestamp.isoformat()
            }
            
            # Accumulate risk scores
            overall_risk_score += result.risk_score
            total_checks += 1
            
            # Collect risk factors and recommendations
            if result.recommendations:
                recommendations.extend(result.recommendations)
            
            if result.status in ["failed", "flagged"]:
                risk_factors.append(result.check_type)
        
        # Calculate average risk score
        if total_checks > 0:
            overall_risk_score = overall_risk_score / total_checks
        else:
            overall_risk_score = 0.5
        
        # Determine overall status and risk level based on orchestrator results
        risk_assessment = next((r for r in verification_results if r.check_type == "educational_risk_assessment"), None)
        
        if risk_assessment:
            # Use orchestrator's risk assessment
            orchestrator_status = risk_assessment.status
            risk_level_mapping = {
                "approved": "low",
                "approved_with_monitoring": "medium", 
                "enhanced_due_diligence_required": "high",
                "rejected": "critical"
            }
            
            overall_status = "approved" if orchestrator_status == "approved" else "review_required" if orchestrator_status in ["approved_with_monitoring", "enhanced_due_diligence_required"] else "rejected"
            risk_level = risk_level_mapping.get(orchestrator_status, "medium")
        else:
            # Fallback status determination
            if overall_risk_score < 0.3:
                overall_status = "approved"
                risk_level = "low"
            elif overall_risk_score < 0.6:
                overall_status = "review_required"
                risk_level = "medium"
            else:
                overall_status = "rejected"
                risk_level = "high"
        
        # Add overall summary
        kyc_results["verification_summary"] = {
            "status": "completed",
            "risk_score": overall_risk_score,
            "data_source": "Educational KYC Orchestrator",
            "details": {
                "total_checks": total_checks,
                "risk_factors": risk_factors,
                "orchestrator_version": "3.0",
                "includes_educational_checks": True
            },
            "recommendations": recommendations[:5],  # Limit to top 5 recommendations
            "timestamp": datetime.now().isoformat()
        }
        
        # Update provider with orchestrated results
        provider.update({
            "status": overall_status,
            "risk_level": risk_level,
            "kyc_results": kyc_results,
            "overall_risk_score": overall_risk_score,
            "processing_completed": datetime.now().isoformat(),
            "verification_summary": {
                "total_checks": total_checks,
                "includes_educational_verification": True,
                "orchestrator_used": True,
                "risk_factors_count": len(risk_factors),
                "recommendations_count": len(recommendations)
            }
        })
        
        processing_queue[verification_id] = "completed"
        print(f"Orchestrated KYC completed: {verification_id} - Status: {overall_status}, Risk: {risk_level}, Checks: {total_checks}")
        
    except Exception as e:
        print(f"Orchestrated KYC verification error: {verification_id} - {str(e)}")
        
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        if provider:
            provider.update({
                "status": "error",
                "risk_level": "unknown",
                "error_message": f"Orchestrator error: {str(e)}",
                "processing_completed": datetime.now().isoformat()
            })
        
        processing_queue[verification_id] = "error"

@app.get("/companies-house/quick-check/{company_number}")
async def quick_companies_house_check(company_number: str):
    """Quick Companies House check endpoint (legacy support)"""
    api = EnhancedCompaniesHouseAPI()
    
    if not api.is_configured():
        return {
            "error": "Companies House API not configured",
            "exists": False,
            "active": False
        }
    
    result = await api.quick_company_check(company_number)
    return result

@app.get("/verification/{verification_id}")
async def get_verification_status(verification_id: str):
    """Get verification status with orchestrator details"""
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
        "provider_type": provider.get("provider_type"),
        "ukprn": provider.get("ukprn"),
        "jcq_centre_number": provider.get("jcq_centre_number"),
        "created_at": provider["created_at"],
        "kyc_results": provider.get("kyc_results", {}),
        "verification_summary": provider.get("verification_summary", {}),
        "orchestrator_used": True,
        "progress": {
            "started": processing_status in ["started", "in_progress", "completed", "error"],
            "in_progress": processing_status == "in_progress",
            "completed": processing_status == "completed",
            "error": processing_status == "error"
        }
    }

@app.get("/jcq/centre/{centre_number}")
async def lookup_jcq_centre(centre_number: str):
    """JCQ centre lookup (legacy endpoint)"""
    result = simulate_jcq_check(centre_number)
    return {
        "centre_number": centre_number,
        "verification": result,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/results/{verification_id}", response_class=HTMLResponse)
async def verification_results(verification_id: str, request: Request):
    """Results page with orchestrator details"""
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
    """Dashboard statistics with orchestrator info"""
    api_status = check_api_configuration()
    
    return {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending", "processing"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "processing": len([p for p in providers_db if p["status"] == "processing"]),
        "api_status": api_status,
        "verification_queue": len(processing_queue),
        "orchestrator_enabled": True,
        "version": "3.0-orchestrator"
    }

@app.get("/health")
async def health_check():
    """Health check with orchestrator status"""
    api_status = check_api_configuration()
    
    return {
        "status": "healthy",
        "service": "educational-kyc-orchestrator",
        "version": "3.0-orchestrator",
        "providers_count": len(providers_db),
        "api_configurations": api_status,
        "orchestrator_available": True,
        "timestamp": datetime.now().isoformat()
    }

# Legacy simulation functions (still used by some endpoints)
def simulate_jcq_check(centre_number: str) -> Dict:
    """Simulate JCQ centre verification (legacy)"""
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
