# Educational Provider KYC System

A comprehensive Know Your Customer (KYC) verification platform specifically designed for UK educational and training providers. This system helps educational organisations obtain official verification and credentials by automatically checking their legitimacy against multiple UK regulatory databases and awarding organisations.

## What is Educational KYC?

The Educational KYC system streamlines the verification process for educational providers, enabling them to:
- Obtain official verification and digital credentials
- Match their capabilities with suitable course offerings
- Assess partnership maturity with Awarding Organisations
- Maintain compliance with UK educational regulations

## Core Features

### 🎓 Educational Provider Verification
- **Education qualification searches** via Ofqual API
- **Ofsted inspection ratings** verification
- **UKPRN validation** for registered providers
- **Companies House integration** for organisational verification
- **Model Context Protocol (MCP) wrapper** for AI integrations
- **REST onboarding API** with MCP wrapper support and integration with downstream services

### 📚 Training Course Recommendations System

#### How It Works
Our recommendation engine uses **content-based filtering** to match centres with courses based on objective resource compatibility. Unlike collaborative filtering systems that learn from user preferences, this approach focuses on answering: *"Can this centre deliver this course effectively?"*

**Technical Implementation:**
- PostgreSQL & SQLAlchemy models for centres, labs, staff skills and courses
- ETL pipeline with scikit-learn producing centre and course feature matrices
- FastAPI service returning recommended courses for a centre
- React/Tailwind dashboard visualising similarity scores and capability radar charts

**The Matching Process:**
1. **Centre Profile Analysis** - Examines available laboratories, staff qualifications, technical expertise
2. **Course Requirements Mapping** - Maps courses by required facilities, skills, equipment needs
3. **Smart Matching Algorithm** - Calculates compatibility using cosine similarity between feature vectors
4. **Results Visualisation** - Interactive radar charts showing capability alignment

#### Partnership Maturity Tiers
Each recommendation includes a partnership tier reflecting your relationship with the Awarding Organisation:
- **Tier 1: New Partner** - Initial engagement, basic verification complete
- **Tier 2: Developing Partner** - Active delivery, building track record
- **Tier 3: Established Partner** - Proven delivery success, strong relationship
- **Tier 4: Strategic Partner** - Long-term collaboration, premium status

### 📊 Risk Assessment
- **Automated risk scoring** considering multiple factors
- **Educational-specific compliance checks**
- **Real-time verification results**
- Lower risk scores indicate higher trustworthiness and faster approval

### 🔒 Security & Compliance
- UK educational regulations compliance
- GDPR data protection
- Comprehensive audit trail maintenance
- Digital credential issuance upon approval

### ⚙️ Additional Technical Capabilities
- **Orchestrated KYC checks** leverage a combined workflow that calls real APIs like Companies House, UKRLP and sanction screening when configured, falling back to internal logic otherwise
- **LTI launch endpoint** (`/lti/launch`) enables integration with Learning Tools Interoperability platforms
- **AI document and image analysis** assesses safeguarding policies and classroom images using OpenAI models with heuristic fallbacks
- **Verifiable credential toolchain** issues W3C credentials, generates QR codes and PDFs, and validates signatures and revocation status
- **Model Context Protocol API** provides programmatic health checks, provider onboarding, status queries and Ofqual search

## Information Architecture

The application features a global navigation structure:

- **Centre Approval** – Dashboard for centre verification and approval status
- **Qualification Approvals** – Track and manage qualification approval applications
- **Qualification Selection** – Browse and select qualifications suitable for your centre
- **Evidence** – Submit and manage evidence documents for applications
- **Verify** – Document verification and validation status
- **About** – Account management and system information

## Application Process

### Requirements for Centre Applications
**Essential Information:**
- Organisation legal name and trading name
- Company registration number
- UKPRN (if applicable)
- Main contact details
- Registered and trading addresses

**Supporting Documentation:**
- Certificate of incorporation
- Proof of address
- Insurance certificates
- Safeguarding policy
- Health & safety policy
- Equality & diversity policy

**Delivery Site Information:**
- Complete address for each location
- Site contact details
- Available facilities and equipment
- Laboratory specifications
- Accessibility information

### Requirements for Qualification Applications
- Qualification title and level
- Awarding organisation details
- Proposed start date
- Delivery method and duration
- Assessment strategy
- Internal verification procedures
- Staff CVs and qualifications
- Resources and equipment list

## Technical Documentation

### Quick Start

This application is deployed on Railway.app with PostgreSQL and Redis.

#### Local Development
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload

# Create tables locally
python -c "from backend.database import init_db; init_db()"

# Populate with example centres and courses before running ETL/recommendations
python -m backend.seed_data
```

### Deploy on Railway

#### Quick Deploy
1. Click the "Deploy on Railway" button
2. Connect your GitHub account
3. Railway will automatically deploy the app
4. Your app will be live in 2-3 minutes!

### Architecture Overview

The Railway deployment provisions a PostgreSQL service for storing user accounts and provider applications. The FastAPI application connects to this database using SQLAlchemy. Dataclasses in `app/models.py` define the schema for `user_accounts` and `applications` tables, which support full CRUD operations.

### Course Recommendation Engine Setup

Before generating feature matrices or running the recommendation API, seed the database:

```bash
python -m backend.seed_data

# Rebuild feature matrices via the main app
curl -X POST http://localhost:8000/build-recommendations

# Start the recommendation API (included in main app)
uvicorn app.main:app --reload

# Open the demo dashboard (served statically)
python -m http.server --directory frontend 8001
```

Navigate to `http://localhost:8001` and enter a centre ID to view recommended courses. Results can be filtered by delivery mode and minimum similarity score, with radar charts showing how centre capabilities compare to course requirements.

### Technical Details: How Recommendations Work

The recommendation engine models each centre and course using features drawn from the relational database:

- **Centres** link to available labs and staff skills via `centre_labs` and `centre_staff_skills` tables
- **Courses** list required labs and prerequisite skills in `courses` and `course_tags`
- **ETL Process** vectorises attributes with scikit-learn's `DictVectorizer`, `OneHotEncoder` and `StandardScaler`
- **Similarity Computation** uses cosine similarity between centre and course feature vectors
- **Filtering** removes unsuitable options based on required labs and online content restrictions
- **Results** are sorted by similarity and annotated with risk score and partner tier

### API Examples

#### Qualification Search
```python
import asyncio
from app.services.ofqual_qualifications import OfqualQualificationsClient

async def demo():
    client = OfqualQualificationsClient()
    results = await client.search(course="history gcse")
    for qual in results:
        print(qual.get("title", qual))

asyncio.run(demo())
```

#### Ofqual Register Search
```python
import asyncio
from app.services.ofqual_awarding_orgs import OfqualAOSearchClient

async def demo():
    client = OfqualAOSearchClient()
    organisations = await client.search(course="maths", location="london")
    qualifications = await client.search_qualifications(course="maths", location="london")
    print("Organisations:", len(organisations))
    print("Qualifications:", len(qualifications))

asyncio.run(demo())
```

Or via endpoint:
```
GET /ofqual/search?course=maths&location=london
```

### MCP Wrapper Integration

The `KYCContextSource` class provides a Model Context Protocol (MCP) interface:

```python
import asyncio
import os
from app.mcp_wrapper import KYCContextSource

async def demo():
    default_base = f"http://localhost:{os.getenv('PORT', '8000')}"
    source = KYCContextSource(base_url=os.getenv("MCP_BASE_URL", default_base))
    
    health = await source.health()
    print("Health status:", health.content)
    
    orgs = await source.search_awarding_orgs(subject="maths")
    print(orgs.content)
    
    onboarding = await source.onboard_provider({
        "organisation_name": "Demo School",
        "urn": "123456",
        "postcode": "AB1 2CD",
    })
    print(onboarding.content)

asyncio.run(demo())
```

### REST API Onboarding

Submit provider details via JSON to `/api/onboard`:

```json
{
  "organisation_name": "Example College",
  "urn": "123456",
  "postcode": "AB1 2CD",
  "company_number": "12345678",
  "provider_type": "Training Provider"
}
```

Response includes verification ID, risk score, and credential:
```json
{
  "verification_id": "11111111-2222-3333-4444-555555555555",
  "status": "approved",
  "risk_score": 0.12,
  "credential_url": "https://example.com/credential/...",
  "credential": { "@context": "https://www.w3.org/2018/credentials/v1" }
}
```

For applications still processing, poll `/api/provider-status/<verification_id>` until status changes.

### Running Tests

```bash
pip install -r requirements.txt
pip install pytest
pytest
```

## Tips for Successful Applications

### 📋 Preparation
- Gather all documents before starting
- Ensure information is current and accurate
- Verify company registration details
- Check policies are up to date

### 📄 Documentation
- Upload clear, legible copies
- Use descriptive file names
- Keep file sizes reasonable
- Use standard formats (PDF, JPG, PNG)

### 💬 Communication
- Respond promptly to messages
- Provide complete information
- Use Messages section for queries
- Keep contact details updated

### Digital Credential System & QR Code Verification
How the Credential System Works
Upon successful centre application approval, organisations receive a digital credential with a unique QR code. This credential serves as a gatekeeper for the qualification approval process:
🎫 Digital Credential Features

Unique QR Code - Required for all qualification applications
Verification Gateway - Fast-tracks approved centres through qualification approvals
Performance Tracking - Links to your centre's delivery track record
Revocable Status - Can be suspended or revoked for compliance issues

🔒 Safeguarding the Qualification Process
The QR code requirement ensures that:

Only verified centres can apply for qualification approvals
Fast-track processing for centres with good standing
Protection against bad actors - Centres with poor track records cannot proceed
Quality assurance - Maintains standards across the education sector

⚠️ Credential Revocation
QR codes may be revoked for:

Poor delivery performance or student outcomes
Compliance violations or regulatory breaches
Failed quality audits or inspections
Unresolved complaints or safeguarding issues
Failure to maintain required documentation or insurance

Important: Once revoked, a centre must undergo a full re-verification process and address all identified issues before a new credential can be issued.

## What Happens After Approval?

Upon successful verification, you receive:
- Digital verification credential
- Unique verification ID
- Access to course recommendations
- Partnership tier assignment
- Ongoing compliance monitoring

Your verification status remains valid as long as your organisation maintains compliance with UK educational regulations and your information remains current and accurate.

## Support

- Use the "Help & Support" section for FAQs
- Contact support through the Messages system
- Provide your verification ID for faster assistance

---

This system ensures compliance with UK educational regulations, GDPR data protection requirements, and maintains comprehensive audit trails for all verification activities.
