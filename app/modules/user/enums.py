from enum import Enum

class UserRole(str, Enum):
    PROFESSIONAL = "professional"
    INSTITUTE = "institute"
    ADMIN = "admin"

class EmploymentStatus(str, Enum):
    UNEMPLOYED = "unemployed"
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
