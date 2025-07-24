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
