# Executive Summary
This document outlines the architectural specification for a cloud-based Point of Sale (POS) system designed to manage sales transactions and inventory across a central warehouse and 17 retail stores. The primary goals are to achieve real-time inventory visibility, streamline sales processing, facilitate efficient inventory transfers, ensure robust security, and provide accurate reporting.

The proposed architecture leverages a **Modular Monolith** pattern for the backend, complemented by an **offline-first Progressive Web Application (PWA)** for the POS terminals. This approach balances the need for a unified, maintainable codebase with the critical requirement for operational resilience during network outages at store locations. Key decisions include using a centralized PostgreSQL database for core data, local SQLite for offline PWA data, and JWT-based authentication for secure access. The system is designed for scalability, reliability, and maintainability, addressing performance targets for transaction processing and inventory lookups.

# Architecture Overview
The system employs a hybrid client-server model. Each store's POS terminal will run a Progressive Web Application (PWA) that operates in an offline-first manner, utilizing a local database for immediate transaction processing and inventory lookups. This PWA communicates with a centralized cloud-based backend API. The backend services manage core business logic, synchronize data across all stores and the warehouse, handle inventory transfers, and provide reporting capabilities.

```mermaid
graph TD
    subgraph Store Locations (x17)
        POS_PWA[POS Terminal PWA] -- Sync/API Calls --> Cloud_Backend
        POS_PWA -- Barcode Scanner --> POS_PWA
        POS_PWA -- Receipt Printer --> POS_PWA
        POS_PWA -- Local SQLite DB --> POS_PWA
    end

    subgraph Central Warehouse
        Warehouse_Manager_UI[Warehouse Manager UI] -- API Calls --> Cloud_Backend
    end

    subgraph Cloud Backend
        Cloud_Backend[POS Core API Services]
        Cloud_Backend -- Reads/Writes --> Central_Postgres_DB[Central PostgreSQL Database]
        Cloud_Backend -- Caches --> Redis_Cache[Redis Cache]
        Cloud_Backend -- Async Events --> Message_Broker[Message Broker]
        Cloud_Backend -- Stores Files --> Cloud_Storage[Cloud Storage]
        Cloud_Backend -- Monitors --> Monitoring_System[Monitoring System]
        Cloud_Backend -- Logs --> Logging_System[Logging System]
        Cloud_Backend -- Auth --> Auth_Service[Authentication Service]
    end

    Admin_UI[Administrator UI] -- API Calls --> Cloud_Backend
    Reporting_Tool[Reporting Dashboard] -- Reads --> Central_Postgres_DB
```

# Architecture Pattern
**Modular Monolith**.
This pattern is chosen for the POS system due to several compelling reasons:
1.  **Domain Complexity**: The system involves distinct but interconnected domains (Sales, Inventory, Product Management, User Management, Reporting). A modular monolith allows for clear separation of these concerns into independent modules within a single codebase, promoting better organization and maintainability than a traditional monolithic application.
2.  **Deployment Simplicity & Cost-Effectiveness**: With 1 central warehouse and 17 stores, a single, well-structured deployment unit for the backend reduces operational overhead, infrastructure costs, and complexity compared to a full microservices architecture, especially in the initial phases.
3.  **Offline-First Requirement**: The critical need for offline sales transaction processing is best addressed by a robust PWA client. The modular monolith backend provides a stable, unified API endpoint for this client to synchronize with, simplifying data consistency challenges.
4.  **Future Scalability**: The modular design ensures that if specific modules (e.g., Inventory, Sales) experience disproportionate load or require independent scaling in the future, they can be extracted into separate microservices with reduced refactoring effort. This provides a clear path for evolutionary architecture.
5.  **Team Size & Development Speed**: For a project of this scope, a modular monolith can accelerate initial development by avoiding the distributed system complexities inherent in microservices, allowing the team to focus on business value.

The modules will include: Sales, Inventory, Product Catalog, User & Auth, Reporting, and Transfers. Each module will have its own bounded context, API interfaces, and potentially dedicated database tables, even if residing within the same physical database.

# System Components
1.  **POS Terminal PWA (Progressive Web Application)**:
    *   **Responsibility**: Frontend application running on store cash registers. Handles sales transactions, barcode scanning, receipt printing, offline mode operations, and local inventory lookups. Synchronizes data with the central backend when online.
    *   **Interaction**: Communicates with the POS Core API for online operations and data synchronization. Stores data locally in an embedded database.
2.  **POS Core API Services (Backend)**:
    *   **Responsibility**: Centralized backend application hosting the core business logic for Sales, Inventory, Product Management, User & Role Management, and Inventory Transfers. Provides RESTful APIs for the PWA and administrative UIs. Orchestrates data persistence and asynchronous operations.
    *   **Interaction**: Interacts with the Central PostgreSQL Database, Redis Cache, Message Broker, and Cloud Storage.
3.  **Central PostgreSQL Database**:
    *   **Responsibility**: Primary relational data store for all persistent data, including products, inventory levels (central and per-store), transactions, users, roles, and audit logs. Ensures ACID compliance for critical operations.
    *   **Interaction**: Accessed by the POS Core API Services.
4.  **Local SQLite Database (Embedded in PWA)**:
    *   **Responsibility**: Embedded database within each POS PWA instance. Stores a subset of critical data (products, local inventory, pending transactions) to enable offline operations. Manages data synchronization with the Central PostgreSQL Database via the POS Core API.
    *   **Interaction**: Accessed directly by the POS PWA.
5.  **Authentication Service (Part of POS Core API)**:
    *   **Responsibility**: Manages user authentication (login, logout) and token issuance (JWT). Validates user credentials and provides identity information for authorization.
    *   **Interaction**: Integrated within the POS Core API, used by PWA and administrative UIs.
6.  **Reporting Service (Part of POS Core API or dedicated module)**:
    *   **Responsibility**: Generates various sales, inventory, and transfer reports based on data from the Central PostgreSQL Database. May process data asynchronously for complex reports.
    *   **Interaction**: Queries the Central PostgreSQL Database, potentially uses the Message Broker for asynchronous report generation.
7.  **Administrative & Warehouse Manager UIs**:
    *   **Responsibility**: Web-based interfaces for administrators (user/role management, product catalog) and warehouse managers (inventory transfer approval, manual adjustments).
    *   **Interaction**: Communicates with the POS Core API Services.

# Technology Stack
-   **Frontend**:
    *   **Selected technologies**: React, TypeScript, Tailwind CSS, Workbox (for PWA service worker).
    *   **Rationale**: React provides a robust component-based UI framework for building complex, interactive interfaces. TypeScript enhances code quality and maintainability. Tailwind CSS offers a utility-first approach for rapid and consistent styling. Workbox is a set of libraries that make it easier to implement service workers for offline capabilities, caching strategies, and background sync, which is critical for the PWA's offline mode.
-   **Backend**:
    *   **Selected technologies**: Python 3.12, FastAPI, SQLAlchemy, Pydantic.
    *   **Rationale**: Python with FastAPI offers high performance (comparable to Node.js and Go for I/O-bound tasks), excellent developer experience, and strong type hinting. FastAPI's automatic OpenAPI/Swagger documentation is a significant advantage for API design and consumption. SQLAlchemy provides a powerful ORM for database interactions, and Pydantic ensures robust data validation for API requests and responses.
-   **Database**:
    *   **Selected technologies**: PostgreSQL (Central), SQLite (Local PWA).
    *   **Rationale**: PostgreSQL is a highly reliable, feature-rich, and ACID-compliant relational database, ideal for critical transactional data like sales and inventory. Its extensibility and strong community support make it a solid choice for the central backend. SQLite is a lightweight, serverless, and embedded database perfectly suited for the PWA's local storage needs, enabling robust offline functionality.
-   **Caching**:
    *   **Selected technologies**: Redis.
    *   **Rationale**: Redis is an in-memory data store known for its high performance and versatility. It will be used for caching frequently accessed data (e.g., product catalog details, hot inventory levels for quick lookups, user sessions) to reduce database load and improve response times for performance-critical operations like barcode scanning and inventory lookups.
-   **Messaging**:
    *   **Selected technologies**: RabbitMQ.
    *   **Rationale**: RabbitMQ is a mature and reliable message broker that supports various messaging patterns. It will be used for asynchronous communication between backend modules, particularly for inventory transfer notifications, background report generation, and ensuring eventual consistency for data synchronization between the PWA and the central backend.
-   **Authentication**:
    *   **Selected technologies**: JWT (JSON Web Tokens) with OAuth2 flow.
    *   **Rationale**: JWTs provide a stateless, secure, and scalable mechanism for user authentication and authorization. OAuth2 defines a standard framework for delegated authorization, ensuring secure access to resources. This combination allows for robust authentication across the PWA and administrative UIs, with tokens managed securely.
-   **Storage**:
    *   **Selected technologies**: AWS S3 (or equivalent cloud object storage like Azure Blob Storage/GCS).
    *   **Rationale**: Cloud object storage offers highly durable, scalable, and cost-effective storage for unstructured data. It will be used for storing digital copies of receipts, audit logs, and potentially exported reports, ensuring data availability and integrity.
-   **Monitoring**:
    *   **Selected technologies**: Prometheus, Grafana.
    *   **Rationale**: Prometheus is a powerful open-source monitoring system with a flexible data model and query language (PromQL). Grafana provides excellent visualization capabilities for Prometheus metrics, allowing for comprehensive dashboards and alerts on system performance, availability, and resource utilization.
-   **Logging**:
    *   **Selected technologies**: ELK Stack (Elasticsearch, Logstash, Kibana).
    *   **Rationale**: The ELK stack provides a centralized, scalable solution for collecting, processing, storing, and analyzing logs from all system components. Structured JSON logging will be implemented to facilitate easy searching, filtering, and visualization of logs, crucial for debugging, auditing, and security analysis.

# Database Design
-   **Entities**:
    *   **User**: `user_id (PK)`, `username (UNIQUE)`, `password_hash`, `email`, `first_name`, `last_name`, `role_id (FK)`, `store_id (FK, NULLABLE for Warehouse/Admin)`, `is_active`, `created_at`, `updated_at`.
    *   **Role**: `role_id (PK)`, `role_name (UNIQUE, e.g., 'Cashier', 'Store Manager', 'Warehouse Manager', 'Administrator')`, `permissions (JSONB or separate table)`.
    *   **Store**: `store_id (PK)`, `store_name (UNIQUE)`, `address`, `city`, `state`, `zip_code`, `phone_number`, `tax_rate`.
    *   **Warehouse**: `warehouse_id (PK)`, `warehouse_name (UNIQUE)`, `address`, `city`, `state`, `zip_code`, `phone_number`. (Could be a special 'store' type or separate entity).
    *   **Product**: `product_id (PK)`, `sku (UNIQUE)`, `name`, `description`, `price`, `barcode (UNIQUE)`, `category_id (FK)`, `is_active`, `created_at`, `updated_at`.
    *   **Category**: `category_id (PK)`, `category_name (UNIQUE)`.
    *   **Inventory**: `inventory_id (PK)`, `product_id (FK)`, `location_id (FK, polymorphic for Store/Warehouse)`, `location_type (ENUM 'STORE', 'WAREHOUSE')`, `quantity`, `last_adjusted_at`, `min_stock_level`.
    *   **Transaction**: `transaction_id (PK)`, `store_id (FK)`, `user_id (FK, cashier)`, `transaction_date`, `total_amount`, `tax_amount`, `discount_amount`, `payment_method`, `status (ENUM 'COMPLETED', 'VOIDED', 'REFUNDED')`, `receipt_url (S3)`, `created_at`, `updated_at`.
    *   **TransactionItem**: `transaction_item_id (PK)`, `transaction_id (FK)`, `product_id (FK)`, `quantity`, `unit_price`, `line_total`, `discount_applied`.
    *   **Payment**: `payment_id (PK)`, `transaction_id (FK)`, `amount`, `method`, `status`, `external_transaction_id`, `created_at`.
    *   **StockAdjustment**: `adjustment_id (PK)`, `product_id (FK)`, `location_id (FK)`, `location_type`, `old_quantity`, `new_quantity`, `reason`, `adjusted_by_user_id (FK)`, `adjustment_date`, `audit_log (JSONB)`.
    *   **TransferRequest**: `transfer_id (PK)`, `product_id (FK)`, `requested_quantity`, `sending_location_id (FK)`, `sending_location_type`, `receiving_location_id (FK)`, `receiving_location_type`, `requested_by_user_id (FK)`, `request_date`, `status (ENUM 'PENDING', 'APPROVED', 'REJECTED', 'COMPLETED')`, `approved_by_user_id (FK, NULLABLE)`, `approval_date (NULLABLE)`, `completion_date (NULLABLE)`.
    *   **AuditLog**: `log_id (PK)`, `entity_type`, `entity_id`, `operation_type (ENUM 'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'REFUND', 'VOID', 'ADJUST')`, `user_id (FK)`, `timestamp`, `details (JSONB, old/new values)`.

-   **Relationships**:
    *   `User` (1) -> (*) `Transaction` (Cashier performs transactions).
    *   `User` (1) -> (*) `StockAdjustment` (User performs adjustments).
    *   `User` (1) -> (*) `TransferRequest` (User initiates/approves transfers).
    *   `Role` (1) -> (*) `User` (Users have roles).
    *   `Store` (1) -> (*) `User` (Users are assigned to a store, or NULL for warehouse/admin).
    *   `Store` (1) -> (*) `Transaction` (Transactions occur at a store).
    *   `Product` (1) -> (*) `Inventory` (Products have inventory at locations).
    *   `Product` (1) -> (*) `TransactionItem` (Products are part of transactions).
    *   `Product` (1) -> (*) `StockAdjustment` (Adjustments are for products).
    *   `Product` (1) -> (*) `TransferRequest` (Transfers are for products).
    *   `Category` (1) -> (*) `Product` (Products belong to categories).
    *   `Transaction` (1) -> (*) `TransactionItem` (Transactions have multiple items).
    *   `Transaction` (1) -> (*) `Payment` (Transactions can have multiple payments).
    *   `Inventory` is a polymorphic relationship to `Store` or `Warehouse` via `location_id` and `location_type`.
    *   `TransferRequest` has `sending_location_id` and `receiving_location_id` which are polymorphic to `Store` or `Warehouse`.

-   **Indexes**:
    *   `Product`: `sku` (B-tree, UNIQUE), `barcode` (B-tree, UNIQUE), `category_id`.
    *   `Inventory`: Composite index on `(product_id, location_id, location_type)` for fast inventory lookups.
    *   `Transaction`: `transaction_date`, `store_id`, `user_id`.
    *   `TransactionItem`: `transaction_id`, `product_id`.
    *   `User`: `username` (B-tree, UNIQUE), `role_id`, `store_id`.
    *   `TransferRequest`: `request_date`, `status`, `sending_location_id`, `receiving_location_id`.
    *   `AuditLog`: `timestamp`, `entity_type`, `entity_id`.

-   **Constraints**:
    *   **Uniqueness**: `username`, `sku`, `barcode`, `store_name`, `warehouse_name`, `role_name`, `category_name` must be unique.
    *   **Foreign Keys**: All `(FK)` relationships must enforce referential integrity.
    *   **Non-negative Inventory**: `Inventory.quantity` must be `>= 0` by default. For back-ordering, a specific flag or separate mechanism will allow negative values only with `Store Manager` approval, tracked in `StockAdjustment`.
    *   **Data Type Constraints**: Ensure appropriate data types (e.g., `DECIMAL(10,2)` for monetary values, `TEXT` for descriptions, `BOOLEAN` for active flags).
    *   **Enum Constraints**: `Transaction.status`, `Inventory.location_type`, `TransferRequest.status`, `AuditLog.operation_type` must be restricted to predefined enum values.
    *   **Audit Trail Immutability**: `AuditLog` table should be append-only, with no updates or deletes allowed.
    *   **Product SKU Format**: `Product.sku` should conform to a defined regex pattern (e.g., alphanumeric, specific length).

# API Design
The API will be RESTful, using JSON for request and response bodies, and standard HTTP methods and status codes.

-   **Major REST endpoints**:
    *   **Authentication & User Management**:
        *   `POST /api/v1/auth/login`: Authenticate user credentials and return JWT.
        *   `POST /api/v1/auth/refresh`: Refresh an expired JWT using a refresh token.
        *   `GET /api/v1/users`: Get list of users (Admin only).
        *   `POST /api/v1/users`: Create a new user (Admin only).
        *   `PUT /api/v1/users/{id}`: Update user details (Admin only).
        *   `GET /api/v1/roles`: Get list of available roles (Admin only).
    *   **Product Management**:
        *   `GET /api/v1/products`: Retrieve a list of products, with optional filters (category, active status).
        *   `GET /api/v1/products/scan?barcode={code}`: Resolve product details by barcode for quick scanning.
        *   `GET /api/v1/products/{id}`: Retrieve details for a specific product.
        *   `POST /api/v1/products`: Create a new product (Admin/Warehouse Manager).
        *   `PUT /api/v1/products/{id}`: Update product details (Admin/Warehouse Manager).
        *   `DELETE /api/v1/products/{id}`: Deactivate a product (Admin/Warehouse Manager).
    *   **Sales Transactions**:
        *   `POST /api/v1/sales/checkout`: Process a new sales transaction.
        *   `POST /api/v1/sales/{transaction_id}/void`: Void a transaction (Manager approval required).
        *   `POST /api/v1/sales/{transaction_id}/refund`: Initiate a refund for a transaction (Manager approval required).
        *   `GET /api/v1/sales/{transaction_id}/receipt`: Retrieve digital receipt details.
    *   **Inventory Management**:
        *   `GET /api/v1/inventory?location_id={id}&location_type={type}`: Get current inventory levels for a location.
        *   `POST /api/v1/inventory/adjust`: Manually adjust inventory levels (Manager approval required).
        *   `POST /api/v1/transfers/request`: Initiate an inventory transfer request (Store Manager).
        *   `GET /api/v1/transfers/requests?status={status}`: List transfer requests (Warehouse/Store Manager).
        *   `PUT /api/v1/transfers/{transfer_id}/approve`: Approve an inventory transfer request (Warehouse Manager).
        *   `PUT /api/v1/transfers/{transfer_id}/reject`: Reject an inventory transfer request (Warehouse Manager).
        *   `PUT /api/v1/transfers/{transfer_id}/complete`: Mark transfer as completed (Receiving Store Manager).
    *   **Reporting**:
        *   `GET /api/v1/reports/sales?store_id={id}&start_date={date}&end_date={date}`: Generate sales report.
        *   `GET /api/v1/reports/inventory?location_id={id}`: Generate inventory report.
        *   `GET /api/v1/reports/transfers?status={status}`: Generate inventory transfer report.

-   **Authentication flow**:
    *   Users authenticate by sending `username` and `password` to `POST /api/v1/auth/login`.
    *   Upon successful authentication, the API returns a short-lived **Access Token (JWT)** and a longer-lived **Refresh Token (JWT)**.
    *   The Access Token is included in the `Authorization` header of subsequent requests as `Bearer <access_token>`.
    *   When the Access Token expires, the client uses the Refresh Token to obtain a new Access Token from `POST /api/v1/auth/refresh` without requiring re-authentication.
    *   Tokens will be stored securely (e.g., HTTP-only cookies or in-memory for PWA, with appropriate security measures).

-   **Request structure**:
    *   All requests will use JSON payloads.
    *   Example `POST /api/v1/sales/checkout` request:
        ```json
        {
          "store_id": "uuid-of-store",
          "cashier_id": "uuid-of-cashier",
          "items": [
            {"product_id": "uuid-of-product-1", "quantity": 2, "discount_percentage": 0},
            {"product_id": "uuid-of-product-2", "quantity": 1, "discount_percentage": 10}
          ],
          "payment_method": "CREDIT_CARD",
          "payment_details": {
            "card_type": "VISA",
            "last_four_digits": "1234",
            "transaction_ref": "external-payment-gateway-id"
          },
          "manager_approval_code": "optional-for-discounts-or-voids"
        }
        ```

-   **Response structure**:
    *   Successful responses will return a JSON object with the requested data and a `2xx` HTTP status code.
    *   Example successful `POST /api/v1/sales/checkout` response:
        ```json
        {
          "status": "success",
          "message": "Transaction completed successfully.",
          "data": {
            "transaction_id": "uuid-of-new-transaction",
            "store_id": "uuid-of-store",
            "total_amount": 123.45,
            "receipt_url": "https://s3.aws.com/receipts/uuid-of-new-transaction.pdf",
            "inventory_updates": [
              {"product_id": "uuid-of-product-1", "new_quantity": 98},
              {"product_id": "uuid-of-product-2", "new_quantity": 49}
            ]
          }
        }
        ```
    *   Error responses will follow the RFC 7807 (Problem Details for HTTP APIs) standard for consistency.

-   **Error strategy**:
    *   **HTTP Status Codes**: Standard HTTP status codes will be used to indicate the general nature of the error (e.g., `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity` for validation errors, `500 Internal Server Error`).
    *   **Problem Details (RFC 7807)**: Error responses will include a JSON body with the following fields:
        *   `type`: A URI that identifies the problem type (e.g., "https://example.com/probs/out-of-stock").
        *   `title`: A short, human-readable summary of the problem type.
        *   `status`: The HTTP status code generated by the origin server.
        *   `detail`: A human-readable explanation specific to this occurrence of the problem.
        *   `instance`: A URI that identifies the specific occurrence of the problem.
        *   `errors`: (Optional) A detailed list of validation errors for `422` responses, specifying field and message.
    *   **Example Error Response (Out of Stock)**:
        ```json
        {
          "type": "https://example.com/probs/out-of-stock",
          "title": "Insufficient Stock",
          "status": 400,
          "detail": "Product 'SKU123' (Product A) has only 5 units available, but 10 were requested.",
          "instance": "/api/v1/sales/checkout",
          "product_id": "uuid-of-product-1",
          "available_quantity": 5,
          "requested_quantity": 10
        }
        ```
    *   **Example Error Response (Validation Error)**:
        ```json
        {
          "type": "https://example.com/probs/validation-error",
          "title": "Request Validation Failed",
          "status": 422,
          "detail": "One or more fields in the request payload are invalid.",
          "instance": "/api/v1/products",
          "errors": [
            {"field": "price", "message": "Price must be a positive number."},
            {"field": "sku", "message": "SKU format is invalid."}
          ]
        }
        ```

# External Integrations
-   **Payment gateways**:
    *   **Details**: Integration with a PCI-compliant payment gateway (e.g., Stripe Terminal SDK, Square POS API, Adyen) for processing credit/debit card payments. The specific gateway will be determined based on the "Open Questions" section. The integration will involve client-side SDKs for physical card readers and server-side API calls for transaction authorization and capture.
-   **Email**:
    *   **Details**: Transactional email service (e.g., SendGrid, Amazon SES) for sending digital receipts to customers (if requested) and for sending critical alerts to managers (e.g., low stock warnings, failed transfers).
-   **SMS**:
    *   **Details**: SMS gateway (e.g., Twilio) for sending critical, time-sensitive notifications to business owners or managers (e.g., system outages, high-value transaction alerts, daily sales summaries).
-   **Cloud storage**:
    *   **Details**: AWS S3 (or equivalent) will be used for storing digital copies of receipts, audit logs, and potentially large report exports. Receipts will be stored with appropriate access controls and retention policies.
-   **Authentication providers**:
    *   **Details**: Initially, an internal user management system will be used. Future consideration for integration with an external Identity Provider (IdP) like Okta or Auth0 for administrative users to support Single Sign-On (SSO) and enhanced security features.
-   **Third-party APIs**:
    *   **Details**: Integration with a tax rate API (e.g., Avalara, TaxJar) to ensure accurate sales tax calculation based on the store's geographical location and product categories, complying with local and national tax regulations.

# Scalability Strategy
-   **Horizontal scaling**:
    *   **Strategy**: The POS Core API Services will be designed as stateless microservices (within the modular monolith context) that can be deployed across multiple instances. This allows for horizontal scaling by adding more instances behind a load balancer. Containerization (Docker) and orchestration (Kubernetes) will facilitate dynamic scaling based on CPU utilization, memory, or request queue depth.
    *   **Application**: The PWA itself scales by being deployed to each terminal; its local processing offloads the backend.
-   **Vertical scaling**:
    *   **Strategy**: For components that are difficult to scale horizontally (e.g., the primary database writer instance), vertical scaling (upgrading to more powerful hardware, more CPU/RAM) will be employed as needed. This is a short-to-medium term strategy before sharding or more complex database scaling is considered.
-   **Caching**:
    *   **Detailed caching layer layout**:
        *   **Client-side (PWA)**: Service Worker caching (Workbox) for static assets (JS, CSS, images) and API responses for product catalog, local inventory, and pending transactions. This ensures fast load times and offline access.
        *   **Server-side (Redis)**:
            *   **Product Catalog**: Cache frequently accessed product details (SKU, name, price, barcode) with a moderate TTL (e.g., 24 hours, invalidated on product updates).
            *   **Hot Inventory Levels**: Cache current inventory levels for high-volume products at specific stores with a short TTL (e.g., 5-10 minutes) or event-driven invalidation to reduce database reads during peak sales.
            *   **User Sessions**: Store JWT refresh tokens and session data for faster authentication.
            *   **Reporting Data**: Cache results of complex or frequently requested reports for a defined period (e.g., hourly sales summaries).
-   **Connection pooling**:
    *   **Database connection pool limits**: PgBouncer will be deployed as a connection pooler for PostgreSQL. This will manage and optimize database connections, reducing overhead on the database server and improving application performance by reusing connections. Connection limits will be configured based on expected peak concurrent users and database capacity, typically allowing for a higher number of application connections than direct database connections.
-   **Read replicas**:
    *   **Database read/write segregation plan**: PostgreSQL read replicas will be utilized to offload read-heavy operations from the primary database instance. Specifically, all reporting queries and non-critical inventory lookups (where slight eventual consistency is acceptable) will be routed to read replicas. The primary database will handle all write operations (sales transactions, inventory adjustments, transfers) to ensure strong consistency.
-   **Rate limiting**:
    *   **API traffic control rules**: An API Gateway or application-level rate limiting will be implemented to protect the backend services from abuse and ensure fair usage.
        *   **POS Terminal Requests**: Limit sales transaction and inventory lookup requests per terminal to prevent excessive load (e.g., 100 requests per minute per IP/terminal ID).
        *   **Admin/Manager APIs**: Stricter limits for sensitive operations like user creation or bulk inventory adjustments.
        *   **External Integrations**: Apply rate limits when interacting with third-party APIs (e.g., payment gateways, tax APIs) to comply with their usage policies.

# Reliability
-   **Retries**:
    *   **Retry policies with exponential backoff**: Implement retry mechanisms with exponential backoff for transient failures when interacting with external services (e.g., payment gateways, email/SMS services, tax APIs) and for certain database operations (e.