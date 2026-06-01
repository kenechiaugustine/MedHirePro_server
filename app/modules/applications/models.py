from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.modules.jobs.enums import JobType
from app.modules.applications.enums import ApplicationStatus

class ApplicationModel:
    """
    Tracks applications submitted by verified professionals for unified job listings (permanent or locum).
    Tracks shortlist status and accepted/contracted status.
    """
    @staticmethod
    def new_application(
        candidate_id: str,
        vacancy_id: str,                        # References unified Job Listing
        vacancy_type: JobType,                  # PERMANENT or LOCUM
        curriculum_vitae_url: str,
        clinical_summary: str,
        credentialing_packet_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "vacancy_id": vacancy_id,
            "vacancy_type": vacancy_type,
            "curriculum_vitae_url": curriculum_vitae_url,       # CV / Resume URL
            "clinical_summary": clinical_summary,               # Cover letter / Professional profile
            "credentialing_packet_urls": credentialing_packet_urls or [], # Supporting documents
            "is_shortlisted": False,
            "is_accepted": False,
            "application_status": ApplicationStatus.SUBMITTED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
