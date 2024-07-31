from enum import Enum


class ProofOfIdentityType(str, Enum):
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"


class ShopType(str, Enum):
    PRODUCTS = "products"
    SERVICES = "services"
    BOTH = "both"


class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    PAYMENT_ON_DELIVERY = "payment_on_delivery"


class OrderStatusType(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class NotificationType(str, Enum):
    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"


class UserRoleType(str, Enum):
    USER = "user"
    VENDOR = "vendor"
    ADMIN = "admin"


class FilterOperatorType(str, Enum):
    AND = "and"
    OR = "or"
    LT = "lt"
    GT = "gt"
    LTE = "lte"
    GTE = "gte"
    NEQ = "neq"
    LIKE = "like"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"


class WantedHelpType(str, Enum):
    ADS_AND_AWARENESS = "ads_and_awareness"
    GAINING_NEW_CUSTOMERS = "gaining_new_customers"
    PACKAGING_AND_SHIPPING = "packaging_and_shipping"
    SELL_ONLINE = "sell_online"


class VendorStatusType(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    DELETED = "deleted"
