from enum import Enum


class ProofOfIdentityType(str, Enum):
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"


class ShopTypeType(str, Enum):
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


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
