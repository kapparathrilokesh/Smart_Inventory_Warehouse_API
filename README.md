# Smart Inventory & Warehouse Management API

## Overview

A backend API built with FastAPI and MySQL to manage inventory and warehouse operations. It provides authentication, role-based access control, product and warehouse management, stock tracking, purchase and sales orders, stock reservations, reporting, and audit logs.

## Technology Stack

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- MySQL
- Alembic
- JWT authentication
- Pytest
- Uvicorn

## Features

- User registration, login, JWT authentication, and role-based access
- Category and product management
- Warehouse and supplier management
- Customer management
- Inventory tracking and stock movements
- Purchase order creation, approval, and receiving
- Sales order confirmation, dispatch, and delivery
- Stock reservation and release
- Low-stock reporting
- Audit log retrieval

## Project Setup

### 1. Clone or download the project

Open a terminal in the project directory.

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file using `.env.example` as a reference.

Set the MySQL connection details and authentication settings in `.env`. Do not upload `.env` or share its secrets.

### 5. Create the database

Create a MySQL database named `smart_inventory_db`, or use the database name configured in your `.env` file.

### 6. Apply database migrations

```powershell
alembic upgrade head
```

### 7. Start the API

```powershell
uvicorn app.main:app --reload
```

## API Documentation

When the application is running, open:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

Use Swagger UI to test the available endpoints.

## Running Tests

Run the automated test suite with:

```powershell
pytest -v
```

Review the test results before reporting the project as fully tested.

## Database Migrations

To create a new migration after model changes:

```powershell
alembic revision --autogenerate -m "describe your changes"
```

Review the generated migration before applying it:

```powershell
alembic upgrade head
```

## Security Notes

- Keep `.env` out of source control.
- Use a strong secret key for JWT authentication.
- Use role-based authorization for protected operations.
- Do not commit passwords, access tokens, or SMTP credentials.

## Project Status

The core inventory and warehouse endpoints have been implemented and tested in Swagger. Stock reservation creation and release, low-stock reporting, and reservation audit logging have also been verified. Additional assignment requirements and automated tests should be reviewed before final submission.