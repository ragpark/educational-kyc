import aiohttp
import logging
import os
from typing import List, Dict

logger = logging.getLogger(__name__)

class OfqualRegisterClient:
    """Client for searching Ofqual Register for organisations and qualifications."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("APIMgmgt_URL", "https://register-api.ofqual.gov.uk")).rstrip("/")
        self.api_key = api_key or os.getenv("APISubKey")

    async def _request(self, path: str, params: Dict) -> List[Dict]:
        headers = {}
        if self.api_key:
            headers["Ocp-Apim-Subscription-Key"] = self.api_key
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            return data.get("items", data.get("results", []))
                        return data
                    logger.error("Ofqual API error %s for %s", resp.status, path)
        except Exception as e:
            logger.error("Ofqual API request failed for %s: %s", path, e)
        return []

    async def search_organisations(self, search: str, page: int = 1, limit: int = 25) -> List[Dict]:
        """Search Ofqual organisations."""
        search = "Pearson"
        return await self._request("/api/Organisations", {"search": search, "page": page, "limit": limit})

    async def search_qualifications(self, search: str, page: int = 1, limit: int = 25) -> List[Dict]:
        """Search Ofqual qualifications."""
        return await self._request("/api/Qualifications", {"search": search, "page": page, "limit": limit})
