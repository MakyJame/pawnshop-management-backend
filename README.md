Pawnshop Management Backend
A production-deployed REST API for managing customers, pawn contracts, pawned assets, payments, and contract lifecycle workflows.
Built with FastAPI, PostgreSQL, SQLAlchemy, and Alembic, with automated tests, Docker Compose, Nginx, HTTPS, and Cloudflare.
This project is based on a real-world family pawnshop workflow and focuses on backend business rules rather than CRUD alone.

Overview
The system centralizes pawnshop data and enforces domain rules around contracts, pledged assets, payments, overdue handling, liquidation, redemption, and renewal.
Domain relationships
Customer
   │
   └── Pawn Contract
          ├── Pawn Assets
          └── Payments
A customer can have pawn contracts. A contract contains the pawned assets and its payment history.
Key Features
Customers
- Create, retrieve, and list customers
- Prevent duplicate customer phone numbers
- Validate customer existence before creating contracts
Pawn Contracts
- Create and retrieve pawn contracts
- Generate contract codes server-side
- Calculate due dates automatically
- Restrict client-controlled lifecycle fields
- Enforce contract lifecycle transitions
Supported statuses:
ACTIVE → OVERDUE → LIQUIDATED
Other terminal/workflow states include REDEEMED and RENEWED.
Pawn Assets
- Associate pawned assets with contracts
- Retrieve assets and list assets by contract
- Prevent an actively pawned license plate from being pawned again
Payments and Redemption
- Record interest and principal payments
- Calculate outstanding principal
- Support partial and full principal payments
- Prevent principal overpayment
- Reject payments for invalid contract states
- Provide payment summaries
- Perform formal contract redemption
The system intentionally distinguishes payment history, outstanding principal, and formal redemption. Reaching zero outstanding principal does not automatically mark a contract as REDEEMED; redemption is an explicit business operation.
Renewal and Liquidation
- Detect and refresh overdue contracts
- Enforce a 3-day liquidation grace period
- Renew eligible contracts
- Carry outstanding principal into a renewed contract
- Add additional principal during renewal
- Copy pawned assets to the new contract
- Link renewed contracts through the previous contract
- Prevent invalid operations on terminal contract states
Architecture
The application uses a layered backend structure:
HTTP Request
     │
     ▼
FastAPI + Pydantic
routing / request validation
     │
     ▼
Router
HTTP concerns and error mapping
     │
     ▼
Service
business rules and transaction orchestration
     │
     ▼
Repository
database operations
     │
     ▼
SQLAlchemy
     │
     ▼
PostgreSQL
Project structure
app/
├── api/
│   └── routers/
│       ├── customers.py
│       ├── health.py
│       ├── pawn_assets.py
│       ├── pawn_contracts.py
│       └── payments.py
├── core/
│   └── config.py
├── db/
│   ├── base.py
│   └── session.py
├── models/
│   ├── customer.py
│   ├── pawn_asset.py
│   ├── pawn_contract.py
│   └── payment.py
├── repositories/
│   ├── customer_repository.py
│   ├── pawn_asset_repository.py
│   ├── pawn_contract_repository.py
│   └── payment_repository.py
├── schemas/
│   ├── customer.py
│   ├── pawn_asset.py
│   ├── pawn_contract.py
│   └── payment.py
└── services/
    ├── customer_service.py
    ├── pawn_asset_service.py
    ├── pawn_contract_service.py
    └── payment_service.py
Business Rules
Several values and state transitions are controlled by the backend rather than by API clients.
Due date
due_date = start_date + 1 calendar month
Clients cannot provide their own due_date when creating a contract.
Contract code
Contract codes are generated server-side after the contract receives its database ID.
TL-{YYYYMMDD}-{contract_id}
Overdue handling
A contract becomes overdue when its due date is earlier than the current date. A contract due today is not yet overdue.
Liquidation
An overdue contract cannot be liquidated immediately. The service enforces a 3-day grace period before liquidation is allowed.
Principal payments
Principal payments reduce outstanding principal. A payment greater than the remaining principal is rejected.
Redemption
Redemption is an explicit workflow. If outstanding principal remains, the redemption amount must match the outstanding amount.
Renewal
Renewal creates a new contract, links it to the previous contract, carries forward outstanding principal, optionally adds additional principal, and copies the pawned assets.
API Endpoints
Health
GET  /health
GET  /health/db
Customers
POST /customers
GET  /customers
GET  /customers/{customer_id}
Pawn Contracts
POST  /pawn-contracts
POST  /pawn-contracts/with-assets
GET   /pawn-contracts/{contract_id}
PATCH /pawn-contracts/{contract_id}

POST  /pawn-contracts/refresh-overdue
POST  /pawn-contracts/{contract_id}/liquidate
POST  /pawn-contracts/{contract_id}/renew
POST  /pawn-contracts/{contract_id}/redeem
Pawn Assets
POST /pawn-assets
GET  /pawn-assets/{asset_id}
GET  /pawn-contracts/{contract_id}/assets
Payments
POST /payments
GET  /payments/{payment_id}
GET  /pawn-contracts/{contract_id}/payments
GET  /pawn-contracts/{contract_id}/payment-summary
Testing
The project has automated tests covering API behavior and domain rules, including:
- customer validation
- duplicate active license plates
- contract creation and server-controlled fields
- overdue and liquidation rules
- lifecycle transition restrictions
- principal and interest payments
- outstanding-principal calculations
- redemption
- renewal
Run the suite:
pytest -q
Current verified result:
85 passed
Tech Stack
Area	Technology
API	Python 3.12, FastAPI, Pydantic
Database	PostgreSQL 16
ORM	SQLAlchemy
Migrations	Alembic
Testing	pytest
Containers	Docker, Docker Compose
Reverse proxy	Nginx
HTTPS / DNS proxy	Cloudflare
Hosting	Vultr VPS


Local Development
1. Clone the repository
git clone git@github.com:MakyJame/pawnshop-management-backend.git
cd pawnshop-management-backend
2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Configure environment variables
Create .env from the included example:
cp .env.example .env
Update the values for your local PostgreSQL environment. Do not commit real secrets.
4. Start PostgreSQL
docker compose up -d db
5. Run migrations
alembic upgrade head
6. Start the API
uvicorn app.main:app --reload
Open:
http://127.0.0.1:8000/docs
7. Run tests
Configure TEST_DATABASE_URL for a dedicated test database, then run:
pytest -q
The test setup recreates database tables. Use a dedicated test database, not a production database.

Production Deployment
The application is deployed on a Vultr VPS using Docker Compose.
Internet
   │
   ▼
Cloudflare
   │ HTTPS
   ▼
Nginx :443
   │
   ▼
FastAPI container
127.0.0.1:8000
   │
   ▼
Docker network
   │
   ▼
PostgreSQL container
Production design:
- Nginx is the public reverse proxy
- FastAPI is published only on 127.0.0.1:8000 on the VPS
- PostgreSQL has no public host port
- UFW allows only the required public services
- HTTPS is used between clients, Cloudflare, and the origin
- production secrets are kept outside Git
Production API:
https://api.camdotuanly.site
FastAPI documentation:
https://api.camdotuanly.site/docs
Current Scope
The current backend MVP focuses on the core pawnshop domain and production deployment.
Authentication and authorization are not implemented yet and are intentionally not presented as completed features.
Potential next improvements:
- authentication and role-based authorization
- CI/CD automation
- concurrency protection for financial operations
- monitoring and alerting
- automated database backups
License
MIT
