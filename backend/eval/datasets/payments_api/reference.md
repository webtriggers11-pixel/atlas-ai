# PayFlow Payments API — Requirements Specification (v2)

## 1. Introduction
PayFlow lets merchants accept card payments through a REST API. This document lists the requirements for version 2 of the API. Our goal is a delightful developer experience.

## 2. Authentication
Clients must authenticate using the OAuth 2.0 client credentials flow.
Access tokens must expire after 15 minutes.
Refresh tokens must expire after 30 days.
After 5 consecutive failed authentication attempts the client must be locked out for 10 minutes.

## 3. Payments
The API must support idempotency keys on POST /payments so that retried requests do not create duplicate charges.
Payment amounts must be stored as integer minor units (for example cents), never as floating point numbers.
Merchants must be able to refund a payment up to 180 days after it was captured.

## 4. Performance
POST /payments must respond within 300 ms at the 95th percentile.

## 5. Security and Compliance
All handling of card data must comply with PCI DSS v4.0.
All data at rest must be encrypted with AES-256.

## 6. Operations
Webhook deliveries must be retried with exponential backoff for up to 24 hours.
Every error response must include a machine-readable error code such as PF-1042.
