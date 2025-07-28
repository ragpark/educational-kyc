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

# Educational Provider KYC System

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

## Quick Deploy

1. Click the "Deploy on Railway" button above
2. Connect your GitHub account
3. Railway will automatically deploy the app
4. Your app will be live in 2-3 minutes!

### Example: Awarding Organisation Search

Use the built-in client to retrieve awarding organisations for a given subject
and course.

```python
import asyncio
from app.services.ofqual_awarding_orgs import OfqualAOSearchClient


async def demo():
    client = OfqualAOSearchClient()
    results = await client.search(subject="history", course="gcse")
    for org in results:
        print(org.get("name", org))


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
GET /ofqual/awarding-organisations?subject=history&course=gcse
```

### Example: Ofqual Register Search

You can search both organisations and qualifications by course and location using `OfqualAOSearchClient`:

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

asyncio.run(demo())
```


### Running Tests

To run the automated tests locally, install the dependencies and execute `pytest`:

```bash
pip install -r requirements.txt
pip install pytest
pytest
```

## Verifiable Credential Workflow

The project provides a simple `create_verifiable_credential` function in `app.vc_issue`. After a provider passes all KYC checks and the `status` field is set to `"approved"`, issue a credential like so:

```python
from app.vc_issue import create_verifiable_credential

credential = create_verifiable_credential(provider)
```

The returned JSON document includes a `proof` object with an Ed25519 signature. This signature allows any verifier to confirm the credential was issued by the KYC service.

### Tools for Issuing and Verifying

* **Issuing** – The built-in `create_verifiable_credential` helper signs credentials for you. For more advanced flows you can integrate libraries such as `didkit` or Hyperledger tools.
* **Verification** – Third parties can validate a credential using standard VC libraries (e.g. [`jsonld-signatures`](https://github.com/digitalbazaar/jsonld-signatures`) or Hyperledger Aries). Verification consists of checking the `proof` signature, confirming the issuer URL, and validating the `credentialSubject` details.

A successfully verified credential can be relied upon as proof that the organisation has completed the KYC process.

