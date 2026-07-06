# Executive Summary
This document outlines the architectural specification for a cloud-based Point of Sale (POS) system designed to support 1 central warehouse and 17 retail stores. The primary goals are to enable efficient sales transactions, provide real-time inventory visibility, streamline inventory transfers, and ensure secure, role-based access. The proposed architecture leverages a hybrid approach combining an offline-first Progressive Web Application (PWA) for store operations with a centralized cloud backend. This design prioritizes high availability, data consistency, and scalability, while mitigating risks associated with network outages at store locations.

# Architecture Overview
The system employs a client-server model with a strong emphasis on offline capabilities at the store level. Each POS terminal will run a Progressive Web Application (PWA) that can operate autonomously for sales transactions during network interruptions. This PWA client communicates with a centralized cloud-hosted backend API, which manages core business logic, central inventory, user authentication, and reporting. A dedicated synchronization mechanism will ensure eventual consistency between local client data and the central database, particularly for sales transactions and inventory updates.

# Architecture Pattern
**Modular Monolith with Offline-First PWA Client.**

This architecture pattern is chosen for the following reasons:

1.  **Offline Availability (NFR)**: The critical requirement for 99.9% uptime during store operating hours and the explicit need for an "offline mode for sales transactions" (NFR) is directly addressed by the PWA client. The PWA will utilize client-side storage (e.g., IndexedDB) to cache essential data and queue transactions, ensuring business continuity even during network outages.
2.  **Balanced Complexity and Cost (Business Objective)**: For an initial deployment across 17 stores and 1 warehouse, a full microservices architecture might introduce unnecessary operational overhead and complexity. A modular monolith allows for clear separation of concerns (e.g., Sales, Inventory, User Management modules) within a single deployment unit, simplifying development, testing, and initial deployment while maintaining a cohesive codebase. This aligns with the need for a cost-effective solution.
3.  **Maintainability and Scalability (NFRs)**: The modular design ensures that different business domains are encapsulated, allowing for independent development and easier debugging. Should specific modules (e.g., Inventory Management) experience disproportionate load or require specialized scaling, they can be refactored into separate microservices in the future with reduced effort, fulfilling the scalability NFR to accommodate up to 50 stores.
4.  **Data Consistency (Reliability NFR)**: While the client operates offline, the centralized backend and database ensure strong transactional consistency for critical operations like inventory adjustments and transfers once data is synchronized, which is vital for maintaining accurate inventory levels across all locations.

# System Components
1.  **POS Client (Progressive Web Application - PWA)**:
    *   **Responsibility**: User interface for cashiers, barcode scanning, item addition, transaction processing (cash, card), receipt printing, refunds/voids, local data caching, offline transaction queuing, and synchronization with the backend.
    *   **Interaction**: Communicates with the POS Core API for real-time data and synchronization. Stores data locally using client-side storage.
2.  **POS Core API (Modular Monolith Backend)**:
    *   **Responsibility**: Centralized business logic for Sales, Product Management, Inventory Management, Inventory Transfers, User Management, and Reporting. Acts as the single source of truth for all data. Handles authentication and authorization.
    *   **Interaction**: Exposes RESTful APIs to the POS Client and Reporting Service. Interacts with the Central Database, Caching layer, and Messaging system.
3.  **Synchronization Service**:
    *   **Responsibility**: Manages the reliable transfer of data between offline POS Clients and the POS Core API. Handles conflict resolution for concurrent updates (e.g., inventory adjustments). Ensures eventual consistency.
    *   **Interaction**: Receives queued transactions from POS Clients, pushes inventory updates to clients, and interacts with the POS Core API.
4.  **Central Database**:
    *   **Responsibility**: Persistent storage for all transactional data (sales, inventory movements, transfers), product master data, user accounts, and configuration. Ensures ACID properties for critical operations.
    *   **Interaction**: Accessed exclusively by the POS Core API and Synchronization Service.
5.  **Reporting Service**:
    *   **Responsibility**: Generates various reports (daily sales, inventory levels, transfer history) based on data from the Central Database. Can offload complex queries to read replicas.
    *   **Interaction**: Queries the Central Database (potentially read replicas) and provides data to authorized users via the POS Core API.
6.  **Caching Layer**:
    *   **Responsibility**: Stores frequently accessed data (e.g., product details, current stock levels for quick lookups, user sessions) to improve performance and reduce database load.
    *   **Interaction**: Accessed by the POS Core API.
7.  **Messaging System**:
    *   **Responsibility**: Facilitates asynchronous communication between components, particularly for inventory updates, transfer confirmations, and potentially for triggering background tasks (e.g., report generation, complex sync operations).
    *   **Interaction**: POS Core API publishes events; Synchronization Service and Reporting Service consume events.

# Technology Stack
-   **Frontend**:
    *   **Selected technologies**: React, TypeScript, Tailwind CSS, Workbox (for Service Worker management), IndexedDB (for client-side offline storage).
    *   **Rationale**: React provides a robust framework for building complex UIs. TypeScript enhances code quality and maintainability. Tailwind CSS offers utility-first styling for rapid development. Workbox simplifies PWA development, enabling reliable offline capabilities and background sync, which is critical for the "offline mode" requirement. IndexedDB provides a powerful, persistent client-side database for storing transactions and inventory data when offline.
-   **Backend**:
    *   **Selected technologies**: Python 3.12, FastAPI, SQLAlchemy (ORM), Pydantic (data validation).
    *   **Rationale**: Python with FastAPI offers high performance, excellent developer experience, and strong type hinting, making it suitable for a modular monolith. SQLAlchemy provides a powerful and flexible ORM for database interactions, ensuring data integrity. Pydantic is ideal for robust API request/response validation.
-   **Database**:
    *   **Selected technologies**: PostgreSQL.
    *   **Rationale**: PostgreSQL is a highly reliable, feature-rich, open-source relational database known for its strong ACID compliance, which is crucial for transactional integrity in a POS and inventory system. It supports complex queries, indexing, and replication, essential for scalability and reliability.
-   **Caching**:
    *   **Selected technologies**: Redis.
    *   **Rationale**: Redis is an in-memory data store, ideal for high-speed caching of frequently accessed data like product details, current stock levels, and user sessions. Its pub/sub capabilities can also be leveraged for real-time notifications or internal messaging.
-   **Messaging**:
    *   **Selected technologies**: RabbitMQ.
    *   **Rationale**: RabbitMQ is a mature and robust message broker that supports various messaging patterns. It will be used for asynchronous inventory updates (propagating changes across locations), transfer confirmations, and queuing offline transactions for the Synchronization Service, ensuring reliable delivery and decoupling of components.
-   **Authentication**:
    *   **Selected technologies**: JWT (JSON Web Tokens) with OAuth2 flow.
    *   **Rationale**: JWTs provide a stateless, secure, and scalable method for user authentication and authorization. OAuth2 defines a standard framework for delegated authorization, suitable for both user login and potential future integrations.
-   **Storage**:
    *   **Selected technologies**: AWS S3 (or equivalent cloud object storage like GCS/Azure Blob Storage).
    *   **Rationale**: S3 offers highly durable, scalable, and cost-effective object storage. It will be used for storing digital copies of receipts, audit logs, and potentially backups of reports.
-   **Monitoring**:
    *   **Selected technologies**: Prometheus, Grafana.
    *   **Rationale**: Prometheus is a powerful open-source monitoring system for collecting metrics, and Grafana provides excellent visualization and dashboarding capabilities. This combination allows for comprehensive monitoring of application performance, system health, and resource utilization, crucial for meeting performance and availability NFRs.
-   **Logging**:
    *   **Selected technologies**: ELK Stack (Elasticsearch, Logstash, Kibana).
    *   **Rationale**: The ELK stack provides a centralized, scalable solution for collecting, processing, and analyzing logs from all application components. This is essential for debugging, auditing critical actions (Security NFR), and diagnosing issues quickly, supporting the maintainability NFR.

# Database Design
-   **Entities**:
    *   `Location`: Represents a store or the central warehouse. Attributes: `location_id` (PK), `name`, `address`, `type` (e.g., 'store', 'warehouse').
    *   `Product`: Master data for all products. Attributes: `product_id` (PK), `sku` (Unique), `barcode` (Unique), `name`, `description`, `price`, `is_active`.
    *   `User`: System users. Attributes: `user_id` (PK), `username` (Unique), `password_hash`, `email`, `first_name`, `last_name`, `location_id` (FK to Location, nullable for admins), `is_active`.
    *   `Role`: User roles for RBAC. Attributes: `role_id` (PK), `name` (e.g., 'Cashier', 'Store Manager', 'Warehouse Manager', 'Administrator').
    *   `UserRole`: Junction table for many-to-many relationship between User and Role. Attributes: `user_id` (FK), `role_id` (FK).
    *   `Inventory`: Tracks stock levels per product per location. Attributes: `inventory_id` (PK), `location_id` (FK), `product_id` (FK), `quantity`, `last_updated`.
    *   `InventoryAdjustment`: Records manual inventory changes. Attributes: `adjustment_id` (PK), `inventory_id` (FK), `user_id` (FK), `adjustment_type` (e.g., 'stock_take', 'damage', 'return'), `quantity_change`, `reason`, `timestamp`.
    *   `InventoryTransfer`: Records requests and confirmations for transfers. Attributes: `transfer_id` (PK), `sending_location_id` (FK), `receiving_location_id` (FK), `product_id` (FK), `quantity`, `requested_by_user_id` (FK), `request_timestamp`, `status` (e.g., 'pending', 'sent', 'received', 'rejected'), `confirmed_by_user_id` (FK, nullable), `confirmation_timestamp` (nullable).
    *   `Transaction`: Represents a sales transaction. Attributes: `transaction_id` (PK), `location_id` (FK), `user_id` (FK), `transaction_timestamp`, `subtotal`, `tax_amount`, `grand_total`, `payment_method`, `status` (e.g., 'completed', 'refunded', 'voided'), `receipt_url` (nullable).
    *   `TransactionItem`: Line items within a transaction. Attributes: `transaction_item_id` (PK), `transaction_id` (FK), `product_id` (FK), `quantity`, `unit_price`, `total_price`, `discount_amount` (nullable).
    *   `AuditLog`: Records critical system actions. Attributes: `log_id` (PK), `user_id` (FK, nullable), `action_type`, `entity_type`, `entity_id`, `details` (JSONB), `timestamp`.
-   **Relationships**:
    *   `Location` 1:N `Inventory` (a location has many inventory records)
    *   `Product` 1:N `Inventory` (a product has many inventory records across locations)
    *   `User` 1:N `Transaction` (a user processes many transactions)
    *   `Transaction` 1:N `TransactionItem` (a transaction has many items)
    *   `Product` 1:N `TransactionItem` (a product can be in many transaction items)
    *   `Location` 1:N `InventoryTransfer` (as sending_location_id)
    *   `Location` 1:N `InventoryTransfer` (as receiving_location_id)
    *   `Product` 1:N `InventoryTransfer` (a product is transferred)
    *   `User` N:M `Role` (via `UserRole` junction table)
    *   `Inventory` 1:N `InventoryAdjustment` (an inventory record has many adjustments)
-   **Indexes**:
    *   `Product`: Unique index on `sku`, unique index on `barcode`.
    *   `Inventory`: Composite unique index on (`location_id`, `product_id`) for efficient stock lookup.
    *   `Transaction`: Index on `transaction_timestamp`, index on `location_id`.
    *   `InventoryTransfer`: Index on `request_timestamp`, composite index on (`sending_location_id`, `status`), composite index on (`receiving_location_id`, `status`).
    *   `User`: Unique index on `username`.
    *   `AuditLog`: Index on `timestamp`, index on `user_id`.
-   **Constraints**:
    *   `Product.sku` and `Product.barcode` must be unique.
    *   `Product.price` must be greater than 0.
    *   `Inventory.quantity` cannot be negative (enforced at application level, with specific exceptions for authorized adjustments).
    *   `InventoryTransfer.quantity` must be greater than 0.
    *   Foreign key constraints on all relationships to ensure referential integrity.
    *   `Transaction.status` and `InventoryTransfer.status` fields should be ENUMs or checked against predefined values.
    *   `AuditLog` table should be append-only.

# API Design
The POS Core API will expose RESTful endpoints following standard conventions.

-   **Major REST endpoints**:
    *   **Authentication & User Management**:
        *   `POST /api/v1/auth/login`: Authenticate user credentials and return a JWT.
        *   `POST /api/v1/auth/logout`: Invalidate user session/JWT (if using server-side token revocation).
        *   `GET /api/v1/users/me`: Get current authenticated user's profile.
        *   `POST /api/v1/users`: Create a new user (Admin only).
        *   `PUT /api/v1/users/{id}`: Update user details (Admin only).
    *   **Product Management**:
        *   `POST /api/v1/products`: Add a new product (Admin/Warehouse Manager).
        *   `GET /api/v1/products/{id}`: Get product details by ID.
        *   `GET /api/v1/products/scan?barcode={code}`: Resolve product details by barcode.
        *   `PUT /api/v1/products/{id}`: Update product details (Admin/Warehouse Manager).
        *   `DELETE /api/v1/products/{id}`: Deactivate/Delete product (Admin only).
    *   **Sales Transactions**:
        *   `POST /api/v1/sales/checkout`: Process a new sales transaction.
        *   `POST /api/v1/sales/{transaction_id}/refund`: Process a refund for a transaction (Store Manager+).
        *   `POST /api/v1/sales/{transaction_id}/void`: Void a transaction (Store Manager+).
        *   `GET /api/v1/sales/{transaction_id}`: Retrieve transaction details.
    *   **Inventory Management**:
        *   `GET /api/v1/inventory?location_id={id}&product_id={id}`: View inventory levels for a specific product at a location.
        *   `GET /api/v1/inventory/locations/{location_id}`: View all inventory for a specific location.
        *   `POST /api/v1/inventory/adjust`: Manually adjust inventory levels (Store Manager/Warehouse Manager).
    *   **Inventory Transfer**:
        *   `POST /api/v1/transfers/request`: Initiate an inventory transfer request.
        *   `GET /api/v1/transfers?status={status}&location_id={id}`: View pending/completed transfers for a location.
        *   `POST /api/v1/transfers/{transfer_id}/confirm`: Confirm receipt of transferred inventory (Receiving Store Manager/Warehouse Manager).
        *   `POST /api/v1/transfers/{transfer_id}/reject`: Reject an inventory transfer (Receiving Store Manager/Warehouse Manager).
    *   **Reporting**:
        *   `GET /api/v1/reports/sales/daily?location_id={id}&date={date}`: Generate daily sales report.
        *   `GET /api/v1/reports/inventory?location_id={id}`: Generate current inventory report.
        *   `GET /api/v1/reports/transfers/history?location_id={id}`: Generate inventory transfer history report.
-   **Authentication flow**:
    *   Users send `username` and `password` to `POST /api/v1/auth/login`.
    *   Upon successful authentication, the API returns a JWT (access token) in the response body.
    *   For subsequent requests, the client includes the JWT in the `Authorization` header as `Bearer <token>`.
    *   The backend validates the JWT's signature, expiry, and claims to authenticate and authorize the request.
-   **Request structure**:
    *   All requests will use JSON payloads.
    *   Example `POST /api/v1/sales/checkout` request:
        ```json
        {
          "location_id": "store_001",
          "user_id": "cashier_001",
          "payment_method": "credit_card",
          "items": [
            {"product_id": "prod_abc", "quantity": 2, "unit_price": 10.50, "discount_amount": 0},
            {"product_id": "prod_xyz", "quantity": 1, "unit_price": 25.00, "discount_amount": 2.50}
          ],
          "payment_details": {
            "card_token": "tok_visa",
            "amount": 33.50
          }
        }
        ```
-   **Response structure**:
    *   Successful responses will typically return a JSON object containing the requested resource or a confirmation message.
    *   Example success `POST /api/v1/sales/checkout` response:
        ```json
        {
          "status": "success",
          "message": "Transaction completed successfully.",
          "data": {
            "transaction_id": "txn_12345",
            "grand_total": 33.50,
            "receipt_url": "https://s3.aws.com/receipts/txn_12345.pdf"
          }
        }
        ```
    *   Error responses will follow the RFC 7807 Problem Details standard for machine-readable error information.
    *   Example error response:
        ```json
        {
          "type": "https://example.com/probs/out-of-stock",
          "title": "Product Out of Stock",
          "status": 400,
          "detail": "Product 'prod_abc' is out of stock at location 'store_001'.",
          "instance": "/api/v1/sales/checkout",
          "product_id": "prod_abc",
          "location_id": "store_001"
        }
        ```
-   **Error strategy**:
    *   Standard HTTP status codes will be used:
        *   `2xx` for success (e.g., `200 OK`, `201 Created`, `204 No Content`).
        *   `400 Bad Request`: For invalid request payload or parameters.
        *   `401 Unauthorized`: For unauthenticated requests (missing/invalid JWT).
        *   `403 Forbidden`: For authenticated users lacking necessary permissions (RBAC).
        *   `404 Not Found`: For resources that do not exist.
        *   `409 Conflict`: For resource conflicts (e.g., trying to create a product with an existing SKU).
        *   `422 Unprocessable Entity`: For validation errors where the request is syntactically correct but semantically invalid (e.g., negative quantity).
        *   `5xx` for server-side errors (e.g., `500 Internal Server Error`, `503 Service Unavailable`).
    *   Detailed error information will be provided in the response body using the RFC 7807 Problem Details format.

# External Integrations
-   **Payment gateways**:
    *   **Details**: Integration with a PCI-compliant payment gateway (e.g., Stripe Terminal SDK, Square POS API, Adyen) for credit/debit card processing. The specific gateway will be determined based on the "Open Questions" section. The POS Client will interact with the gateway's SDK for card reader integration, and the POS Core API will handle server-side transaction finalization and token processing.
-   **Email**:
    *   **Details**: SendGrid or Amazon SES for sending digital receipts to customers (if customer email capture is implemented) and for sending administrative alerts (e.g., low stock warnings, critical system errors).
-   **SMS**:
    *   **Details**: Twilio for sending critical alerts to business owners/managers (e.g., high-value refunds, system outages) and for sending transfer confirmation notifications to relevant managers.
-   **Cloud storage**:
    *   **Details**: AWS S3 buckets will be used for storing digital copies of sales receipts (e.g., as PDFs), audit logs, and potentially generated reports. Buckets will be structured by `location_id/year/month/day/receipt_id.pdf`.
-   **Authentication providers**:
    *   **Details**: While internal JWT is primary, for administrative users, future integration with an identity provider like Okta or Auth0 could be considered for Single Sign-On (SSO) capabilities, enhancing security and user management for non-cashier roles.
-   **Third-party APIs**:
    *   **Details**: A tax calculation API (e.g., Avalara, TaxJar) may be integrated if complex, location-specific, or product-specific tax rules are required, as per the "Open Questions" section. This integration would occur within the POS Core API during transaction processing.

# Scalability Strategy
-   **Horizontal scaling**:
    *   The POS Core API will be designed as stateless services, allowing for easy horizontal scaling. This will be achieved by deploying multiple instances behind a load balancer (e.g., using Kubernetes Horizontal Pod Autoscaler or AWS Auto Scaling Groups). The PWA clients are inherently scalable as they run on individual POS terminals.
-   **Vertical scaling**:
    *   The Central Database (PostgreSQL) will be the primary candidate for vertical scaling, especially the writer instance, by upgrading to larger, more powerful machine types (e.g., AWS RDS r6g instances) as transaction volume increases.
-   **Caching**:
    *   Redis will be used as a distributed cache.
    *   **Product Catalog**: Frequently accessed product details (name, price, barcode) will be cached with a moderate TTL (e.g., 24 hours, invalidated on product updates).
    *   **Current Stock Levels**: For high-volume products, current stock levels can be cached for read-heavy operations, with eventual consistency being acceptable for non-critical displays. Critical stock checks during checkout will always hit the database.
    *   **User Sessions**: JWT tokens can be cached for faster validation or blacklisting.
-   **Connection pooling**:
    *   PgBouncer will be deployed as a connection pooler for PostgreSQL. This will efficiently manage database connections, reducing overhead and improving performance by allowing the POS Core API instances to share a smaller pool of persistent database connections.
-   **Read replicas**:
    *   PostgreSQL read replicas will be configured. All reporting queries and non-critical inventory lookup queries will be routed to these replicas, offloading the primary database instance and improving read performance. The POS Core API will distinguish between read-only and write operations.
-   **Rate limiting**:
    *   An API Gateway (or middleware within the POS Core API) will implement rate limiting to protect the backend services from abuse and ensure fair usage. For example, POS client requests could be limited to `X` requests per minute per `location_id` or `user_id`. External integration APIs will also have rate limits applied to prevent overwhelming third-party services.

# Reliability
-   **Retries**:
    *   **External API Calls**: Implement retry policies with exponential backoff for transient failures when interacting with external services (e.g., payment gateways, tax APIs, email/SMS services). A maximum of 3-5 retries with increasing delays (e.g., 1s, 2s, 4s) will be applied.
    *   **Database Operations**: Implement retries for specific database errors like deadlocks or transient connection issues.
    *   **Offline Sync**: The Synchronization Service will implement robust retry mechanisms for failed transaction uploads from offline clients.
-   **Circuit breakers**:
    *   Circuit breakers (e.g., using libraries like Tenacity in Python or Resilience4j in Java) will be applied to external integrations (payment gateway, tax API). If an external service consistently fails or times out, the circuit breaker will "open," preventing further calls to that service for a defined period, allowing it to recover and preventing cascading failures. A fallback mechanism (e.g., manual payment processing, default tax rate) will be provided.
-   **Health checks**:
    *   All backend services will expose `/health/liveness` and `/health/readiness` endpoints.
    *   **Liveness**: Indicates if the application instance is running. If it fails, the instance should be restarted.
    *   **Readiness**: Indicates if the application instance is ready to receive traffic (e.g., database connection established, external dependencies reachable). If it fails, the instance should be removed from the load balancer.
    *   The PWA client will also have internal health checks for IndexedDB and network connectivity.
-   **Timeouts**:
    *   **External API Calls**: Strict timeouts will be enforced for all HTTP requests to external APIs (e.g., 3-5 seconds for payment processing, 2 seconds for tax calculation).
    *   **Database Queries**: Long-running database queries will have configured timeouts to prevent resource exhaustion.
    *   **Internal Service Calls**: Timeouts will be applied to inter-service communication within the modular monolith if using internal HTTP calls or message queues with RPC patterns.
-   **Monitoring**:
    *   Comprehensive monitoring with Prometheus and Grafana will be in place.
    *   **Alerts**: Critical alerts will be configured for:
        *   P99 latency exceeding 500ms for core API endpoints.
        *   Error rates (5xx HTTP status codes) exceeding 1% for any service.
        *   Database connection pool exhaustion or high CPU/memory utilization.
        *   Failed transaction synchronizations from offline clients.
        *   Low stock levels for critical products.
        *   Service downtime or unhealthy instances.
    *   **Telemetry**: Detailed metrics will be collected for request rates, latencies, error counts, resource utilization (CPU, memory, disk I/O), and custom business metrics (e.g., transactions per minute, inventory adjustments).

# Security Considerations
-   **Authentication**:
    *   **JWT**: Secure, short-lived JWT access tokens (e.g., 15-30 minutes expiry) will be used for API authentication. Refresh tokens (longer-lived, securely stored) will be used to obtain new access tokens without re-logging in.
    *   **Password Policy**: Strong password policies will be enforced (minimum length, complexity requirements). Passwords will be hashed using a strong, adaptive hashing algorithm (e.g., bcrypt, Argon2) with a unique salt per user.
    *   **MFA**: Multi-Factor Authentication (MFA) will be a future consideration for administrative roles to enhance login security.
-   **Authorization**:
    *   **Role-Based Access Control (RBAC)**: Implement RBAC based on the defined roles (Cashier, Store Manager, Warehouse Manager, Administrator). Each API endpoint and critical action will have explicit permission checks based on the user's assigned roles.
    *   **Least Privilege**: Users will only be granted the minimum necessary permissions to perform their job functions.
-   **Encryption**:
    *   **Data in Transit**: All communication between the POS Client and POS Core API, and between backend services, will be encrypted using TLS 1.2+ (preferably TLS 1.3) to prevent eavesdropping and tampering.
    *   **Data at Rest**:
        *   The Central Database will utilize Transparent Data Encryption (TDE) or disk-level encryption (e.g., AWS RDS encryption with KMS) for all data.
        *   Sensitive fields within the database (e.g., partial payment card numbers if stored, though full card numbers should not be stored) will be encrypted at the application level using AES-256.
        *   Cloud storage (AWS S3) will use server-side encryption (SSE-S3 or SSE