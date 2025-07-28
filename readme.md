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

## MCP Wrapper Usage

The application exposes a lightweight wrapper that speaks the
**Model Context Protocol (MCP)**. This wrapper lets downstream AI agents
retrieve context from the service in a standardised document format.

```python
from app.mcp_wrapper import KYCContextSource

source = KYCContextSource(base_url="https://your-kyc-service.com")
health_doc = await source.health()
print(health_doc.content)
```

Each method on `KYCContextSource` returns an `MCPDocument` which contains the
raw content, metadata about when it was retrieved, and the originating URL.
You can use this wrapper to fetch awarding organisation data or verification
statuses without dealing with HTTP directly.
