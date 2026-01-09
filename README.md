# BookIt API

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Latest-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A comprehensive REST API for a modern booking platform called **BookIt**. This API enables users to browse services, make bookings, leave reviews, and provides full administrative capabilities for managing the platform.

##  Features

### Core Functionality
- **User Management**: Registration, authentication, profile management
- **Service Management**: Browse, search, and manage service offerings
- **Booking System**: Complete booking lifecycle with status management
- **Review System**: Rate and review services after booking completion
- **Admin Panel**: Full administrative control over users, services, and bookings

### Key Highlights
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: User and Admin roles with appropriate permissions
- **Database Migrations**: Alembic integration for schema versioning
- **Professional Logging**: Structured logging throughout the application
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Data Validation**: Robust input validation with Pydantic schemas

##  Architecture

### Tech Stack
- **Framework**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (SQLite for testing)
- **ORM**: SQLAlchemy 2.0
- **Authentication**: JWT tokens with bcrypt password hashing
- **Migration**: Alembic
- **Documentation**: OpenAPI/Swagger UI

### Project Structure
```
BookIt-API/
├── alembic/                 # Database migrations
├── services/                    # CRUD operations
│   ├── booking_crud.py
│   ├── review_crud.py
│   ├── service_crud.py
│   └── user_crud.py
├── models/                  # SQLAlchemy models
│   ├── booking_model.py
│   ├── review_model.py
│   ├── service_model.py
│   ├── token_blacklist.py
│   └── user_model.py
├── routes/                 # API route handlers
│   ├── booking_route.py
│   ├── review_route.py
│   ├── service_route.py
│   └── user_route.py
├── schemas/                 # Pydantic schemas
│   ├── booking_schema.py
│   ├── review_schema.py
│   ├── service_schema.py
│   └── user_schema.py
├── security/                # Authentication & authorization
├── utils/                   # App Utilities
├── tests/                   # Comprehensive test suite
├── database.py              # Databse Configuration
├── middleware.py            # Custom Middleware
└── main.py                  # Application entry point
```

##  Prerequisites

- Python 3.13+
- PostgreSQL (for production)
- pip or pipenv for dependency management

##  How to Start

### 1. Clone the Repository
```bash
git clone https://github.com/esther-anierobi/BookIT.git
cd BookIT
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv menv

# Activate virtual environment
# On Windows:
menv\Scripts\activate
# On macOS/Linux:
source menv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create an .env file with values on .env.example file

### 5. Set Up Database
```bash
# Run migrations
alembic upgrade head
```

### 6. Run the Application
```bash
# Development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 7. Access the API
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive SwaggerUI Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
