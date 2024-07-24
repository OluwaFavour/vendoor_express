CREATE TABLE "users" (
  "id" int PRIMARY KEY,
  "full_name" varchar,
  "email" varchar UNIQUE,
  "phone_number" varchar UNIQUE,
  "password" varchar,
  "proof_of_identity" enum(passport,drivers_license,national_id),
  "proof_of_identity_image" varchar,
  "business_registration_certificate_image" varchar
);

CREATE TABLE "shops" (
  "id" int PRIMARY KEY,
  "name" varchar UNIQUE,
  "description" text,
  "type" enum(products,services,both),
  "category" varchar,
  "email" varchar,
  "phone_number" varchar,
  "logo" varchar,
  "user_id" int
);

CREATE TABLE "products" (
  "id" int PRIMARY KEY,
  "name" varchar UNIQUE,
  "description" text,
  "specifications" text,
  "packaging" text,
  "stock" int,
  "price" float,
  "category" varchar,
  "sub_category" varchar,
  "media" varchar,
  "created_at" datetime DEFAULT (now()),
  "updated_at" datetime DEFAULT (now()),
  "disabled" boolean DEFAULT false,
  "shop_id" int
);

CREATE TABLE "product_options" (
  "id" int PRIMARY KEY,
  "name" varchar UNIQUE,
  "details" varchar,
  "product_id" int
);

CREATE TABLE "product_reviews" (
  "id" int PRIMARY KEY,
  "rating" int,
  "review" text,
  "images" varchar,
  "product_id" int,
  "created_at" datetime DEFAULT (now()),
  "user_id" int
);

CREATE TABLE "orders" (
  "id" int PRIMARY KEY,
  "order_number" varchar UNIQUE,
  "created_at" datetime DEFAULT (now()),
  "payment_method" enum(card,bank_transfer,payment_on_delivery),
  "user_id" int,
  "card_id" int,
  "delivery_address_id" int
);

CREATE TABLE "order_products" (
  "id" int PRIMARY KEY,
  "quantity" int,
  "product_id" int,
  "order_id" int,
  "status" enum(pending,processing,shipped,delivered,cancelled) DEFAULT 'pending'
);

CREATE TABLE "notifications" (
  "id" int PRIMARY KEY,
  "title" varchar,
  "message" varchar,
  "order_id" int,
  "user_id" int
);

CREATE TABLE "saved" (
  "id" int PRIMARY KEY,
  "user_id" int
);

CREATE TABLE "saved_products" (
  "id" int PRIMARY KEY,
  "product_id" int,
  "saved_id" int
);

CREATE TABLE "carts" (
  "id" int PRIMARY KEY,
  "user_id" int
);

CREATE TABLE "cart_products" (
  "id" int PRIMARY KEY,
  "product_id" int,
  "cart_id" int
);

CREATE TABLE "shipping_addresses" (
  "id" int PRIMARY KEY,
  "full_name" varchar,
  "address" varchar,
  "city" varchar,
  "state" varchar,
  "country" varchar DEFAULT 'Nigeria',
  "phone_number" varchar,
  "user_id" int
);

CREATE TABLE "default_shipping_addresses" (
  "id" int PRIMARY KEY,
  "shipping_address_id" int,
  "user_id" int
);

CREATE TABLE "cards" (
  "id" int PRIMARY KEY,
  "card_name" varchar,
  "card_number" varchar,
  "expiry_date" varchar,
  "cvv" varchar,
  "user_id" int
);

CREATE TABLE "default_cards" (
  "id" int PRIMARY KEY,
  "card_id" int,
  "user_id" int
);

CREATE INDEX ON "shops" ("type", "category", "user_id");

CREATE INDEX ON "products" ("category", "sub_category", "updated_at", "disabled", "shop_id");

CREATE INDEX ON "product_options" ("product_id");

CREATE INDEX ON "product_reviews" ("rating", "product_id", "created_at", "user_id");

CREATE INDEX ON "orders" ("created_at", "user_id", "payment_method");

CREATE INDEX ON "order_products" ("order_id", "status");

COMMENT ON COLUMN "users"."proof_of_identity_image" IS 'URL, optional, length constraint';

COMMENT ON COLUMN "users"."business_registration_certificate_image" IS 'URL, optional, length constraint';

COMMENT ON COLUMN "shops"."logo" IS 'URL';

COMMENT ON COLUMN "products"."media" IS 'URL';

COMMENT ON COLUMN "product_reviews"."rating" IS '1 to 5 constraint';

COMMENT ON COLUMN "product_reviews"."images" IS 'URL';

COMMENT ON COLUMN "orders"."card_id" IS 'optional';

ALTER TABLE "shops" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "orders" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "product_reviews" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "notifications" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "cards" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "shipping_addresses" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "default_cards" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "default_shipping_addresses" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "saved" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "carts" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id");

ALTER TABLE "products" ADD FOREIGN KEY ("shop_id") REFERENCES "shops" ("id");

ALTER TABLE "product_options" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id");

ALTER TABLE "product_reviews" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id");

ALTER TABLE "orders" ADD FOREIGN KEY ("card_id") REFERENCES "cards" ("id");

ALTER TABLE "orders" ADD FOREIGN KEY ("delivery_address_id") REFERENCES "shipping_addresses" ("id");

ALTER TABLE "order_products" ADD FOREIGN KEY ("product_id") REFERENCES "products" ("id");

ALTER TABLE "order_products" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id");

ALTER TABLE "notifications" ADD FOREIGN KEY ("order_id") REFERENCES "orders" ("id");

ALTER TABLE "saved_products" ADD FOREIGN KEY ("saved_id") REFERENCES "saved" ("id");

ALTER TABLE "cart_products" ADD FOREIGN KEY ("cart_id") REFERENCES "carts" ("id");

ALTER TABLE "shipping_addresses" ADD FOREIGN KEY ("id") REFERENCES "default_shipping_addresses" ("shipping_address_id");

ALTER TABLE "cards" ADD FOREIGN KEY ("id") REFERENCES "default_cards" ("card_id");
