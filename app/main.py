# app/main.py
# Updated FastAPI app with JCQ National Centre Number verification

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import structlog
import os
from typing import Dict, List, Optional
from datetime import datetime
import json
import asyncio
import uuid

# Import our enhanced KYC system with JCQ
from app.services.real_kyc_orchestrator import (
    RealEducationalKYCOrchestrator,
    VerificationResult,
    VerificationStatus
)
from app.services.jcq_integration import (
    JCQCentreAPI,
    EnhancedEducationalKYCOrchestrator
)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# In-memory storage for demo (Railway will provide PostgreSQL later)
providers_db = []
verification_logs = []
processing_queue = {}

# Initialize enhanced KYC orchestrator with JCQ
base_orchestrator = RealEducationalKYCOrchestrator()
kyc_orchestrator = EnhancedEducationalKYCOrchestrator(base_orchestrator)
jcq_api = JCQCentreAPI()

def check_api_configuration() -> Dict[str, bool]:
    """Check which APIs are properly configured"""
    return {
        "companies_house_api": bool(os.getenv('COMPANIES_HOUSE_API_KEY')) and os.getenv('COMPANIES_HOUSE_API_KEY') != 'your_key_here',
        "ukrlp_api": bool(os.getenv('UKRLP_USERNAME')) and bool(os.getenv('UKRLP_PASSWORD')),
        "sanctions_api": True,  # Always available (uses public data)
        "ofqual_api": True,     # Always available (uses public data)
        "jcq_api": True,        # Always available (uses JCQ directory lookup)
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Educational KYC application with JCQ integration")
    
    # Check API configuration
    api_status = check_api_configuration()
    logger.info("API Configuration Status", **api_status)
    
    # Add sample data for demo
    sample_providers = [
        {
            "id": 1,
            "organisation_name": "Excellent Sixth Form College",
            "provider_type": "Sixth Form College",
            "company_number": "12345678",
            "ukprn": "10012345",
            "jcq_centre_number": "12345",
            "postcode": "M1 1AA",
            "status": "approved",
            "risk_level": "low",
            "created_at": "2025-07-18",
            "kyc_results": {
                "companies_house": {"status": "passed", "risk_score": 0.1},
                "ukprn_validation": {"status": "passed", "risk_score": 0.1},
                "jcq_centre_verification": {"status": "passed", "risk_score": 0.1},
                "ofqual_check": {"status": "passed", "risk_score": 0.1},
                "sanctions_screening": {"status": "passed", "risk_score": 0.05},
                "overall_risk": 0.08
            }
        }
    ]
    
    providers_db.extend(sample_providers)
    
    yield
    
    logger.info("Shutting down Educational KYC application")

app = FastAPI(
    title="UK Educational Provider KYC with JCQ Verification",
    description="Real-time KYC verification for UK educational providers including JCQ National Centre Numbers",
    version="2.1.0",
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
    pass  # Directory might not exist yet

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    stats = {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending", "processing"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "jcq_verified": len([p for p in providers_db if p.get("jcq_centre_number") and 
                           p.get("kyc_results", {}).get("jcq_centre_verification", {}).get("status") == "passed"])
    }
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "providers": providers_db, "stats": stats}
    )

@app.get("/onboard", response_class=HTMLResponse)
async def onboard_form(request: Request):
    """Provider onboarding form with JCQ centre number"""
    api_status = check_api_configuration()
    return templates.TemplateResponse(
        "onboard_with_jcq.html", 
        {"request": request, "api_status": api_status}
    )

@app.post("/onboard")
async def onboard_provider(request: Request, background_tasks: BackgroundTasks):
    """Process provider onboarding with JCQ verification"""
    form_data = await request.form()
    
    # Generate unique ID for this verification
    verification_id = str(uuid.uuid4())
    
    # Extract form data including JCQ centre number
    provider_data = {
        "verification_id": verification_id,
        "organisation_name": form_data.get("organisation_name"),
        "provider_type": form_data.get("provider_type"),
        "company_number": form_data.get("company_number"),
        "ukprn": form_data.get("ukprn"),
        "jcq_centre_number": form_data.get("jcq_centre_number"),  # New field
        "postcode": form_data.get("postcode"),
        "contact_email": form_data.get("contact_email"),
        "address": form_data.get("address")
    }
    
    # Create provider record with processing status
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
    
    # Start enhanced KYC verification in background (now includes JCQ)
    background_tasks.add_task(process_enhanced_kyc, verification_id, provider_data)
    
    # Return processing page
    return templates.TemplateResponse(
        "processing_with_jcq.html", 
        {
            "request": request, 
            "provider": new_provider,
            "verification_id": verification_id
        }
    )

async def process_enhanced_kyc(verification_id: str, provider_data: Dict):
    """Background task to process enhanced KYC verification including JCQ"""
    logger.info("Starting enhanced KYC verification with JCQ", verification_id=verification_id)
    
    try:
        processing_queue[verification_id] = "in_progress"
        
        # Run enhanced KYC verification (includes JCQ if provided)
        results = await kyc_orchestrator.process_provider_kyc_with_jcq(provider_data)
        
        # Find the provider in our database
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        
        if provider:
            # Process results
            kyc_results = {}
            overall_risk_score = 0.5
            overall_status = "approved"
            risk_level = "medium"
            
            for result in results:
                kyc_results[result.check_type] = {
                    "status": result.status.value,
                    "risk_score": result.risk_score,
                    "data_source": result.data_source,
                    "confidence": result.confidence,
                    "details": result.details,
                    "recommendations": result.recommendations or [],
                    "timestamp": result.timestamp.isoformat()
                }
                
                # Update overall risk assessment
                if result.check_type in ["risk_assessment", "enhanced_risk_assessment"]:
                    overall_risk_score = result.risk_score
                    
                    if result.status == VerificationStatus.FAILED:
                        overall_status = "rejected"
                        risk_level = "high"
                    elif result.status == VerificationStatus.FLAGGED:
                        overall_status = "review_required"
                        risk_level = "medium" if overall_risk_score < 0.6 else "high"
                    else:
                        overall_status = "approved"
                        risk_level = "low" if overall_risk_score < 0.3 else "medium"
            
            # Update provider record
            provider.update({
                "status": overall_status,
                "risk_level": risk_level,
                "kyc_results": kyc_results,
                "overall_risk_score": overall_risk_score,
                "processing_completed": datetime.now().isoformat(),
                "verification_summary": {
                    "total_checks": len(results),
                    "passed": len([r for r in results if r.status == VerificationStatus.PASSED]),
                    "flagged": len([r for r in results if r.status == VerificationStatus.FLAGGED]),
                    "failed": len([r for r in results if r.status == VerificationStatus.FAILED]),
                    "errors": len([r for r in results if r.status == VerificationStatus.ERROR]),
                    "includes_jcq": bool(provider_data.get("jcq_centre_number"))
                }
            })
            
            processing_queue[verification_id] = "completed"
            
            logger.info("Enhanced KYC verification completed", 
                       verification_id=verification_id,
                       status=overall_status,
                       risk_score=overall_risk_score,
                       includes_jcq=bool(provider_data.get("jcq_centre_number")))
        
    except Exception as e:
        logger.error("Enhanced KYC verification failed", verification_id=verification_id, error=str(e))
        
        # Update provider with error status
        provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
        if provider:
            provider.update({
                "status": "error",
                "risk_level": "unknown",
                "error_message": str(e),
                "processing_completed": datetime.now().isoformat()
            })
        
        processing_queue[verification_id] = "error"

@app.get("/verification/{verification_id}")
async def get_verification_status(verification_id: str):
    """Get real-time verification status"""
    provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Verification not found")
    
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
    """Lookup JCQ centre information"""
    try:
        verification_result = await jcq_api.verify_centre_number(centre_number)
        qualification_info = await jcq_api.get_qualification_info(centre_number)
        
        return {
            "centre_number": centre_number,
            "verification": {
                "status": verification_result.status.value,
                "risk_score": verification_result.risk_score,
                "confidence": verification_result.confidence,
                "details": verification_result.details,
                "recommendations": verification_result.recommendations
            },
            "qualifications": qualification_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("JCQ centre lookup error", centre_number=centre_number, error=str(e))
        raise HTTPException(status_code=500, detail=f"JCQ lookup failed: {str(e)}")

@app.get("/results/{verification_id}", response_class=HTMLResponse)
async def verification_results(verification_id: str, request: Request):
    """Display verification results page with JCQ information"""
    provider = next((p for p in providers_db if p.get("verification_id") == verification_id), None)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    return templates.TemplateResponse(
        "results_with_jcq.html", 
        {"request": request, "provider": provider}
    )

@app.get("/api/providers")
async def get_providers():
    """API endpoint to get all providers"""
    return {"providers": providers_db, "total": len(providers_db)}

@app.get("/api/providers/{provider_id}")
async def get_provider(provider_id: int):
    """Get specific provider details"""
    provider = next((p for p in providers_db if p["id"] == provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics including JCQ metrics"""
    api_status = check_api_configuration()
    
    jcq_stats = {
        "total_with_jcq": len([p for p in providers_db if p.get("jcq_centre_number")]),
        "jcq_verified": len([p for p in providers_db if p.get("jcq_centre_number") and 
                           p.get("kyc_results", {}).get("jcq_centre_verification", {}).get("status") == "passed"]),
        "jcq_failed": len([p for p in providers_db if p.get("jcq_centre_number") and 
                         p.get("kyc_results", {}).get("jcq_centre_verification", {}).get("status") == "failed"])
    }
    
    return {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending", "processing"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "processing": len([p for p in providers_db if p["status"] == "processing"]),
        "api_status": api_status,
        "verification_queue": len(processing_queue),
        "jcq_statistics": jcq_stats
    }

@app.get("/api/config")
async def get_api_configuration():
    """Get API configuration status including JCQ"""
    config = check_api_configuration()
    
    config_details = {
        "companies_house": {
            "enabled": config["companies_house_api"],
            "description": "Companies House API for company verification",
            "status": "configured" if config["companies_house_api"] else "missing_api_key"
        },
        "ukrlp": {
            "enabled": config["ukrlp_api"],
            "description": "UK Register of Learning Providers SOAP API",
            "status": "configured" if config["ukrlp_api"] else "missing_credentials"
        },
        "sanctions": {
            "enabled": config["sanctions_api"],
            "description": "UK Treasury and OFAC sanctions screening",
            "status": "configured"
        },
        "ofqual": {
            "enabled": config["ofqual_api"],
            "description": "Ofqual awarding organisation recognition",
            "status": "configured"
        },
        "jcq": {
            "enabled": config["jcq_api"],
            "description": "JCQ National Centre Number verification",
            "status": "configured"
        }
    }
    
    return {
        "api_configuration": config_details,
        "overall_status": "fully_configured" if all(config.values()) else "partial_configuration",
        "missing_apis": [k for k, v in config.items() if not v]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    api_status = check_api_configuration()
    
    return {
        "status": "healthy",
        "service": "educational-kyc-with-jcq",
        "version": "2.1.0",
        "providers_count": len(providers_db),
        "processing_queue": len(processing_queue),
        "api_integrations": api_status,
        "jcq_integration": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test-apis")
async def test_api_connections():
    """Test endpoint to verify API connections including JCQ"""
    test_results = {}
    
    # Test Companies House API
    if base_orchestrator.companies_house:
        try:
            result = await base_orchestrator.companies_house.verify_company("08242665", "Companies House")
            test_results["companies_house"] = {
                "status": "success",
                "response_status": result.status.value,
                "risk_score": result.risk_score
            }
        except Exception as e:
            test_results["companies_house"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        test_results["companies_house"] = {
            "status": "not_configured",
            "message": "API key not provided"
        }
    
    # Test JCQ API
    try:
        result = await jcq_api.verify_centre_number("12345", "Test Centre")
        test_results["jcq"] = {
            "status": "success",
            "response_status": result.status.value,
            "risk_score": result.risk_score,
            "confidence": result.confidence
        }
    except Exception as e:
        test_results["jcq"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Sanctions API
    try:
        result = await base_orchestrator.sanctions.check_sanctions("Test Organisation")
        test_results["sanctions"] = {
            "status": "success",
            "response_status": result.status.value
        }
    except Exception as e:
        test_results["sanctions"] = {
            "status": "error",
            "error": str(e)
        }
    
    return {
        "test_results": test_results,
        "jcq_integration_active": True,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
