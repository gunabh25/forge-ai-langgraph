# Executive Summary
This Backend Blueprint outlines the design for a cloud-based Point of Sale (POS) system, supporting a central warehouse and 17 retail stores. The system is built as a modular monolith using Python with FastAPI, designed to provide efficient sales transaction processing, real-time inventory visibility, streamlined inventory transfers, and secure role-based access. It integrates with PostgreSQL for robust data persistence, Redis for caching, and RabbitMQ for asynchronous communication, ensuring high availability, data consistency, and scalability, while supporting an offline-first PWA client for continuous store operations.

# Folder Structure
```
app/
├── main.py
├── config/
│   ├── settings.py
│   └── database.py
├── api/
│   ├── v1/
│   │   ├── auth.py
│   │   ├── products.py
│   │   ├── sales.py
│   │   ├── inventory.py
│   │   ├── transfers.py
│   │   ├── reports.py
│   │   └── users.py
│   └── middleware/
│       ├── auth_middleware.py
│       ├── logging_middleware.py
│       └── error_middleware.py
├── core/
│   ├── security.py
│   ├── exceptions.py
│   └── constants.py
├── models/
│   ├── base.py
│   ├── location.py
│   ├── product.py
│   ├── user.py
│   ├── inventory.py
│   ├── transaction.py
│   ├── transfer.py
│   └── audit.py
├── schemas/
│   ├── auth.py
│   ├── product.py
│   ├── sales.py
│   ├── inventory.py
│   ├── transfer.py
│   ├── user.py
│   ├── report.py
│   └── common.py
├── services/
│   ├── auth_service.py
│   ├── product_service.py
│   ├── sales_service.py
│   ├── inventory_service.py
│   ├── transfer_service.py
│   ├── user_service.py
│   └── report_service.py
├── repositories/
│   ├── base_repository.py
│   ├── location_repository.py
│   ├── product_repository.py
│   ├── user_repository.py
│   ├── inventory_repository.py
│   ├── transaction_repository.py
│   ├── transfer_repository.py
│   └── audit_repository.py
├── workers/
│   └── sync_worker.py
└── tests/
    ├── unit/
    └── integration/
```

# Module Breakdown
-   **AuthModule**: Handles user authentication, token generation, and secure password management.
-   **UserModule**: Manages user accounts, roles, and permissions (Admin only for creation/modification).
-   **ProductModule**: Manages product master data (add, update, delete, retrieve product details).
-   **SalesModule**: Processes sales transactions, refunds, voids, and updates inventory levels.
-   **InventoryModule**: Tracks current stock levels, supports manual adjustments, and provides inventory visibility.
-   **TransferModule**: Manages inventory transfer requests, confirmations, and history between locations.
-   **ReportModule**: Generates various reports (sales, inventory, transfer history).
-   **SynchronizationModule**: (Implicitly handled by specific API endpoints and a dedicated worker) Manages incoming offline transactions and ensures data consistency.

# Controllers
-   `AuthController`: Handles user login and session management.
    -   `login(credentials: LoginRequest) -> TokenResponse`: Authenticates user and returns JWT.
    -   `logout() -> MessageResponse`: Invalidates JWT (if server-side revocation is implemented).
-   `UserController`: Manages user accounts (Admin only).
    -   `create_user(user_data: UserCreateRequest) -> UserResponse`: Creates a new user.
    -   `get_current_user() -> UserResponse`: Retrieves authenticated user's profile.
    -   `update_user(user_id: UUID, user_data: UserUpdateRequest) -> UserResponse`: Updates user details.
-   `ProductController`: Manages product master data.
    -   `create_product(product_data: ProductCreateRequest) -> ProductResponse`: Adds a new product.
    -   `get_product_by_id(product_id: UUID) -> ProductResponse`: Retrieves product details by ID.
    -   `get_product_by_barcode(barcode: str) -> ProductResponse`: Resolves product details by barcode.
    -   `update_product(product_id: UUID, product_data: ProductUpdateRequest) -> ProductResponse`: Updates product details.
    -   `delete_product(product_id: UUID) -> MessageResponse`: Deactivates/deletes a product.
-   `SalesController`: Handles sales transactions, refunds, and voids.
    -   `checkout(transaction_data: SalesCheckoutRequest) -> SalesCheckoutResponse`: Processes a new sales transaction.
    -   `refund_transaction(transaction_id: UUID, refund_data: RefundRequest) -> MessageResponse`: Processes a refund.
    -   `void_transaction(transaction_id: UUID) -> MessageResponse`: Voids a transaction.
    -   `get_transaction_details(transaction_id: UUID) -> TransactionResponse`: Retrieves transaction details.
    -   `sync_offline_transactions(transactions: List[SalesCheckoutRequest]) -> SyncResponse`: Endpoint for Synchronization Service to push offline transactions.
-   `InventoryController`: Manages inventory levels and adjustments.
    -   `get_inventory_levels(location_id: UUID, product_id: UUID) -> InventoryLevelResponse`: Views inventory for a specific product at a location.
    -   `get_location_inventory(location_id: UUID) -> List[InventoryLevelResponse]`: Views all inventory for a specific location.
    -   `adjust_inventory(adjustment_data: InventoryAdjustmentRequest) -> InventoryLevelResponse`: Manually adjusts inventory levels.
-   `TransferController`: Manages inventory transfers.
    -   `request_transfer(transfer_data: InventoryTransferRequest) -> InventoryTransferResponse`: Initiates a transfer request.
    -   `get_transfers(location_id: UUID, status: Optional[str]) -> List[InventoryTransferResponse]`: Views transfers for a location.
    -   `confirm_transfer(transfer_id: UUID, confirmation_data: TransferConfirmationRequest) -> MessageResponse`: Confirms receipt of transferred inventory.
    -   `reject_transfer(transfer_id: UUID, rejection_data: TransferRejectionRequest) -> MessageResponse`: Rejects an inventory transfer.
-   `ReportController`: Generates various reports.
    -   `get_daily_sales_report(location_id: UUID, date: date) -> SalesReportResponse`: Generates daily sales report.
    -   `get_inventory_report(location_id: UUID) -> InventoryReportResponse`: Generates current inventory report.
    -   `get_transfer_history_report(location_id: UUID) -> TransferHistoryReportResponse`: Generates transfer history report.

# Routes
-   `POST /api/v1/auth/login` -> `AuthController.login` (Public)
-   `POST /api/v1/auth/logout` -> `AuthController.logout` (AuthRequired)
-   `GET /api/v1/users/me` -> `UserController.get_current_user` (AuthRequired)
-   `POST /api/v1/users` -> `UserController.create_user` (AuthRequired, Role: Administrator)
-   `PUT /api/v1/users/{id}` -> `UserController.update_user` (AuthRequired, Role: Administrator)
-   `POST /api/v1/products` -> `ProductController.create_product` (AuthRequired, Role: Administrator, Warehouse Manager)
-   `GET /api/v1/products/{id}` -> `ProductController.get_product_by_id` (AuthRequired)
-   `GET /api/v1/products/scan` -> `ProductController.get_product_by_barcode` (AuthRequired)
-   `PUT /api/v1/products/{id}` -> `ProductController.update_product` (AuthRequired, Role: Administrator, Warehouse Manager)
-   `DELETE /api/v1/products/{id}` -> `ProductController.delete_product` (AuthRequired, Role: Administrator)
-   `POST /api/v1/sales/checkout` -> `SalesController.checkout` (AuthRequired, Role: Cashier, Store Manager)
-   `POST /api/v1/sales/{transaction_id}/refund` -> `SalesController.refund_transaction` (AuthRequired, Role: Store Manager, Administrator)
-   `POST /api/v1/sales/{transaction_id}/void` -> `SalesController.void_transaction` (AuthRequired, Role: Store Manager, Administrator)
-   `GET /api/v1/sales/{transaction_id}` -> `SalesController.get_transaction_details` (AuthRequired, Role: Cashier, Store Manager, Administrator)
-   `POST /api/v1/sales/sync-offline` -> `SalesController.sync_offline_transactions` (AuthRequired, Role: SyncService) - *Internal endpoint for Synchronization Service*
-   `GET /api/v1/inventory` -> `InventoryController.get_inventory_levels` (AuthRequired)
-   `GET /api/v1/inventory/locations/{location_id}` -> `InventoryController.get_location_inventory` (AuthRequired)
-   `POST /api/v1/inventory/adjust` -> `InventoryController.adjust_inventory` (AuthRequired, Role: Store Manager, Warehouse Manager)
-   `POST /api/v1/transfers/request` -> `TransferController.request_transfer` (AuthRequired, Role: Store Manager, Warehouse Manager)
-   `GET /api/v1/transfers` -> `TransferController.get_transfers` (AuthRequired, Role: Store Manager, Warehouse Manager)
-   `POST /api/v1/transfers/{transfer_id}/confirm` -> `TransferController.confirm_transfer` (AuthRequired, Role: Store Manager, Warehouse Manager)
-   `POST /api/v1/transfers/{transfer_id}/reject` -> `TransferController.reject_transfer` (AuthRequired, Role: Store Manager, Warehouse Manager)
-   `GET /api/v1/reports/sales/daily` -> `ReportController.get_daily_sales_report` (AuthRequired, Role: Store Manager, Administrator)
-   `GET /api/v1/reports/inventory` -> `ReportController.get_inventory_report` (AuthRequired, Role: Store Manager, Warehouse Manager, Administrator)
-   `GET /api/v1/reports/transfers/history` -> `ReportController.get_transfer_history_report` (AuthRequired, Role: Store Manager, Warehouse Manager, Administrator)

# Services
-   `AuthService`:
    -   `authenticate_user(username, password) -> User`: Verifies credentials, generates JWT.
    -   `create_access_token(user_id, roles, location_id) -> str`: Creates a signed JWT.
    -   `hash_password(password) -> str`: Hashes password using bcrypt.
    -   `verify_password(plain_password, hashed_password) -> bool`: Verifies password.
-   `UserService`:
    -   `create_user(user_data: UserCreateRequest) -> User`: Creates a new user with hashed password and assigns roles.
    -   `get_user_by_id(user_id) -> User`: Retrieves user details.
    -   `get_user_by_username(username) -> User`: Retrieves user by username.
    -   `update_user(user_id, update_data) -> User`: Updates user details and roles.
-   `ProductService`:
    -   `add_product(product_data: ProductCreateRequest) -> Product`: Creates a new product, validates SKU/barcode uniqueness.
    -   `get_product(product_id) -> Product`: Retrieves product by ID.
    -   `get_product_by_barcode(barcode) -> Product`: Retrieves product by barcode.
    -   `update_product(product_id, update_data) -> Product`: Updates product details, invalidates cache.
    -   `deactivate_product(product_id) -> None`: Marks product as inactive.
-   `SalesService`:
    -   `process_checkout(transaction_data: SalesCheckoutRequest) -> Transaction`:
        -   Validates items, quantities, and payment method.
        -   Checks inventory availability for each item at the specified location.
        -   Calculates subtotal, tax (potentially via external API), and grand total.
        -   Decrements inventory levels for each item in a database transaction.
        -   Records the transaction and its items.
        -   Publishes `SalesCompleted` event to RabbitMQ.
        -   Generates and stores receipt in S3.
    -   `process_refund(transaction_id, refund_data) -> Transaction`:
        -   Authorizes refund (Store Manager+).
        -   Increments inventory levels for refunded items.
        -   Updates transaction status to 'refunded'.
        -   Publishes `SalesRefunded` event.
    -   `void_transaction(transaction_id) -> Transaction`:
        -   Authorizes void (Store Manager+).
        -   Increments inventory levels for voided items.
        -   Updates transaction status to 'voided'.
        -   Publishes `SalesVoided` event.
    -   `handle_offline_transactions(transactions: List[SalesCheckoutRequest]) -> SyncResponse`:
        -   Receives a batch of offline transactions from the Synchronization Service.
        -   Processes each transaction, applying conflict resolution (e.g., last-write-wins for inventory, or specific business rules).
        -   Ensures atomicity for each transaction.
        -   Publishes events for each successfully processed transaction.
-   `InventoryService`:
    -   `get_current_stock(location_id, product_id) -> int`: Retrieves current stock level.
    -   `get_all_inventory_by_location(location_id) -> List[Inventory]`: Retrieves all inventory for a location.
    -   `adjust_stock(location_id, product_id, quantity_change, adjustment_type, reason, user_id) -> Inventory`:
        -   Applies manual inventory adjustment.
        -   Validates quantity change (e.g., prevents negative stock unless authorized).
        -   Records `InventoryAdjustment` with audit trail.
        -   Publishes `InventoryAdjusted` event.
-   `TransferService`:
    -   `initiate_transfer(transfer_data: InventoryTransferRequest) -> InventoryTransfer`:
        -   Validates sending/receiving locations and product availability.
        -   Creates a `pending` `InventoryTransfer` record.
        -   Decrements inventory at sending location (or marks as 'in transit').
        -   Publishes `TransferRequested` event to RabbitMQ (for receiving location notification).
    -   `confirm_transfer(transfer_id, user_id) -> InventoryTransfer`:
        -   Authorizes confirmation (Receiving Store Manager+).
        -   Updates `InventoryTransfer` status to 'received'.
        -   Increments inventory at receiving location.
        -   Publishes `TransferConfirmed` event.
    -   `reject_transfer(transfer_id, user_id, reason) -> InventoryTransfer`:
        -   Authorizes rejection.
        -   Updates `InventoryTransfer` status to 'rejected'.
        -   Reverts inventory at sending location.
        -   Publishes `TransferRejected` event.
-   `ReportService`:
    -   `generate_daily_sales_report(location_id, date) -> SalesReport`: Aggregates sales data for a given day/location.
    -   `generate_inventory_report(location_id) -> InventoryReport`: Retrieves current inventory snapshot for a location.
    -   `generate_transfer_history_report(location_id) -> TransferHistoryReport`: Retrieves all transfers involving a location.

# Repositories
-   `BaseRepository`: Generic CRUD operations.
-   `LocationRepository`:
    -   `get_by_id(location_id) -> Location`
    -   `get_all() -> List[Location]`
-   `ProductRepository`:
    -   `create(product_data) -> Product`
    -   `get_by_id(product_id) -> Product`
    -   `get_by_sku(sku) -> Product`
    -   `get_by_barcode(barcode) -> Product`
    -   `update(product_id, update_data) -> Product`
    -   `delete(product_id) -> None` (soft delete/deactivate)
-   `UserRepository`:
    -   `create(user_data) -> User`
    -   `get_by_id(user_id) -> User`
    -   `get_by_username(username) -> User`
    -   `update(user_id, update_data) -> User`
    -   `get_roles_for_user(user_id) -> List[Role]`
-   `InventoryRepository`:
    -   `get_by_location_and_product(location_id, product_id) -> Inventory`
    -   `get_all_by_location(location_id) -> List[Inventory]`
    -   `increment_quantity(location_id, product_id, quantity) -> Inventory`
    -   `decrement_quantity(location_id, product_id, quantity) -> Inventory`
    -   `create_adjustment(adjustment_data) -> InventoryAdjustment`
-   `TransactionRepository`:
    -   `create(transaction_data) -> Transaction`
    -   `get_by_id(transaction_id) -> Transaction`
    -   `update_status(transaction_id, new_status) -> Transaction`
    -   `get_daily_sales_summary(location_id, date) -> SalesSummary`
-   `TransactionItemRepository`:
    -   `create_batch(items_data) -> List[TransactionItem]`
    -   `get_by_transaction_id(transaction_id) -> List[TransactionItem]`
-   `TransferRepository`:
    -   `create(transfer_data) -> InventoryTransfer`
    -   `get_by_id(transfer_id) -> InventoryTransfer`
    -   `get_by_location_and_status(location_id, status) -> List[InventoryTransfer]`
    -   `update_status(transfer_id, new_status, confirmed_by_user_id=None, confirmation_timestamp=None) -> InventoryTransfer`
-   `AuditRepository`:
    -   `create(audit_log_data) -> AuditLog`

# Models
-   `Location`: `id` (UUID, PK), `name` (str), `address` (str), `type` (Enum: 'store', 'warehouse'), `is_active` (bool), `created_at` (datetime), `updated_at` (datetime).
-   `Product`: `id` (UUID, PK), `sku` (str, Unique), `barcode` (str, Unique), `name` (str), `description` (str), `price` (Decimal), `is_active` (bool), `created_at` (datetime), `updated_at` (datetime).
-   `User`: `id` (UUID, PK), `username` (str, Unique), `password_hash` (str), `email` (str), `first_name` (str), `last_name` (str), `location_id` (UUID, FK to Location, nullable), `is_active` (bool), `created_at` (datetime), `updated_at` (datetime).
-   `Role`: `id` (UUID, PK), `name` (str, Unique, e.g., 'Cashier', 'Store Manager', 'Warehouse Manager', 'Administrator').
-   `UserRole`: `user_id` (UUID, FK), `role_id` (UUID, FK). (Junction table)
-   `Inventory`: `id` (UUID, PK), `location_id` (UUID, FK), `product_id` (UUID, FK), `quantity` (int), `last_updated` (datetime). (Unique composite index on `location_id`, `product_id`)
-   `InventoryAdjustment`: `id` (UUID, PK), `inventory_id` (UUID, FK), `user_id` (UUID, FK), `adjustment_type` (Enum: 'stock_take', 'damage', 'return', 'other'), `quantity_change` (int), `reason` (str), `timestamp` (datetime).
-   `InventoryTransfer`: `id` (UUID, PK), `sending_location_id` (UUID, FK), `receiving_location_id` (UUID, FK), `product_id` (UUID, FK), `quantity` (int), `requested_by_user_id` (UUID, FK), `request_timestamp` (datetime), `status` (Enum: 'pending', 'sent', 'received', 'rejected'), `confirmed_by_user_id` (UUID, FK, nullable), `confirmation_timestamp` (datetime, nullable), `rejection_reason` (str, nullable).
-   `Transaction`: `id` (UUID, PK), `location_id` (UUID, FK), `user_id` (UUID, FK), `transaction_timestamp` (datetime), `subtotal` (Decimal), `tax_amount` (Decimal), `grand_total` (Decimal), `payment_method` (Enum: 'cash', 'credit_card', 'debit_card'), `status` (Enum: 'completed', 'refunded', 'voided', 'pending_sync'), `receipt_url` (str, nullable), `created_at` (datetime), `updated_at` (datetime).
-   `TransactionItem`: `id` (UUID, PK), `transaction_id` (UUID, FK), `product_id` (UUID, FK), `quantity` (int), `unit_price` (Decimal), `total_price` (Decimal), `discount_amount` (Decimal, nullable).
-   `AuditLog`: `id` (UUID, PK), `user_id` (UUID, FK, nullable), `action_type` (str), `entity_type` (str), `entity_id` (UUID, nullable), `details` (JSONB), `timestamp` (datetime).

# DTOs
-   `LoginRequest`: `username` (str), `password` (str).
-   `TokenResponse`: `access_token` (str), `token_type` (str = "bearer").
-   `UserCreateRequest`: `username` (str), `password` (str), `email` (str), `first_name` (str), `last_name` (str), `location_id` (UUID, nullable), `role_ids` (List[UUID]).
-   `UserUpdateRequest`: `email` (str, optional), `first_name` (str, optional), `last_name` (str, optional), `location_id` (UUID, optional), `is_active` (bool, optional), `role_ids` (List[UUID], optional).
-   `UserResponse`: `id` (UUID), `username` (str), `email` (str), `first_name` (str), `last_name` (str), `location_id` (UUID, nullable), `roles` (List[str]), `is_active` (bool).
-   `ProductCreateRequest`: `sku` (str), `barcode` (str), `name` (str), `description` (str), `price` (Decimal, >0).
-   `ProductUpdateRequest`: `name` (str, optional), `description` (str, optional), `price` (Decimal, optional, >0), `is_active` (bool, optional).
-   `ProductResponse`: `id` (UUID), `sku` (str), `barcode` (str), `name` (str), `description` (str), `price` (Decimal), `is_active` (bool).
-   `SalesCheckoutItemRequest`: `product_id` (UUID), `quantity` (int, >0), `unit_price` (Decimal, >0), `discount_amount` (Decimal, >=0).
-   `SalesCheckoutRequest`: `location_id` (UUID), `user_id` (UUID), `payment_method` (Enum), `items` (List[SalesCheckoutItemRequest]), `payment_details` (Dict, optional, e.g., `card_token`, `amount`).
-   `SalesCheckoutResponse`: `transaction_id` (UUID), `grand_total` (Decimal), `receipt_url` (str, nullable), `status` (str).
-   `RefundRequest`: `refund_items` (List[Dict[product_id, quantity]]), `reason` (str).
-   `InventoryLevelResponse`: `product_id` (UUID), `product_name` (str), `sku` (str), `quantity` (int).
-   `InventoryAdjustmentRequest`: `location_id` (UUID), `product_id` (UUID), `quantity_change` (int, !=0), `adjustment_type` (Enum), `reason` (str).
-   `InventoryTransferRequest`: `sending_location_id` (UUID), `receiving_location_id` (UUID), `product_id` (UUID), `quantity` (int, >0).
-   `InventoryTransferResponse`: `id` (UUID), `sending_location_name` (str), `receiving_location_name` (str), `product_name` (str), `quantity` (int), `status` (str), `request_timestamp` (datetime).
-   `TransferConfirmationRequest`: `confirmed_by_user_id` (UUID).
-   `TransferRejectionRequest`: `rejected_by_user_id` (UUID), `reason` (str).
-   `MessageResponse`: `status` (str), `message` (str).
-   `SyncResponse`: `processed_transactions` (int), `failed_transactions` (int), `errors` (List[Dict]).

# Validation Strategy
Input validation is primarily handled by Pydantic schemas for all incoming API requests.
-   **Schema-based Validation**: Pydantic models define the expected structure, data types, and basic constraints (e.g., `Decimal(gt=0)`, `int(gt=0)`).
-   **Custom Validators**: For more complex business rules (e.g., SKU format, barcode checksums, preventing negative inventory unless explicitly authorized), custom Pydantic validators or service-level checks will be implemented.
-   **Uniqueness Checks**: Database constraints and repository-level checks ensure uniqueness for `Product.sku`, `Product.barcode`, and `User.username`.
-   **Referential Integrity**: Foreign key constraints in PostgreSQL ensure that related entities exist.
-   **Input Sanitization**: FastAPI automatically handles basic input sanitization by parsing JSON. Further sanitization for string inputs (e.g., removing leading/trailing whitespace, preventing XSS in displayed fields) will be applied at the service layer where necessary, especially for user-generated content.
-   **Error Responses**: Validation errors will be returned using HTTP 422 Unprocessable Entity, with detailed error messages following RFC 7807 Problem Details format.

# Authentication
-   **Mechanism**: JWT (JSON Web Tokens) with an OAuth2 bearer token flow.
-   **Login**: Users send `username` and `password` to `POST /api/v1/auth/login`.
-   **Password Hashing**: Passwords are hashed using `bcrypt` with a unique salt per user before storage.
-   **Token Generation**: Upon successful authentication, `AuthService` generates a short-lived JWT access token (e.g., 15-30 minutes expiry). The token payload includes `user_id`, `username`, `roles`, and `location_id`.
-   **Token Usage**: Clients include the JWT in the `Authorization` header as `Bearer <token>` for all protected API requests.
-   **Token Validation**: A middleware (`auth_middleware.py`) intercepts requests, extracts the JWT, verifies its signature (using a secret key or public/private key pair), checks expiry, and extracts user claims.
-   **Statelessness**: JWTs are stateless, meaning the backend doesn't need to store session information, enhancing scalability.
-   **Refresh Tokens**: For a better user experience, a longer-lived refresh token mechanism could be considered in a future iteration, allowing clients to obtain new access tokens without re-logging in, while maintaining security by allowing revocation of refresh tokens.

# Authorization
-   **Mechanism**: Role-Based Access Control (RBAC).
-   **Roles**: Defined roles include 'Cashier', 'Store Manager', 'Warehouse Manager', 'Administrator'.
-   **Permissions**: Each role is associated with a set of permissions, which are implicitly checked against specific API endpoints and critical actions.
-   **Implementation**:
    -   User roles are included in the JWT payload during authentication.
    -   A custom FastAPI dependency (`auth_middleware.py`) extracts roles from the validated JWT.
    -   Decorators or explicit checks within controller methods (`@has_role('Administrator')`) verify if the authenticated user possesses the required role(s) for the requested action.
    -   Least privilege principle is applied: users are granted only the minimum necessary permissions.
-   **Critical Actions**: Actions like refunds, voids, inventory adjustments, and user management explicitly require higher-level roles (e.g., Store Manager, Warehouse Manager, Administrator).

# Middleware
-   **`LoggingMiddleware`**:
    -   **Purpose**: Logs every incoming request and outgoing response.
    -   **Details**: Captures request method, path, client IP, user ID (from JWT if authenticated), request duration, and response status code. Generates a unique `X-Request-ID` (correlation ID) for each request, added to logs and response headers.
    -   **Order**: Executed early in the request pipeline.
-   **`AuthMiddleware`**:
    -   **Purpose**: Authenticates requests using JWT and populates user context.
    -   **Details**: Extracts, validates, and decodes JWT from the `Authorization` header. Sets `request.state.user` with user details and roles. Raises `HTTPException(401)` for invalid/missing tokens.
    -   **Order**: After `LoggingMiddleware`, before `AuthorizationMiddleware`.
-   **`AuthorizationMiddleware` (or