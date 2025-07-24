import aiohttp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class OfqualAOSearchClient:
    """Client for searching Ofqual awarding organisations by course or subject."""

    BASE_URL = "https://api.ofqual.gov.uk/api/v1/awarding-organisations"

    async def search(self, *, subject: Optional[str] = None, course: Optional[str] = None) -> List[Dict]:
        """Return a list of awarding organisations matching the query."""
        params = {}
        if subject:
            params["subject"] = subject
        if course:
            params["course"] = course
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # API may return list directly or under "results" key
                        if isinstance(data, dict):
                            return data.get("results", data.get("items", []))
                        return data
                    logger.error("Ofqual API error %s", resp.status)
        except Exception as e:
            logger.error("Ofqual API request failed: %s", e)
        return []
