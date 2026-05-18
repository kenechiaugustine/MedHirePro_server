from enum import Enum

class CreditType(str, Enum):
    EARN = "earn"
    SPEND = "spend"

class CreditSource(str, Enum):
    SIGNUP = "signup"
    PURCHASE = "purchase"
    REFERRAL = "referral"
    SOCIALS = "socials"
    DAILY = "daily"
    BONUS = "bonus"
    ADMIN = "admin"
    SPEND = "spend"
    ACCESS = "access"
