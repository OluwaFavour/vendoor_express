# VENDOOR EXPRESS DATABASE SCHEMA

## User

- id: int
- full_name: string
- email: string
- phone_number: string
- password: string
- proof_of_identity: Enum('passport', 'drivers_license', 'national_id')
- proof_of_identity_image: string (url) [optional]
- business_registration_certificate_image: string (url to the business registration certificate image) [optional]

## Shop

- id: int
- name: string
- description: string
- type: Enum('produts', 'services', 'both')
- category: string
- email: string
- phone_number: string
- logo: string (url)
- user_id: int (vendor) [index, unique]

## Product

- id: int
- name: string
- description: string
- specifications: string
- packaging: string
- stock: int
- price: float
- category: string
- sub_category: string
- media: string (url to the product media folder - images, videos)
- created_at: datetime
- updated_at: datetime
- disabled: boolean
- shop_id: int

## ProductOption

- id: int
- name: string (size, color, etc) [index, unique]
- details: string (comma separated values)
- product_id: int

## ProductReview

- id: int
- rating: int
- review: string
- images: string (url to the user product review images folder)
- product_id: int
- user_id: int (customer) [index, unique]
- created_at: datetime

## Order

- id: int
- order_number: string
- created_at: datetime
- user_id: int (customer)
- payment_method: Enum('card', 'bank_transfer', 'payment_on_delivery')
- card_id: int (card) [optional, required if payment_method is 'card']
- delivery_address_id: int (shipping_address)

## OrderProduct

- id: int
- quantity: int
- product_id: int (product)
- order_id: int (order)
- status: Enum('pending', 'processing', 'shipped', 'delivered', 'cancelled')

## Notification

- id: int
- title: string
- message: string
- order_id: int
- user_id: int (user)

## SavedProduct

- id: int
- product_id: int (product) [index, unique]
- user_id: int (customer)

## CartProduct

- id: int
- product_id: int (product)
- user_id: int (customer)

## ShippingAddress

- id: int
- full_name: string
- address: string
- city: string
- state: string
- country: string [default: 'Nigeria']
- phone_number: string
- user_id: int (customer)

## DefaultShippingAddress

- id: int
- shipping_address_id: int (shipping_address)
- user_id: int (customer) [index, unique]

## Card

- id: int
- card_name: string
- card_number: string
- expiry_date: string
- cvv: string
- user_id: int (customer)

## DefaultCard

- id: int
- card_id: int (card)
- user_id: int (customer) [index, unique]

Relationship: One user has one shop (vendor)
Relationship: One shop has many products
Relationship: One product has many product options
Relationship: One product has many product reviews
Relationship: One user has many product reviews but one product review belongs to one user
Relationship: One user has many orders (customer)
Relationship: One order has many order products
Relationship: One order has one shipping address
Relationship: One order has one card
Relationship: One OrderProduct belongs to one product and one order
Relationship: One order has many notifications
Relationship: One user has many notifications
Relationship: One user has many saved products
Relationship: One user has many cart products
Relationship: One user has many shipping addresses
Relationship: One user has one default shipping address
Relationship: One user has many cards
Relationship: One user has one default card
