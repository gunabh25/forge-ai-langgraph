# Examples

Here are examples demonstrating the expected output structure for the Architecture Specification document.

## Example 1: POS System (Point of Sale)

# Executive Summary
This document defines the architecture specification for the cloud-based Point of Sale (POS) system. The system must support 1 Warehouse and 17 Stores, integrating barcode scanners, receipt printers, and store-to-store stock transfers.

# Architecture Overview
The system employs a client-server model with a local offline-first progressive web application (PWA) client running at each store terminal, communicating with a centralized cloud backend.

# Architecture Pattern
Modular Monolith. A modular monolith is selected because the domain complexity is medium, and the deployment footprint must remain low and cost-effective across 17 stores. Clear boundaries are defined between modules (Sales, Inventory, Transfers, Access Control) to allow future separation into microservices if needed.

# System Components
- **Checkout Client**: Frontend PWA running on cash registers.
- **POS Core API**: Centralized backend handling business logic and sync.
- **Local SQLite Database**: Embedded inside each store's local browser runtime for offline resilience.
- **Central Postgres Database**: Main relational store in the cloud.

# Technology Stack
- **Frontend**: React, TypeScript, Tailwind CSS, Workbox (PWA Service Worker)
- **Backend**: FastAPI, Python 3.12, SQLAlchemy
- **Database**: PostgreSQL (Cloud), SQLite (Local Terminal)
- **Caching**: Redis for session cache and stock level cache
- **Messaging**: RabbitMQ for asynchronous stock transfer events
- **Authentication**: JWT-based OAuth2
- **Storage**: AWS S3 for digital receipts backup
- **Monitoring**: Prometheus, Grafana
- **Logging**: Loguru, structured JSON logging to Elasticsearch

# Database Design
- **Entities**: User, Store, Warehouse, Product, StockLedger, Transaction, TransferRequest
- **Relationships**: Store (1) -> (*) User, Product (1) -> (*) StockLedger, Store (1) -> (*) Transaction
- **Indexes**: Composite index on (store_id, product_id) in StockLedger; index on transaction_date.
- **Constraints**: Product SKU must be unique; Stock counts cannot be negative unless pre-approved.

# API Design
- **Major REST endpoints**:
  - `POST /api/v1/auth/login` (Authenticate users)
  - `GET /api/v1/products/scan?barcode={code}` (Resolve barcode scanner)
  - `POST /api/v1/sales/checkout` (Create transaction)
  - `POST /api/v1/transfers/request` (Initiate inventory transfer)
- **Authentication flow**: JWT access token passed via Authorization header (`Bearer <token>`).
- **Request structure**: JSON payload with schemas validated by Pydantic.
- **Response structure**: Standard success wrapper or RFC 7807 problem details error format.
- **Error strategy**: Standardize on HTTP status codes: 400 for bad request, 401/403 for access issues, 422 for validation errors.

# External Integrations
- **Payment gateways**: Stripe Terminal SDK for physical card reader integration.
- **Email**: SendGrid for sending digital receipt copy.
- **SMS**: Twilio for daily sales summaries to business owners.
- **Cloud storage**: AWS S3.
- **Authentication providers**: Okta for administrative single sign-on.
- **Third-party APIs**: Integration with tax rate API.

# Scalability Strategy
- **Horizontal scaling**: Stateless POS Core API scaled dynamically via Kubernetes HPA.
- **Vertical scaling**: Scale DB writer node to larger instance family (e.g. AWS r6g).
- **Caching**: Store lookup data in Redis with a 24-hour TTL.
- **Connection pooling**: PgBouncer for database connection pooling.
- **Read replicas**: Route reporting dashboard queries to a PostgreSQL read replica.
- **Rate limiting**: Limit POS terminal requests to 100 requests per minute using token bucket algorithm.

# Reliability
- **Retries**: 3 retries with exponential backoff for external payment API requests.
- **Circuit breakers**: Apply circuit breaker (e.g. using Tenacity/Resilience4j) on the tax rate API.
- **Health checks**: `/health/liveness` and `/health/readiness` endpoints.
- **Timeouts**: Timeout HTTP requests to external APIs after 3 seconds.
- **Monitoring**: Alerts triggered on p99 latency exceeding 500ms or 5xx rate exceeding 1%.

# Security Considerations
- **Authentication**: Double-signed JWT tokens with short expiry (15 minutes).
- **Authorization**: Role-Based Access Control (Cashier, Store Manager, Warehouse Manager).
- **Encryption**: TLS 1.3 in transit; AES-256 transparent data encryption (TDE) at rest.
- **Secrets**: HashiCorp Vault.
- **OWASP**: Implement parameterized SQL queries, sanitization of inputs, and strict Content Security Policy.

# Tradeoffs
- **Advantages**: Easy to deploy and monitor, high offline reliability due to SQLite sync.
- **Disadvantages**: Synchronizing conflicts between offline SQLite edits and cloud Postgres can be complex.
- **Future improvements**: Transition to Event Sourcing for inventory transfers to track lineage accurately.

---

## Example 2: Inventory Management System

# Executive Summary
Architecture for an internal multi-warehouse Inventory Management System.

# Architecture Overview
A web-based portal using a three-tier architecture patterns (Presentation, Application, Data) running on virtualized resources.

# Architecture Pattern
Layered. A Layered (3-tier) pattern separates concerns logically into User Interface, Business Logic, and Data Access layers. This is selected to keep the implementation simple, testable, and highly aligned with standard MVC frameworks.

# System Components
- **Web UI Portal**: Frontend interface for operators.
- **Inventory Service**: Handles stock rules, reorder thresholds, and bin locations.
- **Report Worker**: Background task runner for compiling summaries.

# Technology Stack
- **Frontend**: Next.js, React, Tailwind CSS
- **Backend**: Node.js, NestJS
- **Database**: PostgreSQL
- **Caching**: Redis
- **Messaging**: Redis Pub/Sub for alerts
- **Authentication**: Keycloak OAuth2
- **Storage**: AWS S3 for export sheets
- **Monitoring**: Datadog
- **Logging**: Winston

# Database Design
- **Entities**: SKU, InventoryItem, WarehouseLocation, StockAdjustment
- **Relationships**: SKU (1) -> (*) InventoryItem, WarehouseLocation (1) -> (*) InventoryItem
- **Indexes**: B-tree index on SKU code.
- **Constraints**: SKU format must conform to standard regex pattern.

# API Design
- **Major REST endpoints**:
  - `GET /api/v1/inventory?warehouse_id={id}`
  - `POST /api/v1/inventory/adjust`
- **Authentication flow**: OAuth2 Authorization Code Flow with PKCE.
- **Request structure**: JSON objects validating input formats.
- **Response structure**: Enveloped JSON lists.
- **Error strategy**: Custom exceptions mapped to standard HTTP statuses.

# External Integrations
- **Cloud storage**: Google Cloud Storage for report PDFs.
- **Third-party APIs**: ERP system SOAP integration.

# Scalability Strategy
- **Horizontal scaling**: Auto-scaling group for Web Portal.
- **Caching**: Cache SKU metadata locally in-memory.
- **Read replicas**: Segregate write ledger transactions from read-only catalog queries.

# Reliability
- **Retries**: Automated database query retry on deadlock error.
- **Health checks**: TCP health probes.
- **Timeouts**: Timeout API requests to legacy ERP system after 10 seconds.

# Security Considerations
- **Authorization**: Attribute-based access control (ABAC) based on Warehouse location assignment.
- **Encryption**: HTTPS-only transport.

# Tradeoffs
- **Advantages**: Straightforward design, low operational overhead.
- **Disadvantages**: Hard-coupled layers limit scaling parts of the system independently.

---

## Example 3: Hospital Management System

# Executive Summary
Architectural framework for an enterprise-level, HIPAA-compliant Hospital Management System (HMS).

# Architecture Overview
Service-oriented architecture dividing patient management, EHR records, scheduling, and billing into independent modules.

# Architecture Pattern
Hexagonal (Ports & Adapters). Hexagonal architecture is selected to decouple the core healthcare business domain (EHR rules, patient triage logic) from external dependencies like databases, third-party labs, and billing systems. This ensures the medical logic can be tested in isolation and remains highly portable.

# System Components
- **HMS Core Domain**: Contains medical, appointment, and billing policies.
- **Adapters**: PostgreSQL database adapter, legacy lab integration adapter, Web API port.

# Technology Stack
- **Frontend**: Angular 17, NgRx
- **Backend**: Spring Boot 3.2, Java 21
- **Database**: Oracle DB (for transactions), MongoDB (for EHR document history)
- **Caching**: Hazelcast
- **Messaging**: Apache Kafka for patient event publishing
- **Authentication**: OpenID Connect with MFA
- **Storage**: Azure Blob Storage (for medical scans)
- **Monitoring**: Dynatrace
- **Logging**: SLF4J, Logback

# Database Design
- **Entities**: Patient, ConsultationRecord, Appointment, Invoice, LabReport
- **Relationships**: Patient (1) -> (*) ConsultationRecord, Patient (1) -> (*) Appointment
- **Indexes**: Index on patient medical record number (MRN).
- **Constraints**: Audit log table is append-only; updates require a new version record.

# API Design
- **Major REST endpoints**:
  - `GET /api/v1/patients/{id}/ehr`
  - `POST /api/v1/appointments/schedule`
- **Authentication flow**: OpenID Connect with multi-factor authentication (MFA).
- **Request structure**: Strongly-typed Java payloads matching API models.
- **Response structure**: JSON objects containing patient metadata.
- **Error strategy**: Centralized exception handler rendering medical-error codes.

# External Integrations
- **Email**: Amazon SES.
- **SMS**: Twilio.
- **Cloud storage**: Azure Blob Storage.
- **Third-party APIs**: Integration with HL7/FHIR health data exchange APIs.

# Scalability Strategy
- **Horizontal scaling**: Scale JVM containers using Kubernetes.
- **Caching**: Multi-level caching (L1 local JVM, L2 shared Hazelcast).
- **Read replicas**: Oracle Active Data Guard for reporting.

# Reliability
- **Circuit breakers**: Resilience4j wrapping HL7 integration points.
- **Health checks**: Spring Boot Actuator endpoints.
- **Timeouts**: Medical record load queries timeout after 5 seconds.

# Security Considerations
- **Authentication**: Mutual TLS (mTLS) for system-to-system APIs.
- **Encryption**: AES-256 for EHR fields; TLS 1.3 in transit.
- **OWASP**: XML/JSON parsing sanitization to prevent injection.

# Tradeoffs
- **Advantages**: Extremely testable, modular, high security posture.
- **Disadvantages**: High initial development effort due to abstracting adapters.

---

## Example 4: Ride Sharing App

# Executive Summary
High-throughput system architecture for matching riders and drivers.

# Architecture Overview
An event-driven microservices architecture optimized for low-latency location-tracking and matching.

# Architecture Pattern
Event-Driven Architecture. Event-driven matching is chosen because the system must process massive streams of continuous GPS coordinates, ride requests, and dispatch confirmations asynchronously. Event logs act as the source of truth for location telemetry and fare calculations.

# System Components
- **Ingress Service**: Handles raw GPS coordinate ingestion from mobile devices.
- **Matching Service**: Event-driven engine matching drivers to riders.
- **Billing Service**: Listens for trip completion events to process payments.

# Technology Stack
- **Frontend**: Flutter (iOS/Android)
- **Backend**: Go (matching engine), Node.js (billing)
- **Database**: PostgreSQL with PostGIS extension, Redis Enterprise
- **Caching**: Redis
- **Messaging**: Kafka (high-throughput event streaming)
- **Authentication**: JWT, OAuth2
- **Storage**: GCS
- **Monitoring**: Grafana, Prometheus
- **Logging**: ELK Stack

# Database Design
- **Entities**: Rider, Driver, Trip, LocationPing, PaymentReceipt
- **Relationships**: Rider (1) -> (*) Trip, Driver (1) -> (*) Trip
- **Indexes**: Spatial index (GIST) on PostGIS location geometry in Trip table.
- **Constraints**: Driver status must be in (offline, active, busy).

# API Design
- **Major REST endpoints**:
  - `POST /api/v1/trips/request`
  - `POST /api/v1/drivers/ping-location`
- **Authentication flow**: JWT with short refresh cycles.
- **Request structure**: JSON maps containing geographical coordinates.
- **Response structure**: Trip object including driver info and ETA.

# External Integrations
- **Payment gateways**: Braintree for app-based credit cards.
- **Cloud storage**: Google Cloud Storage.
- **Third-party APIs**: Google Maps API for route calculation.

# Scalability Strategy
- **Horizontal scaling**: Go services scale instantly on Kubernetes.
- **Caching**: Geohash-based partitioning in Redis.
- **Rate limiting**: API Gateway limits driver location pings to 1 per 5 seconds.

# Reliability
- **Retries**: Exponential retry on Braintree transaction failures.
- **Circuit breakers**: Envoy gateway circuit breaker rules.
- **Timeouts**: Geocoding requests timeout in 1.5 seconds.

# Security Considerations
- **Encryption**: Encryption of location database columns; HTTPS.
- **OWASP**: Strict CORS policies, input validation on location parameters.

# Tradeoffs
- **Advantages**: Extremely scalable, low response latency.
- **Disadvantages**: Complex distributed trace tracking, eventual consistency issues.

---

## Example 5: CRM System (Customer Relationship Management)

# Executive Summary
Architecture for an enterprise Customer Relationship Management (CRM) platform.

# Architecture Overview
A clean architecture design separating domain models, application use cases, adapters, and frameworks.

# Architecture Pattern
Clean Architecture. Clean Architecture is selected to ensure that business rules (lead scoring, deal pipelines) are completely independent of web frameworks, UI platforms, or database models. This isolation facilitates upgrading frameworks or swapping the presentation layer without affecting core business policies.

# System Components
- **Domain Layer**: Contains Lead, Account, Opportunity, Contact.
- **Use Cases**: CreateLead, ConvertOpportunity, GeneratePipelineReport.
- **UI & Gateway Adapters**: Web Controller, Database Gateway.

# Technology Stack
- **Frontend**: Vue.js, Vuex
- **Backend**: Python 3.12, Django (as an outer framework only)
- **Database**: PostgreSQL (relational storage)
- **Caching**: Memcached
- **Messaging**: Celery with Redis broker (background tasks)
- **Authentication**: Auth0 Integration
- **Storage**: AWS S3
- **Monitoring**: New Relic
- **Logging**: Standard Python logging

# Database Design
- **Entities**: Contact, Lead, Deal, Task
- **Relationships**: Account (1) -> (*) Contact, Lead (1) -> (*) Deal
- **Indexes**: Indexes on owner_id and email fields.
- **Constraints**: Lead status field values restricted via Enum.

# API Design
- **Major REST endpoints**:
  - `GET /api/v1/leads`
  - `POST /api/v1/deals`
- **Authentication flow**: JWT validation via Auth0 middleware.
- **Request structure**: JSON objects validating input formats.
- **Response structure**: JSON response containing deal/lead lists.
- **Error strategy**: Global error handler middleware returning standard JSON responses.

# External Integrations
- **Email**: SendGrid.
- **SMS**: Twilio.
- **Cloud storage**: AWS S3.
- **Authentication providers**: Auth0.
- **Third-party APIs**: Clearbit API for lead enrichment.

# Scalability Strategy
- **Horizontal scaling**: Web worker dynos scaled horizontally.
- **Caching**: Cache pipeline reports which compile hourly.
- **Connection pooling**: PgBouncer.

# Reliability
- **Circuit breakers**: Applied to lead enrichment API calls.
- **Health checks**: Readiness probes checking Postgres and Redis connectivity.
- **Timeouts**: Clearbit requests timeout in 2 seconds.

# Security Considerations
- **Authorization**: Role-Based Access Control (Sales Rep, Manager, Admin).
- **Encryption**: TLS 1.3 in transit; encrypted fields for sensitive contacts.
- **OWASP**: Validation of email patterns and input sanitization to prevent XSS.

# Tradeoffs
- **Advantages**: Modular, easy to refactor UI or DB layers without breaking business rules.
- **Disadvantages**: boilerplate mapping code between domain entities and database models.
