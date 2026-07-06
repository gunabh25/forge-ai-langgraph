# Executive Summary
This Backend Blueprint details the design and implementation plan for a cloud-based Point of Sale (POS) system, supporting a central warehouse and 17 retail stores. Built upon a **Modular Monolith** architecture using Python with FastAPI, SQLAlchemy, and PostgreSQL, the system aims to provide real-time inventory visibility, streamline sales transactions, facilitate efficient inventory transfers, and ensure robust security. Key features include an offline-first PWA client synchronization, JWT-based authentication, role-based access control, and comprehensive reporting. The design prioritizes performance, scalability, and maintainability, leveraging Redis for caching, RabbitMQ for asynchronous processing, and the ELK stack for centralized logging and monitoring.

# Folder Structure
```
src/
├── main.py                     # FastAPI application entry point
├── config/
│   ├── settings.py             # Pydantic BaseSettings for environment variables
│   └── database.py             # Database connection and session management
├── core/
│   ├── security.py             # JWT token generation, hashing, and verification utilities
│   ├── exceptions.py           # Custom exception definitions and handlers
│   └── constants.py            # Global constants (e.g., role names, status enums)
├── api/
│   ├── v1/                     # API versioning
│   │   ├── auth/
│   │   │   └── router.py       # Authentication routes
│   │   ├── products/
│   │   │   └── router.py       # Product management routes
│   │   ├── sales/
│   │   │   └── router.py       # Sales transaction routes
│   │   ├── inventory/
│   │   │   └── router.py       # Inventory management routes
│   │   ├── transfers/
│   │   │   └── router.py       # Inventory transfer routes
│   │   ├── users/
│   │   │   └── router.py       # User management routes
│   │   └── reports/
│   │       └── router.py       # Reporting routes
│   └── middleware/
│       ├── auth_middleware.py  # JWT authentication and user context loading
│       ├── rbac_middleware.py  # Role-based access control checks
│       ├── logging_middleware.py # Request logging and correlation ID generation
│       ├── error_middleware.py # Global exception handling
│       └── rate_limit_middleware.py # API rate limiting
├── modules/                    # Modular Monolith domain modules
│   ├── auth/
│   │   ├── service.py
│   │   └── repository.py
│   ├── products/
│   │   ├── service.py
│   │   └── repository.py
│   ├── sales/
│   │   ├── service.py
│   │   └── repository.py
│   ├── inventory/
│   │   ├── service.py
│   │   └── repository.py
│   ├── transfers/
│   │   ├── service.py
│   │   └── repository.py
│   ├── users/
│   │   ├── service.py
│   │   └── repository.py
│   └── reports/
│       ├── service.py
│       └── repository.py
├── models/                     # SQLAlchemy ORM models (database schemas)
│   ├── base.py                 # Base declarative model
│   ├── user.py
│   ├── product.py
│   ├── inventory.py
│   ├── transaction.py
│   ├── transfer.py
│   ├── audit.py
│   └── common.py               # Enums, utility models
├── schemas/                    # Pydantic schemas for DTOs (request/response validation)
│   ├── auth.py
│   ├── product.py
│   ├── sales.py
│   ├── inventory.py
│   ├── transfer.py
│   ├── user.py
│   ├── report.py
│   └── common.py               # Common DTOs (e.g., pagination, error response)
├── services/                   # Cross-cutting concerns or shared services
│   ├── cache_service.py        # Redis caching operations
│   ├── message_broker_service.py # RabbitMQ publishing/subscribing
│   ├── storage_service.py      # AWS S3 integration
│   ├── payment_gateway_service.py # Payment gateway integration
│   ├── tax_service.py          # Tax calculation API integration
│   └── email_sms_service.py    # Email/SMS notification service
├── tasks/                      # Celery/background job definitions
│   ├── __init__.py
│   └── report_tasks.py
├── tests/                      # Unit and integration tests
│   ├── unit/
│   └── integration/
└── Dockerfile                  # Docker build instructions
```

# Module Breakdown
-   **AuthModule**: Manages user authentication, token issuance (JWT), password hashing, and user session management.
-   **UserModule**: Handles CRUD operations for user accounts and role assignments.
-   **ProductModule**: Manages the product catalog, including creation, modification, deactivation, and barcode lookup.
-   **InventoryModule**: Tracks current inventory levels across all locations, supports manual adjustments, and manages stock level alerts.
-   **SalesModule**: Processes sales transactions, calculates totals, handles various payment methods, voids, and refunds, and updates inventory.
-   **TransferModule**: Manages the lifecycle of inventory transfer requests, including initiation, approval, rejection, and completion, updating inventory at sending and receiving locations.
-   **ReportModule**: Generates various sales, inventory, and transfer reports, potentially leveraging asynchronous processing for complex queries.
-   **CoreModule**: Provides cross-cutting concerns like security utilities, custom exceptions, and global constants.

# Controllers
-   **AuthController**:
    -   `login(credentials: AuthLoginRequest) -> AuthTokenResponse`: Authenticates user and returns JWT access and refresh tokens.
    -   `refresh_token(refresh_token: str) -> AuthTokenResponse`: Issues a new access token using a valid refresh token.
-   **ProductController**:
    -   `get_products(filters: ProductFilterParams) -> List[ProductResponse]`: Retrieves a list of products based on filters.
    -   `get_product_by_barcode(barcode: str) -> ProductResponse`: Resolves product details by barcode.
    -   `get_product_by_id(product_id: UUID) -> ProductResponse`: Retrieves details for a specific product.
    -   `create_product(product_data: ProductCreateRequest) -> ProductResponse`: Creates a new product.
    -   `update_product(product_id: UUID, product_data: ProductUpdateRequest) -> ProductResponse`: Updates product details.
    -   `deactivate_product(product_id: UUID) -> MessageResponse`: Deactivates a product.
-   **SalesController**:
    -   `checkout(transaction_data: SalesCheckoutRequest) -> SalesCheckoutResponse`: Processes a new sales transaction.
    -   `void_transaction(transaction_id: UUID, approval: ManagerApprovalRequest) -> MessageResponse`: Voids a transaction (requires manager approval).
    -   `refund_transaction(transaction_id: UUID, refund_data: SalesRefundRequest) -> MessageResponse`: Initiates a refund (requires manager approval).
    -   `get_receipt(transaction_id: UUID) -> ReceiptResponse`: Retrieves digital receipt details.
-   **InventoryController**:
    -   `get_inventory_levels(location_id: UUID, location_type: LocationType) -> List[InventoryResponse]`: Retrieves current inventory levels for a given location.
    -   `adjust_inventory(adjustment_data: InventoryAdjustmentRequest) -> MessageResponse`: Manually adjusts inventory levels (requires manager approval).
-   **TransferController**:
    -   `request_transfer(transfer_data: TransferRequestCreate) -> TransferRequestResponse`: Initiates an inventory transfer request.
    -   `list_transfer_requests(status: TransferStatus, location_id: UUID) -> List[TransferRequestResponse]`: Lists transfer requests based on status and location.
    -   `approve_transfer(transfer_id: UUID, approval: ManagerApprovalRequest) -> MessageResponse`: Approves a transfer request.
    -   `reject_transfer(transfer_id: UUID, reason: str) -> MessageResponse`: Rejects a transfer request.
    -   `complete_transfer(transfer_id: UUID, completion_data: TransferCompletionRequest) -> MessageResponse`: Marks a transfer as completed by the receiving location.
-   **UserController**:
    -   `get_users(filters: UserFilterParams) -> List[UserResponse]`: Retrieves a list of users.
    -   `create_user(user_data: UserCreateRequest) -> UserResponse`: Creates a new user.
    -   `update_user(user_id: UUID, user_data: UserUpdateRequest) -> UserResponse`: Updates user details.
    -   `deactivate_user(user_id: UUID) -> MessageResponse`: Deactivates a user.
    -   `get_roles() -> List[RoleResponse]`: Retrieves a list of available roles.
-   **ReportController**:
    -   `generate_sales_report(params: SalesReportRequest) -> ReportGenerationResponse`: Triggers generation of a sales report.
    -   `generate_inventory_report(params: InventoryReportRequest) -> ReportGenerationResponse`: Triggers generation of an inventory report.
    -   `generate_transfer_report(params: TransferReportRequest) -> ReportGenerationResponse`: Triggers generation of an inventory transfer report.
    -   `get_report_status(report_id: UUID) -> ReportStatusResponse`: Checks the status of a generated report.

# Routes
All routes are prefixed with `/api/v1`.

-   **Authentication & User Management**:
    -   `POST /auth/login` -> `AuthController.login` (Public)
    -   `POST /auth/refresh` -> `AuthController.refresh_token` (Public, requires refresh token)
    -   `GET /users` -> `UserController.get_users` (Admin)
    -   `POST /users` -> `UserController.create_user` (Admin)
    -   `PUT /users/{id}` -> `UserController.update_user` (Admin)
    -   `DELETE /users/{id}` -> `UserController.deactivate_user` (Admin)
    -   `GET /roles` -> `UserController.get_roles` (Admin)
-   **Product Management**:
    -   `GET /products` -> `ProductController.get_products` (All authenticated users)
    -   `GET /products/scan` -> `ProductController.get_product_by_barcode` (Cashier, Manager)
    -   `GET /products/{id}` -> `ProductController.get_product_by_id` (All authenticated users)
    -   `POST /products` -> `ProductController.create_product` (Admin, Warehouse Manager)
    -   `PUT /products/{id}` -> `ProductController.update_product` (Admin, Warehouse Manager)
    -   `DELETE /products/{id}` -> `ProductController.deactivate_product` (Admin, Warehouse Manager)
-   **Sales Transactions**:
    -   `POST /sales/checkout` -> `SalesController.checkout` (Cashier, Store Manager)
    -   `POST /sales/{transaction_id}/void` -> `SalesController.void_transaction` (Store Manager, Admin)
    -   `POST /sales/{transaction_id}/refund` -> `SalesController.refund_transaction` (Store Manager, Admin)
    -   `GET /sales/{transaction_id}/receipt` -> `SalesController.get_receipt` (Cashier, Store Manager, Admin)
-   **Inventory Management**:
    -   `GET /inventory` -> `InventoryController.get_inventory_levels` (All authenticated users)
    -   `POST /inventory/adjust` -> `InventoryController.adjust_inventory` (Store Manager, Warehouse Manager, Admin)
-   **Inventory Transfers**:
    -   `POST /transfers/request` -> `TransferController.request_transfer` (Store Manager, Warehouse Manager)
    -   `GET /transfers/requests` -> `TransferController.list_transfer_requests` (Store Manager, Warehouse Manager, Admin)
    -   `PUT /transfers/{transfer_id}/approve` -> `TransferController.approve_transfer` (Warehouse Manager, Admin)
    -   `PUT /transfers/{transfer_id}/reject` -> `TransferController.reject_transfer` (Warehouse Manager, Admin)
    -   `PUT /transfers/{transfer_id}/complete` -> `TransferController.complete_transfer` (Receiving Store Manager, Admin)
-   **Reporting**:
    -   `GET /reports/sales` -> `ReportController.generate_sales_report` (Store Manager, Admin)
    -   `GET /reports/inventory` -> `ReportController.generate_inventory_report` (Store Manager, Warehouse Manager, Admin)
    -   `GET /reports/transfers` -> `ReportController.generate_transfer_report` (Store Manager, Warehouse Manager, Admin)
    -   `GET /reports/{report_id}/status` -> `ReportController.get_report_status` (Store Manager, Admin)

# Services
-   **AuthService**:
    -   `authenticate_user(username, password) -> User`: Verifies credentials, returns user if valid.
    -   `create_access_token(user_id, role_id, store_id) -> str`: Generates JWT access token.
    -   `create_refresh_token(user_id) -> str`: Generates JWT refresh token.
    -   `verify_token(token) -> TokenPayload`: Decodes and validates JWT.
    -   `hash_password(password) -> str`: Hashes a plain-text password.
    -   `verify_password(plain_password, hashed_password) -> bool`: Verifies a password against its hash.
-   **ProductService**:
    -   `get_products(filters) -> List[Product]`: Retrieves products with optional filtering.
    -   `get_product_by_barcode(barcode) -> Product`: Fetches product by barcode, uses Redis cache.
    -   `get_product_by_id(product_id) -> Product`: Fetches product by ID, uses Redis cache.
    -   `create_product(data) -> Product`: Creates a new product, invalidates cache.
    -   `update_product(product_id, data) -> Product`: Updates product, invalidates cache.
    -   `deactivate_product(product_id) -> None`: Marks product as inactive, invalidates cache.
-   **SalesService**:
    -   `process_checkout(store_id, cashier_id, items, payment_method, payment_details, manager_approval_code) -> Transaction`:
        -   Starts DB transaction.
        -   Validates item availability and discounts.
        -   Calculates total, tax, discount.
        -   Processes payment via `PaymentGatewayService`.
        -   Decrements inventory levels via `InventoryService`.
        -   Creates `Transaction` and `TransactionItem` records.
        -   Generates digital receipt URL via `StorageService`.
        -   Commits DB transaction.
        -   Publishes `SalesCompletedEvent` to `MessageBrokerService`.
    -   `void_transaction(transaction_id, manager_approval_code) -> None`:
        -   Verifies manager approval.
        -   Reverses inventory changes.
        -   Updates transaction status to 'VOIDED'.
        -   Records audit log.
    -   `refund_transaction(transaction_id, refund_data) -> None`:
        -   Verifies manager approval.
        -   Processes refund via `PaymentGatewayService`.
        -   Updates transaction status to 'REFUNDED'.
        -   Records audit log.
-   **InventoryService**:
    -   `get_inventory_by_location(location_id, location_type) -> List[Inventory]`: Retrieves inventory for a location, uses Redis cache for hot items.
    -   `decrement_inventory(product_id, location_id, location_type, quantity) -> None`: Decrements stock, checks for negative stock (with manager override), invalidates cache.
    -   `increment_inventory(product_id, location_id, location_type, quantity) -> None`: Increments stock, invalidates cache.
    -   `adjust_inventory(product_id, location_id, location_type, new_quantity, reason, adjusted_by_user_id, manager_approval_code) -> None`:
        -   Verifies manager approval for significant changes or negative stock.
        -   Updates inventory quantity.
        -   Creates `StockAdjustment` record.
        -   Records audit log.
        -   Publishes `InventoryAdjustedEvent` to `MessageBrokerService`.
-   **TransferService**:
    -   `request_transfer(product_id, requested_quantity, sending_location_id, receiving_location_id, requested_by_user_id) -> TransferRequest`: Creates a new transfer request with 'PENDING' status.
    -   `approve_transfer(transfer_id, approved_by_user_id) -> None`:
        -   Updates transfer status to 'APPROVED'.
        -   Decrements inventory at sending location via `InventoryService`.
        -   Records audit log.
        -   Publishes `TransferApprovedEvent` to `MessageBrokerService`.
    -   `reject_transfer(transfer_id, reason) -> None`: Updates transfer status to 'REJECTED', records audit log.
    -   `complete_transfer(transfer_id, receiving_user_id) -> None`:
        -   Updates transfer status to 'COMPLETED'.
        -   Increments inventory at receiving location via `InventoryService`.
        -   Records audit log.
        -   Publishes `TransferCompletedEvent` to `MessageBrokerService`.
-   **UserService**:
    -   `get_users(filters) -> List[User]`: Retrieves users with optional filtering.
    -   `create_user(data) -> User`: Creates a new user, hashes password.
    -   `update_user(user_id, data) -> User`: Updates user details.
    -   `deactivate_user(user_id) -> None`: Marks user as inactive.
    -   `get_roles() -> List[Role]`: Retrieves all defined roles.
-   **ReportService**:
    -   `initiate_sales_report_generation(params) -> UUID`: Publishes a message to `MessageBrokerService` to trigger a background job for sales report generation.
    -   `initiate_inventory_report_generation(params) -> UUID`: Publishes a message for inventory report.
    -   `initiate_transfer_report_generation(params) -> UUID`: Publishes a message for transfer report.
    -   `get_report_status(report_id) -> ReportStatus`: Retrieves the status of a background report job.
-   **CacheService**:
    -   `get(key) -> Any`: Retrieves data from Redis.
    -   `set(key, value, ttl) -> None`: Stores data in Redis with a time-to-live.
    -   `delete(key) -> None`: Deletes data from Redis.
    -   `invalidate_product_cache(product_id) -> None`: Specific invalidation for product updates.
    -   `invalidate_inventory_cache(product_id, location_id, location_type) -> None`: Specific invalidation for inventory updates.
-   **MessageBrokerService**:
    -   `publish(exchange, routing_key, message) -> None`: Publishes messages to RabbitMQ.
    -   `subscribe(queue, callback) -> None`: Subscribes to a RabbitMQ queue.
-   **StorageService**:
    -   `upload_file(file_data, bucket, path, content_type) -> str`: Uploads a file to AWS S3, returns URL.
    -   `get_file_url(bucket, path) -> str`: Generates a pre-signed URL for a file.
-   **PaymentGatewayService**:
    -   `process_payment(amount, method, details) -> PaymentResult`: Integrates with external payment gateway API.
    -   `process_refund(transaction_ref, amount) -> RefundResult`: Integrates with external payment gateway API for refunds.
-   **TaxService**:
    -   `calculate_tax(items, store_location) -> TaxDetails`: Integrates with external tax API to calculate sales tax.
-   **EmailSmsService**:
    -   `send_email(to, subject, body) -> None`: Sends email notifications.
    -   `send_sms(to, message) -> None`: Sends SMS notifications.

# Repositories
-   **UserRepository**:
    -   `get_by_username(username) -> User`: Fetches user by username.
    -   `get_by_id(user_id) -> User`: Fetches user by ID.
    -   `create(user_data) -> User`: Creates a new user record.
    -   `update(user_id, update_data) -> User`: Updates user record.
    -   `list_users(filters) -> List[User]`: Lists users with filters.
-   **RoleRepository**:
    -   `get_by_name(role_name) -> Role`: Fetches role by name.
    -   `list_roles() -> List[Role]`: Lists all roles.
-   **ProductRepository**:
    -   `get_by_sku(sku) -> Product`: Fetches product by SKU.
    -   `get_by_barcode(barcode) -> Product`: Fetches product by barcode.
    -   `get_by_id(product_id) -> Product`: Fetches product by ID.
    -   `create(product_data) -> Product`: Creates a new product.
    -   `update(product_id, update_data) -> Product`: Updates product.
    -   `list_products(filters) -> List[Product]`: Lists products with filters.
-   **InventoryRepository**:
    -   `get_by_product_and_location(product_id, location_id, location_type) -> Inventory`: Fetches inventory for a specific product at a location.
    -   `update_quantity(inventory_id, new_quantity) -> Inventory`: Updates inventory quantity.
    -   `create_adjustment(adjustment_data) -> StockAdjustment`: Records a stock adjustment.
    -   `list_inventory_by_location(location_id, location_type) -> List[Inventory]`: Lists all inventory for a location.
-   **TransactionRepository**:
    -   `create(transaction_data) -> Transaction`: Creates a new transaction record.
    -   `add_items(transaction_id, items_data) -> List[TransactionItem]`: Adds items to a transaction.
    -   `get_by_id(transaction_id) -> Transaction`: Fetches transaction by ID.
    -   `update_status(transaction_id, new_status) -> Transaction`: Updates transaction status.
    -   `list_transactions(filters) -> List[Transaction]`: Lists transactions with filters.
-   **PaymentRepository**:
    -   `create(payment_data) -> Payment`: Records a payment.
-   **TransferRepository**:
    -   `create(transfer_data) -> TransferRequest`: Creates a new transfer request.
    -   `get_by_id(transfer_id) -> TransferRequest`: Fetches transfer request by ID.
    -   `update_status(transfer_id, new_status, approved_by_user_id=None) -> TransferRequest`: Updates transfer status.
    -   `list_transfers(filters) -> List[TransferRequest]`: Lists transfer requests with filters.
-   **AuditLogRepository**:
    -   `create(log_data) -> AuditLog`: Appends an immutable audit log entry.
    -   `list_logs(filters) -> List[AuditLog]`: Lists audit logs with filters.

# Models
All models inherit from `Base` (SQLAlchemy declarative base) and use `UUID` for primary keys.

-   **User**:
    -   `user_id: UUID (PK)`
    -   `username: str (UNIQUE)`
    -   `password_hash: str`
    -   `email: str`
    -   `first_name: str`
    -   `last_name: str`
    -   `role_id: UUID (FK to Role)`
    -   `store_id: UUID (FK to Store, NULLABLE)`
    -   `is_active: bool`
    -   `created_at: datetime`
    -   `updated_at: datetime`
-   **Role**:
    -   `role_id: UUID (PK)`
    -   `role_name: str (UNIQUE, e.g., 'Cashier', 'Store Manager', 'Warehouse Manager', 'Administrator')`
    -   `permissions: JSONB` (e.g., `{"can_void_transaction": true, "can_adjust_inventory": false}`)
-   **Store**:
    -   `store_id: UUID (PK)`
    -   `store_name: str (UNIQUE)`
    -   `address: str`
    -   `city: str`
    -   `state: str`
    -   `zip_code: str`
    -   `phone_number: str`
    -   `tax_rate: Numeric(5,4)`
-   **Warehouse**:
    -   `warehouse_id: UUID (PK)`
    -   `warehouse_name: str (UNIQUE)`
    -   `address: str`
    -   `city: str`
    -   `state: str`
    -   `zip_code: str`
    -   `phone_number: str`
-   **Product**:
    -   `product_id: UUID (PK)`
    -   `sku: str (UNIQUE)`
    -   `name: str`
    -   `description: str`
    -   `price: Numeric(10,2)`
    -   `barcode: str (UNIQUE)`
    -   `category_id: UUID (FK to Category)`
    -   `is_active: bool`
    -   `created_at: datetime`
    -   `updated_at: datetime`
-   **Category**:
    -   `category_id: UUID (PK)`
    -   `category_name: str (UNIQUE)`
-   **Inventory**:
    -   `inventory_id: UUID (PK)`
    -   `product_id: UUID (FK to Product)`
    -   `location_id: UUID` (Polymorphic FK to Store or Warehouse)
    -   `location_type: Enum('STORE', 'WAREHOUSE')`
    -   `quantity: Integer`
    -   `last_adjusted_at: datetime`
    -   `min_stock_level: Integer`
-   **Transaction**:
    -   `transaction_id: UUID (PK)`
    -   `store_id: UUID (FK to Store)`
    -   `user_id: UUID (FK to User, cashier)`
    -   `transaction_date: datetime`
    -   `total_amount: Numeric(10,2)`
    -   `tax_amount: Numeric(10,2)`
    -   `discount_amount: Numeric(10,2)`
    -   `payment_method: Enum('CASH', 'CREDIT_CARD', 'DEBIT_CARD')`
    -   `status: Enum('COMPLETED', 'VOIDED', 'REFUNDED', 'PENDING_OFFLINE_SYNC')`
    -   `receipt_url: str (S3 URL, NULLABLE)`
    -   `created_at: datetime`
    -   `updated_at: datetime`
-   **TransactionItem**:
    -   `transaction_item_id: UUID (PK)`
    -   `transaction_id: UUID (FK to Transaction)`
    -   `product_id: UUID (FK to Product)`
    -   `quantity: Integer`
    -   `unit_price: Numeric(10,2)`
    -   `line_total: Numeric(10,2)`
    -   `discount_applied: Numeric(10,2)`
-   **Payment**:
    -   `payment_id: UUID (PK)`
    -   `transaction_id: UUID (FK to Transaction)`
    -   `amount: Numeric(10,2)`
    -   `method: Enum('CASH', 'CREDIT_CARD', 'DEBIT_CARD')`
    -   `status: Enum('SUCCESS', 'FAILED', 'PENDING')`
    -   `external_transaction_id: str (UNIQUE, from payment gateway)`
    -   `created_at: datetime`
-   **StockAdjustment**:
    -   `adjustment_id: UUID (PK)`
    -   `product_id: UUID (FK to Product)`
    -   `location_id: UUID` (Polymorphic FK)
    -   `location_type: Enum('STORE', 'WAREHOUSE')`
    -   `old_quantity: Integer`
    -   `new_quantity: Integer`
    -   `reason: str`
    -   `adjusted_by_user_id: UUID (FK to User)`
    -   `adjustment_date: datetime`
    -   `audit_log: JSONB` (details of change)
-   **TransferRequest**:
    -   `transfer_id: UUID (PK)`
    -   `product_id: UUID (FK to Product)`
    -   `requested_quantity: Integer`
    -   `sending_location_id: UUID` (Polymorphic FK)
    -   `sending_location_type: Enum('STORE', 'WAREHOUSE')`
    -   `receiving_location_id: UUID` (Polymorphic FK)
    -   `receiving_location_type: Enum('STORE', 'WAREHOUSE')`
    -   `requested_by_user_id: UUID (FK to User)`
    -   `request_date: datetime`
    -   `status: Enum('PENDING', 'APPROVED', 'REJECTED', 'COMPLETED')`
    -   `approved_by_user_id: UUID (FK to User, NULLABLE)`
    -   `approval_date: datetime (NULLABLE)`
    -   `completion_date: datetime (NULLABLE)`
-   **AuditLog**:
    -   `log_id: UUID (PK)`
    -   `entity_type: str` (e.g., 'Transaction', 'Inventory', 'User')
    -   `entity_id: UUID`
    -   `operation_type: Enum('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'REFUND', 'VOID', 'ADJUST', 'TRANSFER_REQUEST', 'TRANSFER_APPROVE', 'TRANSFER_REJECT', 'TRANSFER_COMPLETE')`
    -   `user_id: UUID (FK to User)`
    -   `timestamp: datetime`
    -   `details: JSONB` (old/new values, IP address, etc.)

# DTOs
Pydantic models for request and response payloads, including