# 🔧 OpsCraft

> A modern, secure platform for managing and executing infrastructure automation scripts with real-time monitoring, secret management, and role-based access control.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Security](#security)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**OpsCraft** is an enterprise-grade platform designed to streamline the execution and management of infrastructure automation scripts. Built with security and scalability in mind, it provides a centralized interface for DevOps teams to manage Bash, Python, Ansible, and Terraform scripts with comprehensive audit trails and real-time execution monitoring.

### Key Capabilities

- **Multi-Language Support**: Execute Bash, Python, Ansible, and Terraform scripts
- **Secure Execution**: Docker-isolated script execution with resource limits
- **Secret Management**: AES-256 encrypted secrets with audit logging
- **Real-Time Monitoring**: WebSocket-based live execution logs
- **Role-Based Access Control**: Three-tier permission system (Admin/Operator/Viewer)
- **RESTful API**: Comprehensive API with OpenAPI documentation
- **Modern UI**: React-based responsive interface with real-time updates

---

## ✨ Features

### 🔐 Security First

- **Encrypted Secret Storage**: AES-256 encryption with dynamic salt generation
- **Audit Logging**: Complete trail of secret access and script executions
- **Docker Isolation**: Scripts run in isolated containers with resource limits
- **Input Validation**: Comprehensive sanitization and validation
- **Rate Limiting**: Redis-backed rate limiting to prevent abuse
- **JWT Authentication**: Secure token-based authentication with refresh tokens

### 📝 Script Management

- **Version Control**: Track script versions and changes
- **Parameter Schema**: Define and validate script parameters
- **Tags & Metadata**: Organize scripts with tags and descriptions
- **Status Management**: Draft, Active, Deprecated lifecycle states
- **Search & Filter**: Quick script discovery with filtering

### ⚡ Execution Engine

- **Asynchronous Execution**: Celery-based distributed task queue
- **Real-Time Logs**: WebSocket streaming of execution output
- **Execution History**: Complete audit trail of all executions
- **Cancellation Support**: Stop running executions
- **Resource Limits**: Memory and CPU constraints per execution

### 👥 User Management

- **Role-Based Access**: Admin, Operator, and Viewer roles
- **User Administration**: Complete user lifecycle management
- **Activity Tracking**: Last login and activity monitoring
- **Self-Service**: Password change and profile management

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Dashboard │  │ Scripts  │  │Executions│  │ Secrets  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/WebSocket
┌────────────────────────┴────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Auth   │  │  Scripts │  │Executions│  │ Secrets  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │   Admin  │  │WebSocket │  │  Health  │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
└────────────────┬───────────────────┬───────────────────────────┘
                 │                   │
        ┌────────┴────────┐  ┌──────┴──────┐
        │   PostgreSQL    │  │    Redis    │
        │   (Database)    │  │ (Cache/Pub) │
        └─────────────────┘  └─────┬───────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │    Celery Worker              │
                    │  ┌──────────────────────┐    │
                    │  │  Executor Service    │    │
                    │  │  ┌────────────────┐  │    │
                    │  │  │  Bash/Python   │  │    │
                    │  │  │  Ansible/TF    │  │    │
                    │  │  └────────────────┘  │    │
                    │  └──────────────────────┘    │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │         Docker Engine         │
                    │  ┌────────────────────────┐  │
                    │  │  Isolated Containers   │  │
                    │  │  - alpine:latest       │  │
                    │  │  - python:3.11-alpine  │  │
                    │  │  - ansible/ansible     │  │
                    │  │  - hashicorp/terraform │  │
                    │  └────────────────────────┘  │
                    └───────────────────────────────┘
```

### Component Breakdown

#### Frontend (React)
- **Framework**: React 18 with TypeScript
- **State Management**: React Query (TanStack Query)
- **Routing**: React Router v6
- **HTTP Client**: Axios with interceptors
- **WebSocket**: Native WebSocket with reconnection logic
- **UI Components**: Custom components with CSS modules

#### Backend (FastAPI)
- **API Framework**: FastAPI with Pydantic validation
- **ORM**: SQLAlchemy 2.0 with async support
- **Authentication**: JWT tokens with refresh mechanism
- **Security**: Input validation, rate limiting, CORS
- **WebSocket**: FastAPI WebSocket with Redis Pub/Sub bridge

#### Task Queue (Celery)
- **Broker**: Redis
- **Result Backend**: Redis
- **Executor**: Custom Docker-based execution strategies
- **Monitoring**: Real-time log streaming via Redis Pub/Sub

#### Database (PostgreSQL)
- **Version**: 15
- **Connection Pooling**: SQLAlchemy pool
- **Migrations**: Alembic (ready, not configured in repo)

#### Cache & Pub/Sub (Redis)
- **Version**: 7
- **Use Cases**: Rate limiting, Celery broker, WebSocket Pub/Sub
- **Persistence**: Configured for data durability

---

## 💻 Technology Stack

### Backend
- **Python 3.12**
- **FastAPI 0.104** - High-performance async web framework
- **SQLAlchemy 2.0** - SQL toolkit and ORM
- **Celery 5.3** - Distributed task queue
- **Redis 5.0** - Cache and message broker
- **PostgreSQL 15** - Relational database
- **Docker SDK** - Container management for script execution
- **Cryptography** - AES-256 encryption for secrets
- **python-jose** - JWT token handling
- **Passlib** - Password hashing with bcrypt

### Frontend
- **React 18.2** - UI library
- **TypeScript 5.3** - Type-safe JavaScript
- **React Query (TanStack)** - Server state management
- **Axios** - HTTP client
- **React Router 6** - Client-side routing
- **WebSocket API** - Real-time communication

### DevOps & Infrastructure
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy and static file serving
- **Make** - Build automation
- **GitHub Actions** - CI/CD (ready for configuration)

---

## 📦 Prerequisites

### Required Software

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Make** (optional, for convenience commands)
- **Git**

### System Requirements

- **RAM**: Minimum 4GB, recommended 8GB+
- **CPU**: 2+ cores recommended
- **Disk**: 10GB+ free space
- **OS**: Linux, macOS, or Windows with WSL2

---

## 🚀 Installation

### Quick Start (Docker Compose)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/opscraft.git
   cd opscraft
   ```

2. **Configure Environment**
   ```bash
   cp .env.template .env
   ```
   
   Edit `.env` with your configuration:
   ```bash
   ENVIRONMENT=dev
   BACKEND_URL=http://localhost:8000
   FRONTEND_URL=http://localhost:3000
   
   DB_USER=devops
   DB_PASS=your_secure_password
   DB_HOST=db
   DB_PORT=5432
   DB_NAME=ops_craft
   
   REDIS_HOST=redis
   REDIS_PORT=6379
   
   SECRET_KEY=your_super_secret_key_here_min_32_chars
   ```

3. **Build and Start**
   ```bash
   make build
   make up
   ```
   
   Or without Make:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Access the Application**
   - **Frontend**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **API ReDoc**: http://localhost:8000/redoc

5. **Create First User**
   ```bash
   # The first registered user becomes admin
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin",
       "email": "admin@example.com",
       "password": "SecurePass123",
       "full_name": "System Administrator"
     }'
   ```

### Manual Installation (Development)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/opscraft"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-secret-key"

# Run migrations (if configured)
# alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker
celery -A app.tasks.executor:celery_app worker --loglevel=info
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env
echo "REACT_APP_WS_URL=ws://localhost:8000" >> .env

# Start development server
npm start
```

---

## ⚙️ Configuration

### Environment Variables

#### Core Settings
```bash
ENVIRONMENT=dev|staging|production
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

#### Database
```bash
DB_USER=devops
DB_PASS=secure_password
DB_HOST=db
DB_PORT=5432
DB_NAME=ops_craft
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
```

#### Redis
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}/0
```

#### Celery
```bash
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
```

#### Security
```bash
SECRET_KEY=minimum_32_character_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Script Storage
```bash
SCRIPT_STORAGE_PATH=/app/scripts/
```

#### CORS
```bash
CORS_ORIGINS='["${FRONTEND_URL}","http://localhost","http://localhost:8000"]'
```

### Docker User Configuration
```bash
APP_USER=ops_craft
APP_GROUP=ops_craft
APP_GID=1001
APP_UID=1001
```

---

## 📖 Usage

### User Roles & Permissions

| Role         | View Scripts | Execute Scripts | Create/Edit Scripts | Manage Secrets | Manage Users |
| ------------ | ------------ | --------------- | ------------------- | -------------- | ------------ |
| **Viewer**   | ✅            | ✅               | ❌                   | ❌              | ❌            |
| **Operator** | ✅            | ✅               | ✅                   | ✅              | ❌            |
| **Admin**    | ✅            | ✅               | ✅                   | ✅              | ✅            |

### Creating a Script

1. Navigate to **Scripts** → **Create New Script**
2. Fill in the form:
   - **Name**: Unique identifier
   - **Description**: What the script does
   - **Type**: bash, python, ansible, or terraform
   - **Content**: The actual script code
   - **Parameters**: JSON schema for input parameters
   - **Tags**: For organization

3. Example Bash Script:
   ```bash
   #!/bin/bash
   echo "Hello, $NAME!"
   echo "Environment: $ENVIRONMENT"
   ```

4. Example Parameters Schema:
   ```json
   {
     "NAME": "World",
     "ENVIRONMENT": "production"
   }
   ```

### Managing Secrets

1. Navigate to **Secrets**
2. Click **Add Secret**
3. Provide:
   - **Name**: Environment variable name (e.g., `API_KEY`)
   - **Value**: The secret value (encrypted at rest)
   - **Description**: Purpose of the secret

4. Attach secrets to scripts:
   - Open script details
   - Click **Manage Secrets**
   - Select secrets to attach
   - Secrets are injected as environment variables during execution

### Executing Scripts

1. Navigate to script details
2. Click **Execute**
3. Provide runtime parameters (JSON format)
4. Monitor execution in real-time via WebSocket
5. View results and logs after completion

### Viewing Execution History

1. Navigate to **Executions**
2. Filter by:
   - Script ID
   - Status (pending, running, success, failed)
   - Date range
3. Click execution to view:
   - Complete logs
   - Parameters used
   - Execution time
   - Exit code

---

## 🔌 API Documentation

### Authentication

#### Register User
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "full_name": "John Doe"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePass123"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Get Current User
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### Scripts

#### List Scripts
```http
GET /api/v1/scripts?search=deploy&script_type=bash&status=active
Authorization: Bearer <access_token>
```

#### Create Script
```http
POST /api/v1/scripts
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "deploy-app",
  "description": "Deploy application",
  "script_type": "bash",
  "content": "#!/bin/bash\necho 'Deploying...'",
  "parameters": {"ENV": "prod"},
  "version": "1.0.0",
  "tags": ["deployment", "production"]
}
```

#### Get Script
```http
GET /api/v1/scripts/{script_id}
Authorization: Bearer <access_token>
```

#### Update Script
```http
PUT /api/v1/scripts/{script_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "description": "Updated description",
  "status": "active"
}
```

#### Delete Script
```http
DELETE /api/v1/scripts/{script_id}
Authorization: Bearer <access_token>
```

### Executions

#### Create Execution
```http
POST /api/v1/executions
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "script_id": 1,
  "parameters": {
    "ENV": "production",
    "VERSION": "2.0.1"
  }
}
```

#### List Executions
```http
GET /api/v1/executions?script_id=1&limit=50
Authorization: Bearer <access_token>
```

#### Get Execution Details
```http
GET /api/v1/executions/{execution_id}
Authorization: Bearer <access_token>
```

#### Cancel Execution
```http
POST /api/v1/executions/{execution_id}/cancel
Authorization: Bearer <access_token>
```

### Secrets

#### Create Secret
```http
POST /api/v1/secrets
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "DATABASE_PASSWORD",
  "value": "super_secret_password",
  "description": "Production database password"
}
```

#### List Secrets
```http
GET /api/v1/secrets
Authorization: Bearer <access_token>
```

#### Attach Secret to Script
```http
POST /api/v1/scripts/{script_id}/secrets/{secret_id}
Authorization: Bearer <access_token>
```

#### Get Secret Audit Logs
```http
GET /api/v1/secrets/{secret_id}/audit-logs
Authorization: Bearer <access_token>
```

### WebSocket

#### Connect to Execution Logs
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(
  `ws://localhost:8000/ws/executions/${executionId}?token=${token}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.content);
};
```

---

## 🔒 Security

### Authentication & Authorization

- **JWT Tokens**: Access tokens expire in 30 minutes, refresh tokens in 7 days
- **Password Hashing**: Bcrypt with automatic salt generation
- **Role-Based Access Control**: Three-tier permission system
- **Rate Limiting**: 60 requests/minute for general endpoints, 5 for auth

### Secret Management

- **Encryption**: AES-256 with dynamic salt per secret
- **Audit Trail**: Every secret access is logged with user, timestamp, execution ID
- **Secure Injection**: Secrets injected as environment variables at runtime
- **No Retrieval**: Once created, secrets cannot be read via API (view only)

### Script Execution Security

#### Docker Isolation
```python
# Container configuration
{
    'mem_limit': '512m',
    'nano_cpus': 500_000_000,  # 0.5 CPU
    'network_disabled': True,   # No network access
    'read_only': True,          # Read-only filesystem
    'tmpfs': {'/tmp': 'rw,noexec,nosuid,size=100m'},
    'security_opt': ['no-new-privileges']
}
```

#### Dangerous Pattern Detection
- `rm -rf /`
- `dd if=/dev/`
- Fork bombs
- Unrestricted curl/wget pipes
- Direct disk access

### Input Validation

- **Script Content**: Size limits, pattern detection, syntax checking
- **JSON Payloads**: Depth and key count limits
- **User Input**: XSS prevention, SQL injection protection
- **File Paths**: Path traversal prevention

### Network Security

- **CORS**: Configured allowed origins
- **Security Headers**: X-Frame-Options, X-Content-Type-Options, CSP
- **TLS**: HTTPS recommended for production

---

## 🛠️ Development

### Project Structure

```
opscraft/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/       # API endpoints
│   │   │   └── dependencies.py
│   │   ├── core/             # Core utilities
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── websocket_bridge.py
│   │   ├── db/               # Database
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── executor_service.py
│   │   │   ├── encryption_service.py
│   │   │   └── secret_service.py
│   │   ├── tasks/            # Celery tasks
│   │   │   └── executor.py
│   │   └── main.py           # FastAPI app
│   ├── tests/                # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   ├── contexts/         # React contexts
│   │   ├── hooks/            # Custom hooks
│   │   ├── pages/            # Page components
│   │   ├── services/         # API services
│   │   ├── styles/           # CSS files
│   │   ├── utils/            # Utilities
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── Makefile
└── .env.template
```

### Code Style

#### Backend (Python)
- **Style Guide**: PEP 8
- **Linting**: Ruff, Black, MyPy (configured in requirements)
- **Type Hints**: Required for all functions
- **Docstrings**: Google style

#### Frontend (TypeScript/React)
- **Style Guide**: Airbnb React
- **Linting**: ESLint
- **Formatting**: Prettier (not configured)
- **Components**: Functional components with hooks

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make Changes**
   - Follow code style guidelines
   - Add tests for new features
   - Update documentation

3. **Run Tests**
   ```bash
   make test
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature
   ```

### Make Commands

```bash
# Build
make build              # Build all Docker images

# Start/Stop
make up                 # Start all services
make down               # Stop all services
make restart            # Restart all services

# Logs
make logs               # View all logs
make logs-backend       # Backend logs only
make logs-frontend      # Frontend logs only
make logs-celery        # Celery worker logs

# Testing
make test               # Run all tests
make backend-test       # Backend tests
make frontend-test      # Frontend tests

# Database
make db-shell           # PostgreSQL shell
make migrate            # Run migrations
make migrate-create     # Create new migration

# Utilities
make backend-shell      # Backend container shell
make redis-cli          # Redis CLI
make clean              # Clean containers and volumes
```

---

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
docker-compose exec backend pytest tests/ -v

# Run with coverage
docker-compose exec backend pytest tests/ --cov=app --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py -v

# Run specific test
docker-compose exec backend pytest tests/test_auth.py::TestAuthentication::test_login_success -v
```

### Frontend Tests

```bash
# Run all tests
docker-compose exec frontend_dev npm test -- --watchAll=false

# Run with coverage
docker-compose exec frontend_dev npm test -- --coverage --watchAll=false

# Run specific test file
docker-compose exec frontend_dev npm test Button.test.tsx
```

### Test Coverage

Current test coverage includes:
- ✅ Authentication flow
- ✅ Script CRUD operations
- ✅ Execution management
- ✅ Security utilities
- ✅ UI components
- 🚧 WebSocket connections (partial)
- 🚧 Celery tasks (partial)

---

## 🚢 Deployment

### Production Deployment with Docker Compose

1. **Configure Production Environment**
   ```bash
   cp .env.template .env.production
   # Edit .env.production with production settings
   ```

2. **Build Production Images**
   ```bash
   docker-compose -f docker-compose.yml build
   ```

3. **Start Services**
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

4. **Configure Reverse Proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name opscraft.example.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name opscraft.example.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /ws {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

### Kubernetes Deployment

Kubernetes manifests are prepared in `infra/kubernetes/` directory (currently empty, ready for configuration).

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Monitoring

#### Application Logs
```bash
# Centralized logging
docker-compose logs -f backend celery_worker

# Structured JSON logs
tail -f backend/logs/opscraft.log
```

#### Metrics (to be implemented)
- Prometheus exporters
- Grafana dashboards
- Alert rules

---

## 🐛 Troubleshooting

### Common Issues

#### Docker Socket Permission Denied
```bash
# Solution: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Database Connection Errors
```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Reset database
docker-compose down -v
docker-compose up -d db
```

#### Redis Connection Errors
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Should respond: PONG
```

#### Celery Worker Not Processing Tasks
```bash
# Check Celery logs
docker-compose logs celery_worker

# Restart worker
docker-compose restart celery_worker

# Verify Redis connection
docker-compose exec celery_worker python -c "from app.core.config import settings; import redis; redis.from_url(settings.REDIS_URL).ping()"
```

#### WebSocket Connection Failed
```bash
# Check if token is valid
# Ensure CORS is configured correctly
# Verify WebSocket URL format
ws://localhost:8000/ws/executions/{id}?token={jwt_token}
```

#### Script Execution Fails
```bash
# Check Docker daemon
docker ps

# Check execution logs
docker-compose logs celery_worker | grep ERROR

# Verify script content validation
# Check resource limits
```

### Debug Mode

Enable debug logging:
```bash
# Backend
export LOG_LEVEL=DEBUG
docker-compose restart backend

# Frontend
REACT_APP_DEBUG=true npm start
```

### Performance Issues

1. **Slow API Responses**
   - Check database query performance
   - Enable query logging in SQLAlchemy
   - Add database indexes

2. **High Memory Usage**
   - Adjust Docker memory limits
   - Monitor Celery worker memory
   - Check for memory leaks in long-running tasks

3. **WebSocket Disconnections**
   - Increase keepalive timeout
   - Check network stability
   - Review Redis Pub/Sub configuration

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Reporting Bugs

Use GitHub Issues with the bug template:
- Describe the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Logs and screenshots

### Requesting Features

Use GitHub Issues with the feature request template:
- Problem description
- Proposed solution
- Alternative solutions considered
- Additional context

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Write/update tests
5. Update documentation
6. Push to your fork
7. Create a Pull Request

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass and coverage maintained
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Dung Dang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👥 Authors & Contributors

- **Dung Dang** - *Initial work* - [GitHub Profile](https://github.com/dungdang39)

See also the list of [contributors](https://github.com/yourusername/opscraft/contributors) who participated in this project.

---

## 🙏 Acknowledgments

- FastAPI team for the amazing web framework
- React team for the UI library
- Celery project for distributed task processing
- Docker for containerization platform
- All open-source contributors

---

## 📞 Support

- **Documentation**: [docs.opscraft.io](https://docs.opscraft.io) (to be published)
- **Issues**: [GitHub Issues](https://github.com/yourusername/opscraft/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/opscraft/discussions)
- **Email**: support@opscraft.io (to be configured)

---

## 🗺️ Roadmap

### Version 1.1 (Q2 2025)
- [ ] Kubernetes deployment manifests
- [ ] Terraform deployment templates
- [ ] Prometheus metrics integration
- [ ] Grafana dashboards
- [ ] Script version history and rollback
- [ ] Scheduled executions (cron-like)

### Version 1.2 (Q3 2025)
- [ ] Multi-tenancy support
- [ ] LDAP/SSO integration
- [ ] Advanced RBAC with custom roles
- [ ] Script approval workflow
- [ ] Notification system (email, Slack, webhook)
- [ ] Execution templates

### Version 2.0 (Q4 2025)
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] Plugin system
- [ ] Script marketplace
- [ ] AI-powered script generation
- [ ] Advanced analytics and reporting

---

## 📊 Project Status

- **Current Version**: 0.1.0
- **Status**: Beta
- **Last Updated**: January 2025
- **Active Development**: Yes

### Build Status
- Backend: ![Backend Status](https://img.shields.io/badge/build-passing-brightgreen)
- Frontend: ![Frontend Status](https://img.shields.io/badge/build-passing-brightgreen)
- Tests: ![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
- Coverage: ![Coverage](https://img.shields.io/badge/coverage-75%25-yellow)

---

## 🔄 Changelog

### [0.1.0] - 2025-01-XX

#### Added
- Initial release
- Multi-language script support (Bash, Python, Ansible, Terraform)
- Docker-isolated execution environment
- AES-256 encrypted secret management
- Real-time execution logs via WebSocket
- Role-based access control (Admin/Operator/Viewer)
- RESTful API with OpenAPI documentation
- React-based responsive UI
- JWT authentication with refresh tokens
- Comprehensive audit logging
- Rate limiting and input validation
- Celery-based asynchronous task processing

#### Security
- Input validation and sanitization
- Dangerous pattern detection
- Docker container isolation with resource limits
- Encrypted secret storage
- Security headers implementation

---

## 📖 Additional Documentation

### For Developers
- [API Reference](docs/api-reference.md) (to be created)
- [Architecture Guide](docs/architecture.md) (to be created)
- [Development Setup](docs/development.md) (to be created)
- [Testing Guide](docs/testing.md) (to be created)

### For Users
- [User Guide](docs/user-guide.md) (to be created)
- [Script Writing Best Practices](docs/best-practices.md) (to be created)
- [Secret Management Guide](docs/secrets.md) (to be created)

### For Operators
- [Deployment Guide](docs/deployment.md) (to be created)
- [Operations Manual](docs/operations.md) (to be created)
- [Monitoring & Alerting](docs/monitoring.md) (to be created)
- [Backup & Recovery](docs/backup.md) (to be created)

---

## ⚠️ Security Considerations

### Before Production Deployment

1. **Change Default Credentials**
   - Generate strong `SECRET_KEY` (min 32 characters)
   - Use strong database passwords
   - Rotate secrets regularly

2. **Enable HTTPS**
   - Configure SSL/TLS certificates
   - Use Let's Encrypt for free certificates
   - Enable HSTS headers

3. **Configure Firewall**
   - Restrict access to ports 5432, 6379
   - Only expose 80/443 publicly
   - Use VPN for administrative access

4. **Regular Updates**
   - Keep Docker images updated
   - Monitor security advisories
   - Apply security patches promptly

5. **Backup Strategy**
   - Regular database backups
   - Secret key backup (encrypted)
   - Disaster recovery plan

6. **Monitoring & Alerting**
   - Failed login attempts
   - Unusual execution patterns
   - Resource exhaustion
   - Security events

### Reporting Security Vulnerabilities

Please report security vulnerabilities to: security@opscraft.io (to be configured)

**Do not** open public GitHub issues for security vulnerabilities.

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/opscraft&type=Date)](https://star-history.com/#yourusername/opscraft&Date)

---

**Made with ❤️ by the OpsCraft team**