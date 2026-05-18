from enum import Enum

class UserRole(str, Enum):
    PROFESSIONAL = "professional"
    INSTITUTE = "institute"
    ADMIN = "admin"
