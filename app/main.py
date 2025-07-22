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

# Import our real KYC system
from app.services.real_kyc_orchestrator import (
    RealEducationalKYCOrchestrator,
    VerificationResult,
    VerificationStatus
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

# Simple in-memory storage for demo (Railway will provide PostgreSQL)
providers_db = []
verification_logs = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Educational KYC application")
    
    # Add sample data for demo
    sample_providers = [
        {
            "id": 1,
            "organisation_name": "Excellence Training Academy",
            "provider_type": "Training Provider",
            "status": "approved",
            "risk_level": "low",
            "created_at": "2025-07-18",
            "kyc_results": {
                "companies_house": {"status": "passed", "risk_score": 0.1},
                "ukprn_validation": {"status": "passed", "risk_score": 0.1},
                "ofqual_check": {"status": "passed", "risk_score": 0.1},
                "overall_risk": 0.15
            }
        },
        {
            "id": 2,
            "organisation_name": "Digital Skills Institute",
            "provider_type": "Apprenticeship Provider",
            "status": "review_required",
            "risk_level": "medium",
            "created_at": "2025-07-19",
            "kyc_results": {
                "companies_house": {"status": "passed", "risk_score": 0.1},
                "ukprn_validation": {"status": "flagged", "risk_score": 0.4},
                "ofqual_check": {"status": "passed", "risk_score": 0.1},
                "overall_risk": 0.45
            }
        }
    ]
    
    providers_db.extend(sample_providers)
    
    yield
    
    logger.info("Shutting down Educational KYC application")

app = FastAPI(
    title="UK Educational Provider KYC",
    description="Comprehensive KYC system for UK educational providers",
    version="1.0.0",
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
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"])
    }
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "providers": providers_db, "stats": stats}
    )

@app.get("/onboard", response_class=HTMLResponse)
async def onboard_form(request: Request):
    """Provider onboarding form"""
    return templates.TemplateResponse("onboard.html", {"request": request})

@app.post("/onboard")
async def onboard_provider(request: Request):
    """Process provider onboarding"""
    form_data = await request.form()
    
    # Simple KYC simulation
    new_provider = {
        "id": len(providers_db) + 1,
        "organisation_name": form_data.get("organisation_name"),
        "provider_type": form_data.get("provider_type"),
        "company_number": form_data.get("company_number"),
        "ukprn": form_data.get("ukprn"),
        "postcode": form_data.get("postcode"),
        "status": "approved",  # Simplified for demo
        "risk_level": "low",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "kyc_results": {
            "companies_house": {"status": "passed", "risk_score": 0.1},
            "ukprn_validation": {"status": "passed", "risk_score": 0.1},
            "ofqual_check": {"status": "not_applicable", "risk_score": 0.2},
            "overall_risk": 0.13
        }
    }
    
    providers_db.append(new_provider)
    
    return templates.TemplateResponse(
        "results.html", 
        {"request": request, "provider": new_provider}
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
    """Get dashboard statistics"""
    return {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len([p for p in providers_db if p["status"] in ["review_required", "pending"]]),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "by_type": {}
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "educational-kyc",
        "version": "1.0.0",
        "providers_count": len(providers_db)
    }

@app.get("/api/sources")
async def get_data_sources():
    """Get information about data sources"""
    sources = {
        "ofqual": {"status": "active", "description": "Ofqual Register - Qualification validation"},
        "ofsted": {"status": "active", "description": "Ofsted Reports - Education quality inspection"},
        "esfa": {"status": "active", "description": "ESFA Register - Funding eligibility"},
        "companies_house": {"status": "active", "description": "Companies House - Corporate verification"},
        "ukrlp": {"status": "active", "description": "UK Register of Learning Providers"}
    }
    return sources

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
