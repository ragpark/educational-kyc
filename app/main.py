# app/main.py - Updated with Educational KYC Orchestrator Integration

from fastapi import FastAPI, Request, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import base64
from typing import Dict, List, Optional
from datetime import datetime
import json
import asyncio
import uuid
import aiohttp
import requests
import logging
from authlib.integrations.starlette_client import OAuth, OAuthError


def secure_filename(filename: str) -> str:
    """Return a secure version of a filename."""
    keep = {"-", "_", "."}
    filename = os.path.basename(filename)
    cleaned = []
    for ch in filename:
        if ch.isalnum() or ch in keep:
            cleaned.append(ch)
    return "".join(cleaned)

from app.mcp_wrapper import KYCContextSource

# Ofqual awarding organisation search
from app.services.ofqual_qualifications import OfqualQualificationsClient

# Import the enhanced Companies House service (for quick checks)
from app.services.companies_house_enhanced import (
    EnhancedCompaniesHouseAPI,
    get_enhanced_companies_house_result,
)

# Import the Educational KYC Orchestrator
from app.services.combined_orchestrator import CombinedEducationalKYCOrchestrator
from app.services.education_kyc_orchestrator import (
    EducationalProviderRequest,
    ProviderType,
    EducationalVerificationResult,
)
from app.vc_issue import create_verifiable_credential
from app.vc_verify import verify_credential
from app.qr_utils import generate_qr_code
from app.pdf_utils import generate_credential_pdf
from app.services.safeguarding_assessment import assess_safeguarding_policy
from app.services.image_relevance import assess_image_relevance
from app.centre_submission import (
    CentreSubmission,
    ParentOrganisation,
    DeliveryAddress,
    DeliverySite,
    QualificationRequest,
    StaffMember,
    ComplianceDeclarations,
)
from app.services.safeguarding_assessor import assess_safeguarding_document

try:
    from backend.recommend import app as recommend_api
    RECOMMENDER_AVAILABLE = True
except Exception:
    recommend_api = None
    RECOMMENDER_AVAILABLE = False

# In-memory storage for demo
providers_db = []
# Simplistic in-memory storage for qualification applications
applications_db: List[Dict] = []
centre_submissions: List[CentreSubmission] = []
processing_queue = {}

# Per-user document storage metadata
documents_storage: Dict[str, List[Dict]] = {}
# Directory to store uploaded files
UPLOAD_DIR = os.path.join("app", "static", "uploads")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth = OAuth()

# MCP wrapper instance (created during startup)
mcp_wrapper: KYCContextSource | None = None

# Demo users for login
users = {
    "centre1": {
        "name": "Example Learning Centre",
        "password": "centrepass",
        "role": "learning_centre",
    },
    "awarding1": {
        "name": "Example Awarding Organisation",
        "password": "awardingpass",
        "role": "awarding_organisation",
    },
}

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="microsoft",
    client_id=os.getenv("MICROSOFT_CLIENT_ID"),
    client_secret=os.getenv("MICROSOFT_CLIENT_SECRET"),
    server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def get_current_user(request: Request):
    """Retrieve the currently logged in user from the session"""
    username = request.session.get("user")
    if username:
        return users.get(username)
    return None


def check_api_configuration() -> Dict[str, bool]:
    """Check which APIs are properly configured"""
    companies_house_api = EnhancedCompaniesHouseAPI()

    return {
        "companies_house_api": companies_house_api.is_configured(),
        "orchestrator_available": True,  # Orchestrator is always available
        "basic_verification": True,  # Always available
        "jcq_simulation": True,  # Simulated JCQ checks
    }


def map_provider_type(provider_type_str: str) -> ProviderType:
    """Map form provider type to orchestrator enum"""
    mapping = {
        "Training Provider": ProviderType.TRAINING_PROVIDER,
        "FE College": ProviderType.FE_COLLEGE,
        "HE Institution": ProviderType.HE_INSTITUTION,
        "Apprenticeship Provider": ProviderType.APPRENTICESHIP_PROVIDER,
        "Private Training": ProviderType.PRIVATE_TRAINING,
        "Adult Community": ProviderType.ADULT_COMMUNITY,
    }
    return mapping.get(provider_type_str, ProviderType.TRAINING_PROVIDER)


class ProviderAPIRequest(BaseModel):
    """Input schema for the API onboarding endpoint."""

    organisation_name: str
    urn: str
    postcode: str
    company_number: str | None = None
    trading_name: Optional[str] = None
    provider_type: Optional[str] = "Training Provider"
    contact_email: Optional[str] = None
    address: Optional[str] = None
    ukprn: Optional[str] = None
    jcq_centre_number: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Educational KYC application with Orchestrator")

    global mcp_wrapper
    default_base = f"http://localhost:{os.getenv('PORT', '8080')}"
    mcp_wrapper = KYCContextSource(base_url=os.getenv("MCP_BASE_URL", "http://localhost:8080"))

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Check API configuration
    api_status = check_api_configuration()
    if api_status["companies_house_api"]:
        print("✓ Companies House API configured")
    else:
        print("⚠ Companies House API not configured - using limited verification")

    if api_status["orchestrator_available"]:
        print("✓ Certify3 KYC Orchestrator available")

    # Add sample data
    sample_providers = [
        {
            "id": 1,
            "organisation_name": "Excellent Training Academy",
            "provider_type": "Training Provider",
            "company_number": "12345678",
            "urn": "123456",  # Sample URN
            "ukprn": "10012345",
            "jcq_centre_number": "12345",
            "postcode": "M1 1AA",
            "status": "approved",
            "risk_level": "low",
            "created_at": "2025-07-18",
            "kyc_results": {
                "company_registration": {"status": "passed", "risk_score": 0.1},
                "ukprn_validation": {"status": "passed", "risk_score": 0.1},
                "educational_risk_assessment": {
                    "status": "approved",
                    "risk_score": 0.15,
                },
                "overall_risk": 0.15,
            },
        }
    ]

    providers_db.extend(sample_providers)

    yield

    print("Shutting down Educational KYC application")


app = FastAPI(
    title="UK Educational Provider KYC (With Orchestrator)",
    description="Comprehensive KYC verification for UK educational providers using orchestrated workflow",
    version="3.0-orchestrator",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "super-secret"))

# Mount recommendation API routes
if RECOMMENDER_AVAILABLE:
    app.include_router(recommend_api.router)

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
        "under_review": len(
            [
                p
                for p in providers_db
                if p["status"] in ["review_required", "pending", "processing"]
            ]
        ),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "jcq_verified": len([p for p in providers_db if p.get("jcq_centre_number")]),
        "centre_submissions": len(centre_submissions),
    }

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "providers": providers_db,
            "centre_submissions": centre_submissions,
            "stats": stats,
        },
    )
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    stats = {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len(
            [
                p
                for p in providers_db
                if p["status"] in ["review_required", "pending", "processing"]
            ]
        ),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "jcq_verified": len([p for p in providers_db if p.get("jcq_centre_number")]),
        "centre_submissions": len(centre_submissions),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "providers": providers_db,
            "centre_submissions": centre_submissions,
            "stats": stats,
        },
    )

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """Display the login form"""
    user = get_current_user(request)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle login submissions"""
    user = users.get(username)
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
        )
    request.session["user"] = username
    return RedirectResponse("/", status_code=302)


@app.get("/auth/{provider}")
async def auth(request: Request, provider: str):
    """Start OAuth flow with the given provider"""
    client = oauth.create_client(provider)
    if not client:
        return RedirectResponse("/login", status_code=302)
    redirect_uri = request.url_for("auth_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@app.get("/auth/{provider}/callback")
async def auth_callback(request: Request, provider: str):
    """Handle OAuth callback"""
    client = oauth.create_client(provider)
    if not client:
        return RedirectResponse("/login", status_code=302)
    try:
        token = await client.authorize_access_token(request)
    except OAuthError:
        return RedirectResponse("/login", status_code=302)
    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await client.parse_id_token(request, token)
        except Exception:
            userinfo = {}
    email = userinfo.get("email")
    if email:
        users.setdefault(
            email,
            {"name": userinfo.get("name", email), "password": None, "role": "external"},
        )
        request.session["user"] = email
        return RedirectResponse("/", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/login", status_code=302)


# ---------------------------------------------------------------------------
# New navigation pages for refactored information architecture


@app.get("/applications", response_class=HTMLResponse)
async def applications(request: Request):
    """List all applications"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user["role"] != "learning_centre":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Access restricted to learning providers"},
        )
    return templates.TemplateResponse(
        "applications.html",
        {"request": request, "applications": applications_db, "user": user},
    )


@app.get("/applications/{verification_id}", response_class=HTMLResponse)
async def application_detail(verification_id: str, request: Request):
    """View a single application"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if user["role"] != "learning_centre":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Access restricted to learning providers"},
        )
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Application not found for verification ID: {verification_id}",
            },
        )

    return templates.TemplateResponse(
        "provider_dashboard.html",
        {"request": request, "provider": provider, "user": user},
    )


@app.get("/my-organisation", response_class=HTMLResponse)
async def my_organisation(request: Request):
    """Organisation management page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("my_organisation.html", {"request": request, "user": user})


@app.get("/messages", response_class=HTMLResponse)
async def messages(request: Request):
    """Messages page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("messages.html", {"request": request, "user": user})


@app.get("/documents", response_class=HTMLResponse)
async def documents(request: Request):
    """Document repository page"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    user_docs = documents_storage.get(user["name"], [])
    logger.info(
        "Rendering documents page for %s with %d documents",
        user["name"],
        len(user_docs),
    )
    return templates.TemplateResponse(
        "documents.html", {"request": request, "user": user, "documents": user_docs}
    )


@app.post("/documents/upload")
async def upload_user_documents(request: Request, files: List[UploadFile] = File(...)):
    """Receive document uploads from the Documents page."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    user_docs = documents_storage.setdefault(user["name"], [])
    saved = []
    assessments = []
    for file in files:
        if not file.filename:
            continue
        filename = secure_filename(file.filename)
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        path = os.path.join(UPLOAD_DIR, stored_name)
        with open(path, "wb") as out:
            while True:
                chunk = await file.read(8192)
                if not chunk:
                    break
                out.write(chunk)
        assessment = None
        assessment_rationale = None
        image_relevance = None
        if "safeguard" in filename.lower():
            logger.info("Assessing safeguarding policy for %s", filename)
            assessment, assessment_rationale = await assess_safeguarding_policy(path)
            logger.info("Assessment result for %s: %s", filename, assessment)

        if (file.content_type or "").startswith("image/"):
            logger.info("Assessing image relevance for %s", filename)
            image_relevance = await assess_image_relevance(path)
            logger.info("Image assessment result for %s: %s", filename, image_relevance)

        user_docs.append(
            {
                "name": file.filename,
                "stored_name": stored_name,
                "uploaded_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "assessment": assessment,
                "assessment_rationale": assessment_rationale,
                "image_relevance": image_relevance,
            }
        )

        saved.append(file.filename)
        assessments.append(
            {
                "name": file.filename,
                "assessment": assessment,
                "image_relevance": image_relevance,
            }
        )

    return {"success": True, "files": saved, "assessments": assessments}


@app.post("/documents/{doc_id}/classify")
async def override_image_classification(
    request: Request, doc_id: int, classification: str = Form(...)
):
    """Allow manual override of image relevance classification."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    docs = documents_storage.get(user["name"], [])
    if 0 <= doc_id < len(docs):
        docs[doc_id]["image_relevance"] = classification
        logger.info(
            "Image relevance for %s set to %s", docs[doc_id]["name"], classification
        )
        return RedirectResponse("/documents", status_code=303)
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Informational page about the service"""
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Informational page about the service"""
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """User profile page"""
    return templates.TemplateResponse("profile.html", {"request": request})


@app.get("/onboard", response_class=HTMLResponse)
async def onboard_form(request: Request):
    """Provider onboarding form"""
    api_status = check_api_configuration()
    return templates.TemplateResponse(
        "onboard_with_jcq.html", {"request": request, "api_status": api_status}
    )


# ---------------------------------------------------------------------------
# Centre Submission workflow


@app.get("/centre-submission", response_class=HTMLResponse)
async def centre_submission_form(
    request: Request,
    organisation_id: Optional[str] = None,
    organisation_name: Optional[str] = None,
    qualification_id: Optional[str] = None,
    qualification_title: Optional[str] = None,
):
    user = get_current_user(request)
    centre_id = 1 if user and user.get("role") == "learning_centre" else None

    return templates.TemplateResponse(
        "centre_submission_form.html",
        {
            "request": request,
            "organisation_id": organisation_id,
            "organisation_name": organisation_name,
            "qualification_id": qualification_id,
            "qualification_title": qualification_title,
            "centre_id": centre_id,
            "recommendations_enabled": RECOMMENDER_AVAILABLE,
        },
    )


@app.post("/centre-submission")
async def submit_centre_submission(request: Request):
    form = await request.form()

    submission_id = str(uuid.uuid4())
    parent_org = ParentOrganisation(
        groupUkprn=form.get("group_ukprn"),
        legalName=form.get("legal_name"),
        organisationType=form.get("organisation_type"),
    )
    address = DeliveryAddress(
        line1=form.get("address_line1"),
        postcode=form.get("postcode"),
    )
    qualification = QualificationRequest(
        qualificationId=form.get("qualification_id"),
        aoId=form.get("ao_id"),
        aoName=form.get("ao_name"),
        title=form.get("title"),
        startDate=form.get("start_date"),
        expectedCohortSize=int(form.get("cohort_size")),
    )
    site = DeliverySite(
        siteId=form.get("site_id"),
        ukprn=form.get("site_ukprn"),
        siteName=form.get("site_name"),
        deliveryAddress=address,
        qualificationsRequested=[qualification],
    )
    staff_member = StaffMember(
        staffId=form.get("staff_id"),
        role=form.get("staff_role"),
        name=form.get("staff_name"),
        email=form.get("staff_email"),
    )
    compliance = ComplianceDeclarations(
        ofqualConditionsAcknowledged=bool(form.get("ofqual_ack")),
        gdprConsent=bool(form.get("gdpr_consent")),
        multiSiteResponsibilityConfirmed=bool(form.get("multi_site")),
    )

    submission = CentreSubmission(
        submissionId=submission_id,
        submittedAt=datetime.utcnow(),
        parentOrganisation=parent_org,
        deliverySites=[site],
        staff=[staff_member],
        complianceDeclarations=compliance,
    )

    centre_submissions.append(submission)

    # Add entry to applications list for display on /applications page
    applications_db.append(
        {
            "id": len(applications_db) + 1,
            "awarding_organisation": form.get("ao_name"),
            "rn": form.get("ao_id"),
            "qualification_number": form.get("qualification_id"),
            "qualification_title": form.get("title"),
            "status": "Pending",
        }
    )

    # After adding to our in-memory store, show the updated applications table
    user = get_current_user(request)
    return templates.TemplateResponse(
        "applications.html",
        {"request": request, "applications": applications_db, "user": user},
    )


@app.post("/onboard")
async def onboard_provider(request: Request, background_tasks: BackgroundTasks):
    """Process provider onboarding with orchestrated verification"""
    # Support JSON payloads in addition to standard form submissions
    if request.headers.get("content-type", "").startswith("application/json"):
        incoming = await request.json()
    else:
        incoming = await request.form()

    verification_id = str(uuid.uuid4())

    provider_data = {
        "verification_id": verification_id,
        "organisation_name": incoming.get("organisation_name"),
        "trading_name": incoming.get("trading_name"),
        "provider_type": incoming.get("provider_type"),
        "company_number": incoming.get("company_number"),
        "urn": incoming.get("urn"),  # Ofsted URN - now mandatory
        "ukprn": incoming.get("ukprn"),  # UKPRN - now optional
        "jcq_centre_number": incoming.get("jcq_centre_number"),
        "postcode": incoming.get("postcode"),
        "contact_email": incoming.get("contact_email"),
        "address": incoming.get("address"),
        "qualifications_offered": (
            incoming.get("qualifications_offered", "").split(",")
            if incoming.get("qualifications_offered")
            else []
        ),
    }

    new_provider = {
        "id": len(providers_db) + 1,
        "verification_id": verification_id,
        "organisation_name": provider_data["organisation_name"],
        "trading_name": provider_data.get("trading_name"),
        "provider_type": provider_data["provider_type"],
        "company_number": provider_data.get("company_number"),
        "urn": provider_data.get("urn"),  # Ofsted URN
        "ukprn": provider_data.get("ukprn"),  # UKPRN - now optional
        "jcq_centre_number": provider_data.get("jcq_centre_number"),
        "postcode": provider_data["postcode"],
        "contact_email": provider_data["contact_email"],
        "status": "processing",
        "risk_level": "unknown",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kyc_results": {},
        "processing_started": datetime.now().isoformat(),
    }

    providers_db.append(new_provider)
    # Application entries now originate from centre submissions
    processing_queue[verification_id] = "started"

    # Start orchestrated KYC verification
    background_tasks.add_task(process_orchestrated_kyc, verification_id, provider_data)

    return templates.TemplateResponse(
        "processing_with_jcq.html",
        {
            "request": request,
            "provider": new_provider,
            "verification_id": verification_id,
        },
    )


async def process_orchestrated_kyc(verification_id: str, provider_data: Dict):
    """Orchestrated KYC verification using the educational KYC orchestrator"""
    print(f"Starting orchestrated KYC verification: {verification_id}")

    try:
        processing_queue[verification_id] = "in_progress"

        # Find provider
        provider = next(
            (p for p in providers_db if p.get("verification_id") == verification_id),
            None,
        )

        if not provider:
            print(f"Provider not found for verification: {verification_id}")
            return

        # Create orchestrator
        orchestrator = CombinedEducationalKYCOrchestrator()

        # Create educational provider request
        educational_request = EducationalProviderRequest(
            organisation_name=provider_data["organisation_name"],
            trading_name=provider_data.get("trading_name"),
            company_number=provider_data["company_number"],
            urn=provider_data["urn"],  # Pass URN directly
            ukprn=provider_data.get("ukprn"),  # UKPRN is now optional
            provider_type=map_provider_type(
                provider_data.get("provider_type", "Training Provider")
            ),
            contact_email=provider_data["contact_email"],
            address=provider_data["address"],
            postcode=provider_data["postcode"],
            qualifications_offered=provider_data.get("qualifications_offered", []),
        )

        print(
            f"Running orchestrated educational KYC for: {provider_data['organisation_name']}"
        )

        # ALSO run the enhanced Companies House check separately to get full data
        companies_house_full_data = None
        if provider_data.get("company_number"):
            print(
                f"Running detailed Companies House check for: {provider_data['company_number']}"
            )
            try:
                companies_house_full_data = await get_enhanced_companies_house_result(
                    provider_data["company_number"],
                    provider_data.get("organisation_name"),
                )
                print(
                    f"Companies House API returned: {companies_house_full_data.get('status', 'unknown status')}"
                )
                if companies_house_full_data and companies_house_full_data.get(
                    "details"
                ):
                    print(
                        f"Companies House details keys: {list(companies_house_full_data['details'].keys())}"
                    )
            except Exception as e:
                print(f"Companies House API call failed: {str(e)}")
                companies_house_full_data = None

        # Run orchestrated verification
        verification_results = await orchestrator.process_educational_kyc(
            educational_request
        )

        # Convert orchestrator results to our existing format
        kyc_results = {}
        overall_risk_score = 0.0
        total_checks = 0
        risk_factors = []
        recommendations = []

        for result in verification_results:
            # Convert each verification result
            result_data = {
                "status": result.status,
                "risk_score": result.risk_score,
                "data_source": result.data_source,
                "confidence": 0.9,  # Default confidence for orchestrator results
                "details": result.details,
                "recommendations": result.recommendations or [],
                "timestamp": result.timestamp.isoformat(),
            }

            # For Companies House, merge with full API data if available
            if (
                result.check_type == "company_registration"
                and companies_house_full_data
            ):
                print(f"Merging detailed Companies House data...")
                # Use the full Companies House data instead of orchestrator mock data
                result_data = {
                    "status": companies_house_full_data.get("status", result.status),
                    "risk_score": companies_house_full_data.get(
                        "risk_score", result.risk_score
                    ),
                    "data_source": companies_house_full_data.get(
                        "data_source", result.data_source
                    ),
                    "confidence": companies_house_full_data.get("confidence", 0.9),
                    "details": companies_house_full_data.get("details", result.details),
                    "recommendations": companies_house_full_data.get(
                        "recommendations", result.recommendations or []
                    ),
                    "timestamp": companies_house_full_data.get(
                        "timestamp", result.timestamp.isoformat()
                    ),
                }
                print(
                    f"Companies House details: {len(str(result_data['details']))} characters"
                )

            kyc_results[result.check_type] = result_data

            # Accumulate risk scores
            overall_risk_score += result_data["risk_score"]
            total_checks += 1

            # Collect risk factors and recommendations
            if result_data["recommendations"]:
                recommendations.extend(result_data["recommendations"])

            if result_data["status"] in ["failed", "flagged"]:
                risk_factors.append(result.check_type)

        # Calculate average risk score
        if total_checks > 0:
            overall_risk_score = overall_risk_score / total_checks
        else:
            overall_risk_score = 0.5

        # Determine overall status and risk level based on orchestrator results
        risk_assessment = next(
            (
                r
                for r in verification_results
                if r.check_type == "educational_risk_assessment"
            ),
            None,
        )

        if risk_assessment:
            # Use orchestrator's risk assessment
            orchestrator_status = risk_assessment.status
            risk_level_mapping = {
                "approved": "low",
                "approved_with_monitoring": "medium",
                "enhanced_due_diligence_required": "high",
                "rejected": "critical",
            }

            overall_status = (
                "approved"
                if orchestrator_status == "approved"
                else (
                    "review_required"
                    if orchestrator_status
                    in ["approved_with_monitoring", "enhanced_due_diligence_required"]
                    else "rejected"
                )
            )
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
                "includes_educational_checks": True,
            },
            "recommendations": recommendations[:5],  # Limit to top 5 recommendations
            "timestamp": datetime.now().isoformat(),
        }

        # Update provider with orchestrated results
        provider.update(
            {
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
                    "recommendations_count": len(recommendations),
                },
            }
        )

        processing_queue[verification_id] = "completed"
        print(
            f"Orchestrated KYC completed: {verification_id} - Status: {overall_status}, Risk: {risk_level}, Checks: {total_checks}"
        )

    except Exception as e:
        print(f"Orchestrated KYC verification error: {verification_id} - {str(e)}")

        provider = next(
            (p for p in providers_db if p.get("verification_id") == verification_id),
            None,
        )
        if provider:
            provider.update(
                {
                    "status": "error",
                    "risk_level": "unknown",
                    "error_message": f"Orchestrator error: {str(e)}",
                    "processing_completed": datetime.now().isoformat(),
                }
            )

        processing_queue[verification_id] = "error"


@app.get("/companies-house/quick-check/{company_number}")
async def quick_companies_house_check(company_number: str):
    """Quick Companies House check endpoint (legacy support)"""
    api = EnhancedCompaniesHouseAPI()

    if not api.is_configured():
        return {
            "error": "Companies House API not configured",
            "exists": False,
            "active": False,
        }

    result = await api.quick_company_check(company_number)
    return result


@app.get("/postcode/validate/{postcode}")
async def validate_postcode_endpoint(postcode: str):
    """Quick postcode validation endpoint using postcodes.io"""
    try:
        # Clean postcode (remove spaces and convert to uppercase)
        clean_postcode = postcode.replace(" ", "").upper()

        # Call postcodes.io API
        url = f"https://api.postcodes.io/postcodes/{clean_postcode}"

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == 200:
                        result_data = data.get("result", {})

                        return {
                            "valid": True,
                            "postcode": result_data.get("postcode"),
                            "country": result_data.get("country"),
                            "region": result_data.get("region"),
                            "admin_district": result_data.get("admin_district"),
                            "admin_county": result_data.get("admin_county"),
                            "parliamentary_constituency": result_data.get(
                                "parliamentary_constituency"
                            ),
                            "coordinates": {
                                "latitude": result_data.get("latitude"),
                                "longitude": result_data.get("longitude"),
                            },
                        }
                    else:
                        return {
                            "valid": False,
                            "error": "Invalid postcode format",
                            "postcode": postcode,
                        }

                elif response.status == 404:
                    return {
                        "valid": False,
                        "error": "Postcode not found",
                        "postcode": postcode,
                    }

                else:
                    return {
                        "valid": False,
                        "error": f"API error: {response.status}",
                        "postcode": postcode,
                    }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation failed: {str(e)}",
            "postcode": postcode,
        }


@app.get("/verification/{verification_id}")
async def get_verification_status(verification_id: str):
    """Get verification status with orchestrator details"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return {"error": "Verification not found"}

    processing_status = processing_queue.get(verification_id, "unknown")

    return {
        "verification_id": verification_id,
        "status": provider["status"],
        "processing_status": processing_status,
        "revoked": provider.get("revoked", False),
        "revocation_reason": provider.get("revocation_reason"),
        "risk_level": provider.get("risk_level"),
        "organisation_name": provider["organisation_name"],
        "provider_type": provider.get("provider_type"),
        "urn": provider.get("urn"),
        "ukprn": provider.get("ukprn"),
        "jcq_centre_number": provider.get("jcq_centre_number"),
        "created_at": provider["created_at"],
        "kyc_results": provider.get("kyc_results", {}),
        "verification_summary": provider.get("verification_summary", {}),
        "orchestrator_used": True,
        "progress": {
            "started": processing_status
            in ["started", "in_progress", "completed", "error"],
            "in_progress": processing_status == "in_progress",
            "completed": processing_status == "completed",
            "error": processing_status == "error",
        },
    }


@app.get("/jcq/centre/{centre_number}")
async def lookup_jcq_centre(centre_number: str):
    """JCQ centre lookup (legacy endpoint)"""
    result = simulate_jcq_check(centre_number)
    return {
        "centre_number": centre_number,
        "verification": result,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/results/{verification_id}", response_class=HTMLResponse)
async def verification_results(verification_id: str, request: Request):
    """Results page with orchestrator details"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html", {"request": request, "message": "Verification not found"}
        )

    return templates.TemplateResponse(
        "results.html", {"request": request, "provider": provider}
    )


@app.get("/credential/{verification_id}", response_class=HTMLResponse)
async def verifiable_credential_page(verification_id: str, request: Request):
    """View the issued Verifiable Credential for an approved provider."""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id),
        None,
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Verification not found"},
        )

    if provider.get("status") != "approved":
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "Credential available only for approved applications",
            },
        )

    credential = create_verifiable_credential(provider)
    credential_json = json.dumps(credential)
    encoded = base64.urlsafe_b64encode(credential_json.encode()).decode()
    verify_url = f"{request.url_for('verify_via_link')}?credential={encoded}"
    qr_data = generate_qr_code(verify_url)

    return templates.TemplateResponse(
        "credential.html",
        {
            "request": request,
            "credential": credential,
            "provider": provider,
            "qr_data": qr_data,
        },
    )


@app.get("/credential/{verification_id}/download")
async def download_credential_pdf(verification_id: str, request: Request):
    """Provide the issued credential and QR code as a PDF download."""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id),
        None,
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Verification not found"},
        )

    if provider.get("status") != "approved":
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "Credential available only for approved applications",
            },
        )

    credential = create_verifiable_credential(provider)
    credential_json = json.dumps(credential)
    encoded = base64.urlsafe_b64encode(credential_json.encode()).decode()
    verify_url = f"{request.url_for('verify_via_link')}?credential={encoded}"
    qr_data = generate_qr_code(verify_url)

    pdf_bytes = generate_credential_pdf(credential, qr_data)

    filename = f"{provider.get('organisation_name','credential')}.pdf"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/revoke/{verification_id}")
async def revoke_credential(verification_id: str, request: Request):
    """Revoke an issued credential for a provider."""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id),
        None,
    )

    if provider:
        provider["revoked"] = True
        provider["revocation_reason"] = "Poor Credit"
        cred_id = provider.get("verification_id") or provider.get("id")
        if cred_id and not str(cred_id).startswith("urn:uuid:"):
            cred_id = f"urn:uuid:{cred_id}"
        from app.vc_verify import REVOKED_IDS

        REVOKED_IDS.add(cred_id)

    return RedirectResponse("/dashboard", status_code=302)


@app.get("/verify-credential", response_class=HTMLResponse)
async def verify_credential_form(request: Request):
    """Display the credential verification form."""
    return templates.TemplateResponse(
        "verify_credential.html",
        {"request": request, "result": None, "error": None},
    )


@app.post("/verify-credential", response_class=HTMLResponse)
async def verify_credential_submit(
    request: Request,
    credential_json: str = Form(...),
    expected_subject: str | None = Form(None),
):
    """Handle credential verification."""
    try:
        credential = json.loads(credential_json)
    except json.JSONDecodeError:
        return templates.TemplateResponse(
            "verify_credential.html",
            {
                "request": request,
                "error": "Invalid credential JSON",
                "result": None,
                "credential_json": credential_json,
                "expected_subject": expected_subject,
            },
        )

    result = verify_credential(credential, expected_subject)

    return templates.TemplateResponse(
        "verify_credential.html",
        {
            "request": request,
            "result": result,
            "credential_json": credential_json,
            "expected_subject": expected_subject,
            "error": None,
        },
    )


@app.get("/verify", response_class=HTMLResponse)
async def verify_via_link(request: Request, credential: str):
    """Verify a credential encoded in a URL parameter."""
    try:
        credential_json = base64.urlsafe_b64decode(credential.encode()).decode()
        cred = json.loads(credential_json)
    except Exception:
        return templates.TemplateResponse(
            "verify_credential.html",
            {
                "request": request,
                "error": "Invalid credential data",
                "result": None,
            },
        )

    result = verify_credential(cred)

    return templates.TemplateResponse(
        "verify_credential.html",
        {
            "request": request,
            "result": result,
            "credential_json": credential_json,
            "expected_subject": None,
            "error": None,
        },
    )


@app.get("/api/stats")
async def get_stats():
    """Dashboard statistics with orchestrator info"""
    api_status = check_api_configuration()

    return {
        "total": len(providers_db),
        "approved": len([p for p in providers_db if p["status"] == "approved"]),
        "under_review": len(
            [
                p
                for p in providers_db
                if p["status"] in ["review_required", "pending", "processing"]
            ]
        ),
        "high_risk": len([p for p in providers_db if p["risk_level"] == "high"]),
        "processing": len([p for p in providers_db if p["status"] == "processing"]),
        "centre_submissions": len(centre_submissions),
        "api_status": api_status,
        "verification_queue": len(processing_queue),
        "orchestrator_enabled": True,
        "version": "3.0-orchestrator",
    }


@app.get("/provider-status/{verification_id}", response_class=HTMLResponse)
async def provider_status_page(verification_id: str, request: Request):
    """Provider status tracking page"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Application not found for verification ID: {verification_id}",
            },
        )

    return templates.TemplateResponse(
        "provider_status.html", {"request": request, "provider": provider}
    )


@app.get("/provider-dashboard", response_class=HTMLResponse)
async def provider_dashboard_no_id(request: Request):
    """Dashboard page when no verification ID is provided"""
    return templates.TemplateResponse(
        "provider_dashboard.html",
        {"request": request, "provider": None},
    )


@app.get("/provider-dashboard/{verification_id}", response_class=HTMLResponse)
async def provider_dashboard(verification_id: str, request: Request):
    """Dashboard view for a single provider application"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Application not found for verification ID: {verification_id}",
            },
        )

    return templates.TemplateResponse(
        "provider_dashboard.html",
        {"request": request, "provider": provider},
    )


@app.post("/provider-status/{verification_id}/upload")
async def upload_documents(verification_id: str, request: Request):
    """Handle document uploads for providers"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return {"error": "Application not found"}

    try:
        form_data = await request.form()
        document_type = form_data.get("document_type")
        document_description = form_data.get("document_description")
        uploaded_files = form_data.getlist("document")

        # Initialize uploaded_documents if not exists
        if "uploaded_documents" not in provider:
            provider["uploaded_documents"] = []

        # Process each uploaded file
        for file in uploaded_files:
            if hasattr(file, "filename") and file.filename:
                # In a real implementation, you would save the file to storage
                # For now, we'll just store metadata
                document_info = {
                    "name": file.filename,
                    "type": document_type or "Other",
                    "description": document_description or "",
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "size": getattr(file, "size", 0),
                    "verification_id": verification_id,
                }
                provider["uploaded_documents"].append(document_info)

        # Update provider status if needed
        if (
            provider.get("status") == "review_required"
            and len(provider["uploaded_documents"]) > 0
        ):
            provider["status"] = "processing"
            provider["document_upload_timestamp"] = datetime.now().isoformat()

        return {
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_files)} document(s)",
            "uploaded_count": len(uploaded_files),
        }

    except Exception as e:
        return {"error": f"Upload failed: {str(e)}"}


@app.get("/api/provider-status/{verification_id}")
async def get_provider_status_api(verification_id: str):
    """API endpoint for provider status (for AJAX polling)"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return {"error": "Application not found"}

    return {
        "verification_id": verification_id,
        "status": provider["status"],
        "risk_level": provider.get("risk_level", "unknown"),
        "organisation_name": provider["organisation_name"],
        "created_at": provider["created_at"],
        "processing_completed": provider.get("processing_completed"),
        "uploaded_documents_count": len(provider.get("uploaded_documents", [])),
        "last_updated": datetime.now().isoformat(),
    }


@app.post("/api/onboard")
async def api_onboard_provider(request: Request, data: ProviderAPIRequest):
    """RESTful API endpoint to run the onboarding KYC checks."""

    verification_id = str(uuid.uuid4())

    provider_data = data.dict()
    provider_data["verification_id"] = verification_id

    new_provider = {
        "id": len(providers_db) + 1,
        "verification_id": verification_id,
        "organisation_name": provider_data["organisation_name"],
        "trading_name": provider_data.get("trading_name"),
        "provider_type": provider_data.get("provider_type", "Training Provider"),
        "company_number": provider_data.get("company_number"),
        "urn": provider_data.get("urn"),
        "ukprn": provider_data.get("ukprn"),
        "jcq_centre_number": provider_data.get("jcq_centre_number"),
        "postcode": provider_data["postcode"],
        "contact_email": provider_data.get("contact_email"),
        "status": "processing",
        "risk_level": "unknown",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kyc_results": {},
        "processing_started": datetime.now().isoformat(),
    }

    providers_db.append(new_provider)
    processing_queue[verification_id] = "started"

    # Run the orchestration synchronously
    await process_orchestrated_kyc(verification_id, provider_data)

    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id),
        None,
    )

    if not provider:
        return JSONResponse(status_code=500, content={"error": "Processing failed"})

    credential_url = str(
        request.url_for("verifiable_credential_page", verification_id=verification_id)
    )

    response = {
        "verification_id": verification_id,
        "status": provider.get("status"),
        "risk_score": provider.get("overall_risk_score"),
        "credential_url": credential_url,
    }

    if provider.get("status") == "approved":
        try:
            response["credential"] = create_verifiable_credential(provider)
        except Exception as exc:
            response["credential_error"] = str(exc)

    return response


@app.get("/ukprn/validate/{ukprn}")
async def validate_ukprn_endpoint(ukprn: str):
    """Quick UKPRN validation endpoint using UKRLP"""
    try:
        # Basic format validation first
        if not ukprn.isdigit() or len(ukprn) != 8 or not ukprn.startswith("10"):
            return {
                "valid": False,
                "ukprn": ukprn,
                "error": "UKPRN must be 8 digits starting with 10",
            }

        # Import orchestrator to use UKPRN validation
        from app.services.combined_orchestrator import (
            CombinedEducationalKYCOrchestrator,
        )

        orchestrator = CombinedEducationalKYCOrchestrator()

        # Check if scraping dependencies are available
        if not orchestrator._check_scraping_dependencies():
            return {
                "valid": False,
                "ukprn": ukprn,
                "error": "UKPRN validation temporarily unavailable - dependencies missing",
            }

        # Get real UKRLP data
        ukrlp_data = await orchestrator._get_real_ukrlp_data(ukprn)

        if ukrlp_data and not ukrlp_data.get("error"):
            return {
                "valid": True,
                "ukprn": ukprn,
                "provider_name": ukrlp_data.get("provider_name", "Unknown"),
                "verification_status": ukrlp_data.get("verification_status", "Unknown"),
                "provider_status": ukrlp_data.get("provider_status", "Unknown"),
                "message": "UKPRN found in UKRLP database",
            }
        else:
            return {
                "valid": False,
                "ukprn": ukprn,
                "error": ukrlp_data.get("error", "UKPRN not found in UKRLP database"),
            }

    except ImportError as e:
        return {
            "valid": False,
            "ukprn": ukprn,
            "error": "UKPRN validation temporarily unavailable",
        }
    except Exception as e:
        return {"valid": False, "ukprn": ukprn, "error": f"Validation failed: {str(e)}"}



@app.get("/ofqual/search", response_class=HTMLResponse)
async def ofqual_search(request: Request, Title: Optional[str] = None):
    """Search the Ofqual Register for organisations and qualifications.
    The query is limited to Pearson Education qualifications that are
    available to learners.
    """
    client = OfqualQualificationsClient()
    qualifications: List[Dict] = []
    if Title:
            qualifications = await client.search(course=Title)
    return templates.TemplateResponse(
        "ofqual_search.html",
        {
            "request": request,
            "Title": Title,
            "qualifications": qualifications,
        },
    )


@app.get("/urn/validate/{urn}")
async def validate_urn_endpoint(urn: str):
    """Quick URN validation endpoint using Ofsted search"""
    try:
        # Basic format validation first
        if not urn.isdigit() or len(urn) < 6 or len(urn) > 7:
            return {"valid": False, "urn": urn, "error": "URN must be 6-7 digits"}

        # Import orchestrator to use URN validation
        from app.services.combined_orchestrator import (
            CombinedEducationalKYCOrchestrator,
        )

        orchestrator = CombinedEducationalKYCOrchestrator()

        # Check if scraping dependencies are available
        if not orchestrator._check_scraping_dependencies():
            return {
                "valid": False,
                "urn": urn,
                "error": "URN validation temporarily unavailable - dependencies missing",
            }

        # Use the resolve_ofsted_url method to check if URN exists
        resolved_url = await orchestrator._resolve_ofsted_url(urn)

        if resolved_url:
            return {
                "valid": True,
                "urn": urn,
                "message": "URN found in Ofsted database",
                "ofsted_url": resolved_url,
            }
        else:
            return {
                "valid": False,
                "urn": urn,
                "error": "URN not found in Ofsted database",
            }

    except ImportError as e:
        return {
            "valid": False,
            "urn": urn,
            "error": "URN validation temporarily unavailable",
        }
    except Exception as e:
        return {"valid": False, "urn": urn, "error": f"Validation failed: {str(e)}"}


@app.get("/debug/provider/{verification_id}")
async def debug_provider_data(verification_id: str):
    """Debug endpoint to see provider data structure"""
    provider = next(
        (p for p in providers_db if p.get("verification_id") == verification_id), None
    )

    if not provider:
        return {"error": "Provider not found"}

    # Return the full provider data for inspection
    return {
        "provider_id": provider.get("id"),
        "verification_id": verification_id,
        "status": provider.get("status"),
        "kyc_results_keys": list(provider.get("kyc_results", {}).keys()),
        "companies_house_data": provider.get("kyc_results", {}).get(
            "company_registration"
        ),
        "full_kyc_results": provider.get("kyc_results", {}),
        "data_structure": {
            key: {
                "status": (
                    value.get("status") if isinstance(value, dict) else "not_dict"
                ),
                "details_keys": (
                    list(value.get("details", {}).keys())
                    if isinstance(value, dict) and value.get("details")
                    else []
                ),
                "has_recommendations": (
                    bool(value.get("recommendations"))
                    if isinstance(value, dict)
                    else False
                ),
            }
            for key, value in provider.get("kyc_results", {}).items()
        },
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
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/mcp/health")
async def mcp_health():
    """Proxy health check using the MCP wrapper."""
    if not mcp_wrapper:
        return JSONResponse(status_code=503, content={"error": "MCP wrapper not initialised"})

    # Query the underlying `/health` endpoint via the MCP wrapper
    doc = await mcp_wrapper.health()

    if doc.context and doc.context.get("error"):
        return JSONResponse(status_code=503, content={"error": doc.context["error"]})


    return {
        "content": doc.content,
        "source_url": doc.source_url,
        "media_type": doc.media_type,
        "retrieved_at": doc.retrieved_at.isoformat(),
        "context": doc.context,
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
            "timestamp": datetime.now().isoformat(),
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
                "qualifications": ["GCSE", "A Level"],
            },
            "timestamp": datetime.now().isoformat(),
        }
    else:
        return {
            "status": "flagged",
            "risk_score": 0.4,
            "data_source": "JCQ Simulation",
            "details": {
                "centre_number": centre_number,
                "message": "Centre not found in simulation database",
            },
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
