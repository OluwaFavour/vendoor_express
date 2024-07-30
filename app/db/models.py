import datetime, uuid, decimal
from typing import Optional

from sqlalchemy.orm import mapped_column, Mapped, relationship, validates
from sqlalchemy import ForeignKey, func, SmallInteger, CheckConstraint

from .base import Base
from .enums import (
    UserRoleType,
    ProofOfIdentityType,
    ShopType,
    PaymentMethodType,
    OrderStatusType,
    NotificationType,
    TokenType,
    WantedHelpType,
    VendorStatusType,
)


class SessionData(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, nullable=False)
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(nullable=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(nullable=False, index=True)
    logged_in_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )


class Token(Base):
    __tablename__ = "token"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    jti: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, insert_default=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    token_type: Mapped[str] = mapped_column(nullable=False, index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="tokens")

    @validates("token_type")
    def validate_token_type(self, key, value):
        if value:
            for enum in TokenType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone_number: Mapped[Optional[str]] = mapped_column(nullable=True, unique=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    proof_of_identity_type: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="Type of proof of identity"
    )
    proof_of_identity_image: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="URL to the image"
    )
    business_registration_certificate_image: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="URL to the image"
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, insert_default=True)
    is_shop_owner: Mapped[bool] = mapped_column(nullable=False, insert_default=False)
    is_first_login: Mapped[Optional[bool]] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(
        nullable=False, index=True, insert_default=f"{UserRoleType.USER.value}"
    )
    shop: Mapped[Optional["Shop"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )
    reviews: Mapped[Optional[list["Review"]]] = relationship(
        back_populates="user", cascade="save-update, merge, refresh-expire, expunge"
    )
    orders: Mapped[Optional[list["Order"]]] = relationship(
        back_populates="user", cascade="save-update, merge, refresh-expire, expunge"
    )
    notifications: Mapped[Optional[list["Notification"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_items: Mapped[Optional[list["SavedItem"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cart_items: Mapped[Optional[list["CartItem"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    addresses: Mapped[Optional[list["Address"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    default_address: Mapped[Optional["DefaultAddress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    default_payment_method: Mapped[Optional["DefaultPaymentMethod"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tokens: Mapped[Optional[list["Token"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cards: Mapped[Optional[list["Card"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    banks: Mapped[Optional[list["Bank"]]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @validates("proof_of_identity_type")
    def validate_proof_of_identity_type(self, key, value):
        if value:
            for enum in ProofOfIdentityType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value

    @validates("role")
    def validate_role(self, key, value):
        if value:
            for enum in UserRoleType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class Shop(Base):
    __tablename__ = "shop"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    tag: Mapped[Optional[str]] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False, index=True)
    category: Mapped[str] = mapped_column(nullable=False, index=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(nullable=False, unique=True)
    wanted_help: Mapped[Optional[str]] = mapped_column(nullable=True)
    cover_photo: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="URL to the image"
    )
    logo: Mapped[str] = mapped_column(nullable=False, comment="URL to the image")
    products: Mapped[Optional[list["Product"]]] = relationship(
        back_populates="shop", cascade="save-update, merge, refresh-expire, expunge"
    )
    status: Mapped[str] = mapped_column(
        nullable=False, insert_default=VendorStatusType.PENDING.value, index=True
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), unique=True
    )
    vendor: Mapped["User"] = relationship(back_populates="shop")

    @validates("type")
    def validate_type(self, key, value):
        if value:
            for enum in ShopType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value

    @validates("wanted_help")
    def validate_wanted_help(self, key, value):
        if value:
            for enum in WantedHelpType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value

    @validates("status")
    def validate_status(self, key, value):
        if value:
            for enum in VendorStatusType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class Product(Base):
    __tablename__ = "product"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    specifications: Mapped[Optional[str]] = mapped_column(nullable=True)
    packaging: Mapped[Optional[str]] = mapped_column(nullable=True)
    stock: Mapped[int] = mapped_column(
        CheckConstraint("stock >= 0", name="stock_non_negative"), nullable=False
    )
    price: Mapped[decimal.Decimal] = mapped_column(
        CheckConstraint("price > 0", name="price_positive"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(nullable=False, index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
    media: Mapped[str] = mapped_column(
        nullable=False, comment="URL to the product media folder with images and videos"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        insert_default=func.now(),
        onupdate=func.now(),
    )
    disabled: Mapped[bool] = mapped_column(
        nullable=False, insert_default=False, index=True
    )
    options: Mapped[Optional[list["ProductOption"]]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )  # Delete options when product is disabled or deleted

    shop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shop.id", ondelete="SET NULL")
    )
    shop: Mapped["Shop"] = relationship(back_populates="products")
    reviews: Mapped[Optional[list["Review"]]] = relationship(
        back_populates="product", cascade="save-update, merge, refresh-expire, expunge"
    )
    orders: Mapped[Optional[list["OrderItem"]]] = relationship(
        back_populates="product", cascade="save-update, merge, refresh-expire, expunge"
    )
    saved: Mapped[Optional["SavedItem"]] = relationship(
        back_populates="product", cascade="save-update, merge, refresh-expire, expunge"
    )
    in_cart: Mapped[Optional["CartItem"]] = relationship(
        back_populates="product", cascade="save-update, merge, refresh-expire, expunge"
    )


class ProductOption(Base):
    __tablename__ = "product_option"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    value: Mapped[str] = mapped_column(nullable=False, index=True)

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="CASCADE")
    )
    product: Mapped["Product"] = relationship(back_populates="options")


class Review(Base):
    __tablename__ = "review"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    rating: Mapped[int] = mapped_column(type_=SmallInteger, nullable=False, index=True)
    comment: Mapped[str] = mapped_column(nullable=False)
    images: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment="URL to the product review image folder"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL")
    )
    user: Mapped["User"] = relationship(back_populates="reviews")
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL")
    )
    product: Mapped["Product"] = relationship(back_populates="reviews")


class Order(Base):
    __tablename__ = "order"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    payment_method: Mapped[str] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL")
    )
    user: Mapped["User"] = relationship(back_populates="orders")
    card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("card.id", ondelete="SET NULL")
    )
    card: Mapped[Optional["Card"]] = relationship(back_populates="orders")
    bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("bank.id", ondelete="SET NULL")
    )
    bank: Mapped[Optional["Bank"]] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    notifications: Mapped[Optional[list["Notification"]]] = relationship(
        back_populates="order", cascade="save-update, merge, refresh-expire, expunge"
    )

    @validates("payment_method")
    def validate_payment_method(self, key, value):
        if value:
            for enum in PaymentMethodType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    quantity: Mapped[int] = mapped_column(type_=SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, index=True, insert_default="pending"
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL")
    )
    product: Mapped["Product"] = relationship(back_populates="orders")

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order.id", ondelete="CASCADE")
    )
    order: Mapped["Order"] = relationship(back_populates="items")

    @validates("status")
    def validate_status(self, key, value):
        if value:
            for enum in OrderStatusType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class Card(Base):
    __tablename__ = "card"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False)
    hashed_number: Mapped[str] = mapped_column(nullable=False)
    last_four: Mapped[str] = mapped_column(nullable=False)
    expiry_date: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    hashed_cvv: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="cards")

    orders: Mapped[Optional[list["Order"]]] = relationship(
        back_populates="card", cascade="save-update, merge, refresh-expire, expunge"
    )
    default: Mapped[Optional["DefaultPaymentMethod"]] = relationship(
        back_populates="card", cascade="save-update, merge, refresh-expire, expunge"
    )


class DefaultPaymentMethod(Base):
    __tablename__ = "default_payment_method"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    payment_method: Mapped[str] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="default_payment_method")
    bank_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("bank.id", ondelete="SET NULL")
    )
    bank: Mapped[Optional["Bank"]] = relationship(back_populates="default")
    card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("card.id", ondelete="SET NULL")
    )
    card: Mapped[Optional["Card"]] = relationship(back_populates="default")

    @validates("payment_method")
    def validate_payment_method(self, key, value):
        if value:
            for enum in PaymentMethodType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class Bank(Base):
    # TODO: Add more columns
    __tablename__ = "bank"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="banks")

    orders: Mapped[Optional[list["Order"]]] = relationship(
        back_populates="bank", cascade="save-update, merge, refresh-expire, expunge"
    )
    default: Mapped[Optional["DefaultPaymentMethod"]] = relationship(
        back_populates="bank", cascade="save-update, merge, refresh-expire, expunge"
    )


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    type: Mapped[str] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(nullable=False)
    read: Mapped[bool] = mapped_column(nullable=False, insert_default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped[Optional["User"]] = relationship(back_populates="notifications")
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("order.id", ondelete="SET NULL")
    )
    order: Mapped[Optional["Order"]] = relationship(back_populates="notifications")

    @validates("type")
    def validate_type(self, key, value):
        if value:
            for enum in NotificationType:
                if value == enum.value:
                    return value
            raise ValueError(f"Invalid value for {key}: {value}")
        return value


class SavedItem(Base):
    __tablename__ = "saved_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="saved_items")
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL")
    )
    product: Mapped["Product"] = relationship(back_populates="saved")


class CartItem(Base):
    __tablename__ = "cart_item"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    quantity: Mapped[int] = mapped_column(type_=SmallInteger, nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product.id", ondelete="SET NULL")
    )
    product: Mapped["Product"] = relationship(back_populates="in_cart")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="cart_items")


class Address(Base):
    __tablename__ = "address"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(nullable=False)
    phone_number: Mapped[str] = mapped_column(nullable=False)
    address: Mapped[str] = mapped_column(nullable=False)
    city: Mapped[str] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(nullable=False)
    country: Mapped[str] = mapped_column(nullable=False, insert_default="Nigeria")
    postal_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, insert_default=func.now(), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="addresses")
    default: Mapped[Optional["DefaultAddress"]] = relationship(
        back_populates="address", cascade="save-update, merge, refresh-expire, expunge"
    )


class DefaultAddress(Base):
    __tablename__ = "default_address"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, insert_default=uuid.uuid4)
    address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("address.id", ondelete="CASCADE")
    )
    address: Mapped["Address"] = relationship(back_populates="default")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="default_address")
