import aiohttp
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class OfqualQualificationsClient:
    """Client for querying Ofqual qualifications.

    The client always filters results to the Pearson Education awarding
    organisation and qualifications that are available to learners.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("APIMgmgt_URL", "https://register-api.ofqual.gov.uk")).rstrip("/")
        self.api_key = api_key or os.getenv("APISubKey")

    async def search(
        self,
        *,
        course: Optional[str] = None,
        location: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> List[Dict]:
        """Return a list of qualifications matching the query."""
        search_terms = " ".join(filter(None, [course, location]))
        params = {
            "search": search_terms,
            "page": page,
            "limit": limit,
            "Organisations": "Pearson Education",
            "availability": "Available to learners",
        }

        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/Qualifications", params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            return data.get("results", data.get("items", []))
                        return data
                    logger.error("Ofqual API error %s", resp.status)
        except Exception as e:
            logger.error("Ofqual API request failed: %s", e)
        return []
