# Educational Provider KYC System

A comprehensive Know Your Customer (KYC) verification system specifically designed for UK educational and training providers.

## Features

🎓 **Educational Provider Verification**
- Pearson Education qualification search via Ofqual API
- Ofsted inspection ratings
- ESFA funding status verification
- UKPRN validation
- Companies House integration
- Model Context Protocol (MCP) wrapper for AI integrations
- REST onboarding API with MCP wrapper support

📚 **Training Course Recommendations**
- PostgreSQL & SQLAlchemy models for centres, labs, staff skills and courses
- ETL pipeline with scikit-learn producing centre and course feature matrices
- FastAPI service returning recommended courses for a centre
- React/Tailwind dashboard visualising similarity scores and capability radar charts

📊 **Risk Assessment**
- Automated risk scoring
- Educational-specific compliance checks
- Real-time verification results

🔒 **Security & Compliance**
- UK educational regulations compliance
- Data protection (GDPR)
- Audit trail maintenance

## Information Architecture

The app now includes a global navigation bar linking to:

- **Home** – dashboard overview
- **Applications** – track submitted and in‑progress applications
- **My Organisation** – manage organisational details and delivery sites
- **Messages** – application updates and AO requests
- **Documents** – upload and reuse common documents
- **Help & Support** – FAQs and guidance
- **User Profile** – account management and settings

## Quick Start

This application is deployed on Railway.app with PostgreSQL and Redis.

### Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload

# create tables locally
python -c "from backend.database import init_db; init_db()"

# populate with example centres and courses before running ETL/recommendations
python -m backend.seed_data

```
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

## Quick Deploy

1. Click the "Deploy on Railway" button above
2. Connect your GitHub account
3. Railway will automatically deploy the app
4. Your app will be live in 2-3 minutes!

## Architecture Overview

The Railway deployment now provisions a **PostgreSQL** service for storing user
accounts and provider applications. The FastAPI application connects to this
database using SQLAlchemy. Dataclasses in `app/models.py` define the schema for
`user_accounts` and `applications` tables, which support full CRUD operations.

## Course Recommendation Engine

The repository now contains a small training course recommendation prototype.

Before generating feature matrices or running the recommendation API, seed the
database with sample data:

```bash
python -m backend.seed_data
```

```bash
# rebuild feature matrices via the main app
curl -X POST http://localhost:8000/build-recommendations

# start the recommendation API (included in main app)
uvicorn app.main:app --reload

# open the demo dashboard (served statically)
# e.g. using a simple file server
python -m http.server --directory frontend 8001
```

Navigate to `http://localhost:8001` and enter a centre ID to view recommended
courses. Results can be filtered by delivery mode and minimum similarity score,
with radar charts showing how centre capabilities compare to course
requirements.

The centre submission form invokes `POST /build-recommendations` to generate
the latest feature matrices before requesting recommendations.

### Example: Qualification Search

Use the built-in client to retrieve Pearson Education qualifications by title.
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

### MCP Wrapper Endpoint


Once the server is running you can access the wrapper via HTTP. If deploying on Railway make sure the `MCP_BASE_URL` environment variable matches your service URL; otherwise the wrapper defaults to `http://localhost:$PORT`.
Calling `/mcp/health` returns the underlying `/health` response wrapped in the MCP metadata:

```bash
curl http://localhost:$PORT/mcp/health


```

The JSON payload contains the raw content and context information returned by
`KYCContextSource`.


Alternatively you can call the FastAPI endpoint directly:

```
GET /ofqual/search?Title=history%20gcse
```

### Example: Ofqual Register Search


You can search Pearson Education qualifications by title using `OfqualQualificationsClient`:

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

Or via the new endpoint:

```
GET /ofqual/search?course=maths&location=london
```

### Using the MCP Wrapper

The `KYCContextSource` class provides a simple Model Context Protocol (MCP)
interface to the application's endpoints. Each call returns an `MCPDocument`
containing the raw response and metadata.

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

    onboarding = await source.onboard_provider(
        {
            "organisation_name": "Demo School",
            "urn": "123456",
            "postcode": "AB1 2CD",
        }
    )
    print(onboarding.content)

asyncio.run(demo())
```

`onboard_provider` posts the given details to `/api/onboard` and returns the
wrapped response, allowing automated client integrations.

## REST API Onboarding

You can submit provider details directly via JSON using the `/api/onboard` endpoint. The payload must conform to the `ProviderAPIRequest` schema used by the application.

```json
{
  "organisation_name": "Example College",
  "urn": "123456",
  "postcode": "AB1 2CD",
  "company_number": "12345678",
  "provider_type": "Training Provider"
}
```

The endpoint runs the full KYC orchestration and returns the verification ID, risk score, and a link to the credential page. If the application is approved, the JSON‑LD credential is included in the response.

```json
{
  "verification_id": "11111111-2222-3333-4444-555555555555",
  "status": "approved",
  "risk_score": 0.12,
  "credential_url": "https://example.com/credential/11111111-2222-3333-4444-555555555555",
  "credential": { "@context": "https://www.w3.org/2018/credentials/v1" }
}
```

For applications still processing, poll `/api/provider-status/<verification_id>` until the status changes from `processing`.


### Running Tests

To run the automated tests locally, install the dependencies and execute `pytest`:

```bash
pip install -r requirements.txt
pip install pytest
pytest
```
