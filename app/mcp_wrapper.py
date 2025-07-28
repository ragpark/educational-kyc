"""Model Context Protocol wrapper for the Educational KYC service."""

from __future__ import annotations

import aiohttp
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MCPDocument:
    """Document representation for Model Context Protocol."""

    content: str
    source_url: str
    media_type: str = "application/json"
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] | None = None


class KYCContextSource:
    """Wrapper for querying the Educational KYC site via HTTP."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def _get(self, path: str) -> MCPDocument:
        url = f"{self.base_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                return MCPDocument(
                    content=text,
                    source_url=url,
                    media_type=resp.headers.get("Content-Type", "text/plain"),
                    context={"status": resp.status},
                )

    async def health(self) -> MCPDocument:
        """Return the service health information."""
        return await self._get("/health")

    async def verification_status(self, verification_id: str) -> MCPDocument:
        """Fetch verification status for a given ID."""
        return await self._get(f"/verification/{verification_id}")

    async def search_awarding_orgs(
        self, *, subject: Optional[str] = None, course: Optional[str] = None
    ) -> MCPDocument:
        params = []
        if subject:
            params.append(f"subject={subject}")
        if course:
            params.append(f"course={course}")
        query = "&".join(params)
        path = f"/ofqual/awarding-organisations?{query}" if query else "/ofqual/awarding-organisations"
        return await self._get(path)

    async def ofqual_search(
        self, *, course: Optional[str] = None, location: Optional[str] = None
    ) -> MCPDocument:
        params = []
        if course:
            params.append(f"course={course}")
        if location:
            params.append(f"location={location}")
        query = "&".join(params)
        path = f"/ofqual/search?{query}" if query else "/ofqual/search"
        return await self._get(path)


__all__ = ["MCPDocument", "KYCContextSource"]
