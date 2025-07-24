from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class ParentOrganisation:
    groupUkprn: str
    legalName: str
    organisationType: str

@dataclass
class DeliveryAddress:
    line1: str
    postcode: str

@dataclass
class QualificationRequest:
    qualificationId: str
    aoId: str
    aoName: str
    title: str
    startDate: str
    expectedCohortSize: int

@dataclass
class DeliverySite:
    siteId: str
    ukprn: str
    siteName: str
    deliveryAddress: DeliveryAddress
    qualificationsRequested: List[QualificationRequest]

@dataclass
class StaffMember:
    staffId: str
    role: str
    name: str
    email: str

@dataclass
class ComplianceDeclarations:
    ofqualConditionsAcknowledged: bool
    gdprConsent: bool
    multiSiteResponsibilityConfirmed: bool

@dataclass
class CentreSubmission:
    submissionId: str
    submittedAt: datetime
    parentOrganisation: ParentOrganisation
    deliverySites: List[DeliverySite]
    staff: List[StaffMember]
    complianceDeclarations: ComplianceDeclarations
