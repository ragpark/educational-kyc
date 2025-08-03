import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.services.ofqual_qualifications import OfqualQualificationsClient


def test_search_filters_awarding_org_and_availability():
    client = OfqualQualificationsClient()

    session = AsyncMock()
    session.__aenter__.return_value = session
    response = AsyncMock()
    response.status = 200
    response.__aenter__.return_value = response
    response.json = AsyncMock(return_value={"results": []})
    session.get = Mock(return_value=response)

    with patch("aiohttp.ClientSession", return_value=session):
        asyncio.run(client.search(course="maths"))
        session.get.assert_called_with(
            f"{client.base_url}/api/Qualifications",
            params={
                "search": "maths",
                "page": 1,
                "limit": 25,
                "awardingOrganisations": "Pearson Education",
                "availability": "Available to learners",
            },
            headers={},
        )
