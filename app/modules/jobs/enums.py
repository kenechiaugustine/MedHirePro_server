from enum import Enum

class JobType(str, Enum):
    PERMANENT = "PERMANENT"
    LOCUM = "LOCUM"

class JobStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    FILLED = "FILLED"
    EXPIRED = "EXPIRED"

class RateType(str, Enum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ANNUALLY = "ANNUALLY"

class ClinicalSetting(str, Enum):
    ACUTE_CARE_HOSPITAL = "Acute Care Hospital"
    OUTPATIENT_CLINIC = "Outpatient Clinic"
    REHABILITATION_FACILITY = "Rehabilitation Facility"
    LONG_TERM_CARE = "Long-Term Care Facility"
    SKILLED_NURSING_FACILITY = "Skilled Nursing Facility"
    URGENT_CARE_CENTER = "Urgent Care Center"
    COMMUNITY_HEALTH_CENTER = "Community Health Center"
    TELEHEALTH = "Telehealth"

class ClinicalSpecialty(str, Enum):
    CARDIOLOGY = "Cardiology"
    EMERGENCY_MEDICINE = "Emergency Medicine"
    PEDIATRICS = "Pediatrics"
    INTERNAL_MEDICINE = "Internal Medicine"
    ANESTHESIOLOGY = "Anesthesiology"
    FAMILY_PRACTICE = "Family Practice"
    PULMONOLOGY = "Pulmonology"
    CRITICAL_CARE = "Critical Care"
    OBSTETRICS_GYNECOLOGY = "Obstetrics & Gynecology"
    PSYCHIATRY = "Psychiatry"
    SURGERY = "Surgery"
    GENERAL_PRACTICE = "General Practice"
    NURSING = "Nursing"
    PHARMACY = "Pharmacy"
