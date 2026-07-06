# AI Software Engineer – Output Examples

These examples illustrate the expected JSON workspace structure. Values are abbreviated for readability — in real output every file must contain complete, production-ready source code.

---

## Example 1: POS System (FastAPI + PostgreSQL)

```json
{
  "src/controllers/product_controller.py": "\"\"\"Product controller handling HTTP requests for product management.\"\"\"\nfrom fastapi import APIRouter, Depends, HTTPException, status\nfrom src.services.product_service import ProductService\nfrom src.schemas.product_schema import ProductCreateRequest, ProductResponse\nfrom src.middleware.auth_middleware import require_role\nfrom typing import List\n\nrouter = APIRouter(prefix='/api/v1/products', tags=['Products'])\n\n@router.get('/', response_model=List[ProductResponse])\nasync def list_products(service: ProductService = Depends()) -> List[ProductResponse]:\n    \"\"\"List all products.\"\"\"\n    return await service.list_all()\n\n@router.post('/', response_model=ProductResponse, status_code=status.HTTP_201_CREATED)\nasync def create_product(\n    payload: ProductCreateRequest,\n    service: ProductService = Depends(),\n    _: None = Depends(require_role('manager'))\n) -> ProductResponse:\n    \"\"\"Create a new product (manager only).\"\"\"\n    return await service.create(payload)\n",
  "src/services/product_service.py": "\"\"\"Product business logic service.\"\"\"\nfrom src.repositories.product_repository import ProductRepository\nfrom src.schemas.product_schema import ProductCreateRequest, ProductResponse\nfrom src.core.exceptions import ProductNotFoundError\nfrom typing import List\n\nclass ProductService:\n    def __init__(self, repo: ProductRepository):\n        self._repo = repo\n\n    async def list_all(self) -> List[ProductResponse]:\n        rows = await self._repo.find_all()\n        return [ProductResponse.from_orm(r) for r in rows]\n\n    async def create(self, payload: ProductCreateRequest) -> ProductResponse:\n        product = await self._repo.insert(payload)\n        return ProductResponse.from_orm(product)\n",
  "src/repositories/product_repository.py": "\"\"\"Product repository — data access layer.\"\"\"\nfrom sqlalchemy.ext.asyncio import AsyncSession\nfrom src.models.product import Product\nfrom src.schemas.product_schema import ProductCreateRequest\nfrom sqlalchemy import select\n\nclass ProductRepository:\n    def __init__(self, db: AsyncSession):\n        self._db = db\n\n    async def find_all(self):\n        result = await self._db.execute(select(Product))\n        return result.scalars().all()\n\n    async def insert(self, payload: ProductCreateRequest) -> Product:\n        product = Product(**payload.dict())\n        self._db.add(product)\n        await self._db.commit()\n        await self._db.refresh(product)\n        return product\n",
  "src/models/product.py": "\"\"\"SQLAlchemy ORM model for Product.\"\"\"\nfrom sqlalchemy import Column, Integer, String, Numeric, DateTime, func\nfrom src.core.database import Base\n\nclass Product(Base):\n    __tablename__ = 'products'\n    id = Column(Integer, primary_key=True, index=True)\n    name = Column(String(200), nullable=False)\n    sku = Column(String(50), unique=True, nullable=False)\n    price = Column(Numeric(10, 2), nullable=False)\n    stock = Column(Integer, default=0)\n    created_at = Column(DateTime(timezone=True), server_default=func.now())\n",
  "src/middleware/auth_middleware.py": "\"\"\"JWT authentication middleware.\"\"\"\nfrom fastapi import Depends, HTTPException, status\nfrom fastapi.security import HTTPBearer, HTTPAuthorizationCredentials\nfrom src.core.security import decode_jwt\nfrom typing import Callable\n\nsecurity = HTTPBearer()\n\nasync def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):\n    payload = decode_jwt(credentials.credentials)\n    if not payload:\n        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')\n    return payload\n\ndef require_role(role: str) -> Callable:\n    async def _check(user=Depends(get_current_user)):\n        if user.get('role') != role:\n            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')\n    return _check\n",
  "src/routes/router.py": "\"\"\"Central route registration.\"\"\"\nfrom fastapi import FastAPI\nfrom src.controllers.product_controller import router as product_router\nfrom src.controllers.sale_controller import router as sale_router\nfrom src.controllers.auth_controller import router as auth_router\n\ndef register_routes(app: FastAPI) -> None:\n    app.include_router(auth_router)\n    app.include_router(product_router)\n    app.include_router(sale_router)\n",
  "src/core/database.py": "\"\"\"Async SQLAlchemy database engine and session factory.\"\"\"\nfrom sqlalchemy.ext.asyncio import create_async_engine, AsyncSession\nfrom sqlalchemy.orm import sessionmaker, DeclarativeBase\nfrom src.config.settings import settings\n\nengine = create_async_engine(settings.DATABASE_URL, echo=False)\nAsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)\n\nclass Base(DeclarativeBase):\n    pass\n\nasync def get_db():\n    async with AsyncSessionLocal() as session:\n        yield session\n",
  "src/core/exceptions.py": "\"\"\"Domain-specific exception hierarchy.\"\"\"\nclass AppError(Exception):\n    def __init__(self, message: str, status_code: int = 500):\n        self.message = message\n        self.status_code = status_code\n        super().__init__(message)\n\nclass ProductNotFoundError(AppError):\n    def __init__(self, product_id: int):\n        super().__init__(f'Product {product_id} not found', status_code=404)\n\nclass InsufficientStockError(AppError):\n    def __init__(self, sku: str, available: int, requested: int):\n        super().__init__(f'Insufficient stock for {sku}: {available} available, {requested} requested', status_code=400)\n",
  "src/config/settings.py": "\"\"\"Application settings loaded from environment variables.\"\"\"\nfrom pydantic_settings import BaseSettings\n\nclass Settings(BaseSettings):\n    DATABASE_URL: str\n    JWT_SECRET: str\n    JWT_ALGORITHM: str = 'RS256'\n    JWT_EXPIRY_MINUTES: int = 15\n    LOG_LEVEL: str = 'INFO'\n\n    class Config:\n        env_file = '.env'\n        case_sensitive = True\n\nsettings = Settings()\n",
  "tests/test_product_service.py": "\"\"\"Unit tests for ProductService.\"\"\"\nimport pytest\nfrom unittest.mock import AsyncMock, MagicMock\nfrom src.services.product_service import ProductService\nfrom src.schemas.product_schema import ProductCreateRequest\n\n@pytest.mark.asyncio\nasync def test_create_product_calls_repository():\n    mock_repo = AsyncMock()\n    mock_product = MagicMock(id=1, name='Widget', sku='WGT-001', price=9.99)\n    mock_repo.insert.return_value = mock_product\n    service = ProductService(repo=mock_repo)\n    payload = ProductCreateRequest(name='Widget', sku='WGT-001', price=9.99)\n    result = await service.create(payload)\n    mock_repo.insert.assert_called_once_with(payload)\n    assert result.id == 1\n",
  "Dockerfile": "# ---- Builder stage ----\nFROM python:3.12-slim AS builder\nWORKDIR /build\nCOPY requirements.txt .\nRUN pip install --no-cache-dir --prefix=/install -r requirements.txt\n\n# ---- Runtime stage ----\nFROM python:3.12-slim\nWORKDIR /app\nCOPY --from=builder /install /usr/local\nCOPY . .\nEXPOSE 8000\nCMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n",
  "requirements.txt": "fastapi==0.111.0\nuvicorn[standard]==0.29.0\nsqlalchemy[asyncio]==2.0.30\nasyncpg==0.29.0\npydantic-settings==2.2.1\npython-jose[cryptography]==3.3.0\npasslib[bcrypt]==1.7.4\nalembic==1.13.1\nhttpx==0.27.0\npytest==8.2.0\npytest-asyncio==0.23.6\n",
  "README.md": "# POS System API\\n\\n## Overview\\nCloud-based Point of Sale REST API built with FastAPI and PostgreSQL.\\n\\n## Stack\\n- **Runtime**: Python 3.12\\n- **Framework**: FastAPI\\n- **Database**: PostgreSQL (async via asyncpg)\\n- **Auth**: JWT (RS256)\\n\\n## Setup\\n```bash\\ncp .env.example .env  # Fill in DATABASE_URL, JWT_SECRET\\npip install -r requirements.txt\\nalembic upgrade head\\nuvicorn src.main:app --reload\\n```\\n\\n## Running Tests\\n```bash\\npytest tests/ -v\\n```\\n"
}
```

---

## Example 2: Inventory Management System (FastAPI + PostgreSQL)

```json
{
  "src/controllers/inventory_controller.py": "\"\"\"Inventory controller.\"\"\"\nfrom fastapi import APIRouter, Depends\nfrom src.services.inventory_service import InventoryService\nfrom src.schemas.inventory_schema import StockReceiveRequest, InventoryItemResponse\n\nrouter = APIRouter(prefix='/api/v1/inventory', tags=['Inventory'])\n\n@router.post('/receive')\nasync def receive_stock(payload: StockReceiveRequest, service: InventoryService = Depends()):\n    return await service.receive(payload)\n",
  "src/services/inventory_service.py": "\"\"\"Inventory business logic.\"\"\"\nfrom src.repositories.inventory_repository import InventoryRepository\nfrom src.schemas.inventory_schema import StockReceiveRequest, InventoryItemResponse\n\nclass InventoryService:\n    def __init__(self, repo: InventoryRepository):\n        self._repo = repo\n\n    async def receive(self, payload: StockReceiveRequest) -> InventoryItemResponse:\n        item = await self._repo.add_stock(payload.sku, payload.qty, payload.bin_code)\n        return InventoryItemResponse.from_orm(item)\n",
  "Dockerfile": "FROM python:3.12-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install --no-cache-dir -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\\n",
  "README.md": "# Inventory Management API\\n\\nREST API for warehouse stock management.\\n"
}
```

---

## Example 3: Hospital Management System (FastAPI + PostgreSQL, HIPAA)

```json
{
  "src/controllers/patient_controller.py": "\"\"\"Patient records controller (HIPAA-compliant).\"\"\"\nfrom fastapi import APIRouter, Depends, HTTPException\nfrom src.services.patient_service import PatientService\nfrom src.middleware.auth_middleware import get_current_user\nfrom src.middleware.audit_middleware import audit_log\n\nrouter = APIRouter(prefix='/api/v1/patients', tags=['Patients'])\n\n@router.get('/{patient_id}/records')\n@audit_log('read_patient_records')\nasync def get_records(patient_id: int, user=Depends(get_current_user), service: PatientService = Depends()):\n    return await service.get_records_for_patient(patient_id, requesting_user=user)\n",
  "src/middleware/audit_middleware.py": "\"\"\"HIPAA-compliant audit logging middleware.\"\"\"\nimport functools\nimport logging\nfrom datetime import datetime, timezone\n\naudit_logger = logging.getLogger('audit')\n\ndef audit_log(action: str):\n    def decorator(func):\n        @functools.wraps(func)\n        async def wrapper(*args, **kwargs):\n            audit_logger.info({'action': action, 'timestamp': datetime.now(timezone.utc).isoformat()})\n            return await func(*args, **kwargs)\n        return wrapper\n    return decorator\n",
  "Dockerfile": "FROM python:3.12-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\\n",
  "README.md": "# Hospital Management API\\n\\nHIPAA-compliant patient records REST API.\\n"
}
```

---

## Example 4: CRM System (FastAPI + PostgreSQL)

```json
{
  "src/controllers/deal_controller.py": "\"\"\"Deal pipeline controller.\"\"\"\nfrom fastapi import APIRouter, Depends\nfrom src.services.deal_service import DealService\nfrom src.schemas.deal_schema import DealCreateRequest, DealResponse\n\nrouter = APIRouter(prefix='/api/v1/deals', tags=['Deals'])\n\n@router.post('/', response_model=DealResponse)\nasync def create_deal(payload: DealCreateRequest, service: DealService = Depends()):\n    return await service.create(payload)\n",
  "src/services/deal_service.py": "\"\"\"Deal business logic.\"\"\"\nfrom src.repositories.deal_repository import DealRepository\nfrom src.schemas.deal_schema import DealCreateRequest, DealResponse\n\nclass DealService:\n    def __init__(self, repo: DealRepository):\n        self._repo = repo\n\n    async def create(self, payload: DealCreateRequest) -> DealResponse:\n        deal = await self._repo.insert(payload)\n        return DealResponse.from_orm(deal)\n",
  "Dockerfile": "FROM python:3.12-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\"uvicorn\", \"src.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\\n",
  "README.md": "# CRM API\\n\\nCustomer relationship management REST API.\\n"
}
```

---

## Example 5: Generic REST API (FastAPI + SQLite for local dev)

```json
{
  "src/main.py": "\"\"\"FastAPI application entry point.\"\"\"\nfrom fastapi import FastAPI, Request\nfrom fastapi.responses import JSONResponse\nfrom src.routes.router import register_routes\nfrom src.core.exceptions import AppError\nimport logging\n\nlogging.basicConfig(level=logging.INFO, format='{\\\"time\\\": \\\"%(asctime)s\\\", \\\"level\\\": \\\"%(levelname)s\\\", \\\"message\\\": \\\"%(message)s\\\"}')\n\napp = FastAPI(title='REST API', version='1.0.0')\nregister_routes(app)\n\n@app.exception_handler(AppError)\nasync def app_error_handler(request: Request, exc: AppError):\n    return JSONResponse(status_code=exc.status_code, content={'detail': exc.message})\n\n@app.get('/health/liveness')\ndef liveness(): return {'status': 'ok'}\n\n@app.get('/health/readiness')\ndef readiness(): return {'status': 'ok', 'database': 'connected'}\n",
  "src/core/security.py": "\"\"\"JWT token creation and validation.\"\"\"\nfrom jose import jwt, JWTError\nfrom datetime import datetime, timedelta, timezone\nfrom src.config.settings import settings\n\ndef create_access_token(data: dict) -> str:\n    payload = data.copy()\n    payload['exp'] = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)\n    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)\n\ndef decode_jwt(token: str) -> dict | None:\n    try:\n        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])\n    except JWTError:\n        return None\n",
  "tests/test_health.py": "\"\"\"Health endpoint smoke tests.\"\"\"\nfrom fastapi.testclient import TestClient\nfrom src.main import app\n\nclient = TestClient(app)\n\ndef test_liveness():\n    response = client.get('/health/liveness')\n    assert response.status_code == 200\n    assert response.json() == {'status': 'ok'}\n",
  "Dockerfile": "FROM python:3.12-slim AS builder\\nWORKDIR /build\\nCOPY requirements.txt .\\nRUN pip install --no-cache-dir --prefix=/install -r requirements.txt\\n\\nFROM python:3.12-slim\\nWORKDIR /app\\nCOPY --from=builder /install /usr/local\\nCOPY . .\\nEXPOSE 8000\\nCMD [\\\"uvicorn\\\", \\\"src.main:app\\\", \\\"--host\\\", \\\"0.0.0.0\\\", \\\"--port\\\", \\\"8000\\\"]\\n",
  "requirements.txt": "fastapi==0.111.0\\nuvicorn[standard]==0.29.0\\npython-jose[cryptography]==3.3.0\\npytest==8.2.0\\nhttpx==0.27.0\\n",
  "README.md": "# REST API\\n\\nGeneric REST API skeleton.\\n\\n## Running Locally\\n```bash\\nuvicorn src.main:app --reload\\n```\\n\\n## Tests\\n```bash\\npytest tests/ -v\\n```\\n"
}
```
