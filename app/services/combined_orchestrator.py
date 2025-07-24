# app/services/combined_orchestrator.py
"""Combined orchestrator that reuses real API integrations when available
while falling back to the default educational orchestrator logic."""

from __future__ import annotations

from typing import Optional

from .education_kyc_orchestrator import (
    UKEducationalKYCOrchestrator,
    EducationalProviderRequest,
    EducationalVerificationResult,
)
from .real_kyc_orchestrator import (
    RealEducationalKYCOrchestrator,
    VerificationResult,
)


class CombinedEducationalKYCOrchestrator(UKEducationalKYCOrchestrator):
    """Orchestrator combining real API integrations with educational checks."""

    def __init__(self) -> None:
        super().__init__()
        # Real orchestrator provides API clients. It is used when configured.
        self.real = RealEducationalKYCOrchestrator()

    # Internal helper -----------------------------------------------------
    def _convert_real(self, result: VerificationResult, check_type: Optional[str] = None) -> EducationalVerificationResult:
        """Convert a result from the real orchestrator to the educational format."""
        return EducationalVerificationResult(
            check_type=check_type or result.check_type,
            status=result.status.value,
            risk_score=result.risk_score,
            data_source=result.data_source,
            timestamp=result.timestamp,
            details=result.details,
            recommendations=result.recommendations,
        )

    # Overrides -----------------------------------------------------------
    async def verify_company_registration(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        if self.real.companies_house:
            real_res = await self.real.companies_house.verify_company(
                request.company_number,
                request.organisation_name,
            )
            return self._convert_real(real_res, "company_registration")
        return await super().verify_company_registration(request)

    async def validate_ukprn(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        if self.real.ukrlp and request.ukprn:
            real_res = await self.real.ukrlp.verify_ukprn(
                request.ukprn,
                request.organisation_name,
            )
            return self._convert_real(real_res, "ukprn_validation")
        return await super().validate_ukprn(request)

    async def check_sanctions(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        if self.real.sanctions:
            real_res = await self.real.sanctions.check_sanctions(request.organisation_name)
            return self._convert_real(real_res, "sanctions_screening")
        return await super().check_sanctions(request)

    async def check_ofqual_recognition(self, request: EducationalProviderRequest) -> EducationalVerificationResult:
        # Always available in real orchestrator as it does not require config
        real_res = await self.real.ofqual.verify_awarding_organisation(request.organisation_name)
        return self._convert_real(real_res, "ofqual_recognition")

