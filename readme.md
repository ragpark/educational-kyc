# Educational Provider KYC System

A comprehensive Know Your Customer (KYC) verification system specifically designed for UK educational and training providers.

## Features

🎓 **Educational Provider Verification**
- Ofqual qualification validation
- Awarding organisation search via Ofqual API
- Ofsted inspection ratings
- ESFA funding status verification
- UKPRN validation
- Companies House integration
- Model Context Protocol (MCP) wrapper for AI integrations
- REST onboarding API with MCP wrapper support

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
python -c "from app.database import init_db; init_db()"

# Educational Provider KYC System

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

### Example: Awarding Organisation Search

Use the built-in client to retrieve qualifications for a given subject
and course.

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
=======
Once the server is running you can also access the wrapper via HTTP.
Calling `/mcp/health` returns the underlying `/health` response wrapped in the MCP metadata:


```

The JSON payload contains the raw content and context information returned by
`KYCContextSource`.


Alternatively you can call the FastAPI endpoint directly:

```
GET /ofqual/search?Title=history%20gcse
```

### Example: Ofqual Register Search

You can search qualifications by course and location using `OfqualQualificationsClient`:

```python
import asyncio
from app.services.ofqual_qualifications import OfqualQualificationsClient


async def demo():
    client = OfqualQualificationsClient()
    qualifications = await client.search(course="maths", location="london")
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

    quals = await source.ofqual_search(course="maths")
    print(quals.content)

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

cvu9o6-codex/update-readme-with-verification-process
## Verifiable Credentials

When an application is approved the service can issue a W3C compliant
Verifiable Credential for the organisation.  Credentials are created using the
`create_verifiable_credential` function in `app/vc_issue.py` and can be viewed
at `/credential/<verification_id>` in a running instance. The credentials are
issued by **certify3.io** and use a UUID based identifier for the subject.

### Issuing a Credential
=======
## Verifiable Credential Workflow

The project provides a simple `create_verifiable_credential` function in `app.vc_issue`. After a provider passes all KYC checks and the `status` field is set to `"approved"`, issue a credential like so:
main

```python
from app.vc_issue import create_verifiable_credential

cvu9o6-codex/update-readme-with-verification-process
provider = {
    "id": 2,
    "verification_id": "11111111-1111-1111-1111-111111111111",
    "organisation_name": "Sample Training Ltd",
    "status": "approved",
}

vc = create_verifiable_credential(provider)
print(vc)
```

### Verifying a Credential

A third party can verify the JSON-LD signature in the `proof` section using any
VC verification library (for example `jsonld-signatures` or `did-jwt-vc`).  A
successful verification confirms the credential was issued by certify3.io and
has not been modified, providing proof of completion.  For example in Python:

```python
from py_vcreds import verify_credential

is_valid = verify_credential(vc)
print("Valid:" if is_valid else "Invalid")
```
credential = create_verifiable_credential(provider)
```

The returned JSON document includes a `proof` object with an Ed25519 signature. This signature allows any verifier to confirm the credential was issued by the KYC service.

### Tools for Issuing and Verifying

* **Issuing** – The built-in `create_verifiable_credential` helper signs credentials for you. For more advanced flows you can integrate libraries such as `didkit` or Hyperledger tools.
* **Verification** – Third parties can validate a credential using standard VC libraries (e.g. [`jsonld-signatures`](https://github.com/digitalbazaar/jsonld-signatures`) or Hyperledger Aries). Verification consists of checking the `proof` signature, confirming the issuer URL, and validating the `credentialSubject` details.

A successfully verified credential can be relied upon as proof that the organisation has completed the KYC process.

### QR Code Verification

Each issued credential page now displays a QR code. Scanning the code opens the
`/verify` endpoint with the credential embedded in the URL. The page
automatically validates the credential and shows whether it is valid or not.

