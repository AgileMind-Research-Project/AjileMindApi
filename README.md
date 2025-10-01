# AgileMind – Backend Server (Node.js + Express)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green)](https://nodejs.org/)
[![Express](https://img.shields.io/badge/Express-4.x-orange)](https://expressjs.com/)
[![SaaS](https://img.shields.io/badge/SaaS-Multi--tenant-brightgreen)](https://en.wikipedia.org/wiki/Software_as_a_service)

**AgileMind** is an AI-powered, cloud-native SaaS platform that automates Agile ceremonies (sprint planning, daily standups, retrospectives) and provides intelligent project governance. This repository contains the **Node.js + Express backend** responsible for user management, multi-tenant isolation, project story CRUD, JWT authentication, Redis-based logout, AI proxy integration, and secure API exposure.

> 📌 **Aligned with IT4010 Research Project – 2025 (Project ID: 25-26J-508)**  
> *"Transforming Agile from reactive to proactive through Cross-Component Intelligence and Conversational Feedback Loops."*

---

## ✨ Features

- ✅ **Multi-tenant SaaS architecture** with `X-Tenant-ID` header isolation
- 🔐 **Secure authentication**: JWT (15m expiry) + Refresh Token (7d) + Redis blacklist
- 🗃️ **Project Story Management**: Create, Read, Update, Delete (CRUD) with tenant scoping
- 🤖 **AI Proxy**: Forward meeting transcripts to Python AI Engine for NLP processing
- 📊 **Swagger API Docs**: Auto-generated OpenAPI 3.0 documentation
- 🛡️ **Security Hardening**: Helmet, CORS, Rate Limiting, bcrypt, SQL injection protection (Sequelize ORM)
- 📦 **Docker & Docker Compose**: Ready for local development and production deployment
- 📝 **Structured Logging**: Winston-based JSON logging with file + console output
- 🌐 **Enterprise Compliance**: Follows ISO/IEC 27001:2022 principles (audit-ready design)

---

## 🗂️ Tech Stack

| Layer | Technology |
|------|------------|
| Runtime | Node.js 18+ |
| Framework | Express.js |
| Database | MySQL 8.0 |
| ORM | Sequelize |
| Auth | JWT + bcrypt + Redis |
| Caching/Logout | Redis |
| AI Integration | Axios (HTTP proxy to Python AI Engine) |
| Logging | Winston |
| API Docs | Swagger UI + swagger-jsdoc |
| Containerization | Docker, Docker Compose |

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Node.js ≥ 18
- npm ≥ 9
- Docker & Docker Compose (optional but recommended)

### 1. Clone & Install
```bash
git clone https://github.com/your-org/agilemind-backend.git
cd agilemind-backend
npm install
```

### 2. Environment Setup
Create a `.env` file in the `backend/` root:
```env
NODE_ENV=development
PORT=5000

# JWT Secrets (use strong random strings in production!)
JWT_SECRET=your_strong_256bit_jwt_secret_here_2025!
REFRESH_SECRET=your_strong_refresh_secret_here_2025!

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=agilemind_saas

# Redis
REDIS_URL=redis://localhost:6379

# AI Engine (Python microservice)
AI_SERVICE_URL=http://localhost:8000

# Frontend
FRONTEND_URL=http://localhost:3000
```

### 3. Start Services (with Docker Compose)
```bash
# Starts MySQL, Redis, and Backend
docker-compose up --build
```

> 💡 **Note**: The `ai-engine` service must be running separately (see `ai-engine/` repo).

### 4. Manual Start (without Docker)
```bash
# Ensure MySQL & Redis are running locally
npm run dev  # Uses nodemon for auto-restart
```

### 5. Access APIs
- **Base URL**: `http://localhost:5000/api`
- **Swagger Docs**: `http://localhost:5000/api-docs`
- **Auth Endpoints**: `/api/auth/register`, `/api/auth/login`
- **Story Endpoints**: `/api/stories`
- **AI Endpoints**: `/api/ai/standup`

---

## 🔐 Authentication Flow

1. **Register**:  
   `POST /api/auth/register`  
   Headers: `X-Tenant-ID: <UUID>`  
   Body: `{ "email": "...", "password": "..." }`

2. **Login**:  
   `POST /api/auth/login` → Returns `accessToken` + `refreshToken` (in HTTP-only cookie)

3. **Access Protected Routes**:  
   Include `Authorization: Bearer <accessToken>` header

4. **Logout**:  
   `POST /api/auth/logout` → Revokes refresh token via Redis blacklist

---

## 🏗️ Project Structure

```
src/
├── config/          # DB, Redis, env
├── controllers/     # Auth, Story, AI logic
├── middleware/      # Auth, tenant, security
├── models/          # Sequelize models (User, ProjectStory)
├── routes/          # API route definitions
├── services/        # AI proxy, external integrations
├── utils/           # Logger, helpers
├── swagger/         # OpenAPI spec
└── app.js           # Express app factory
server.js            # Entry point
```

---

## 🧪 Testing & Quality

```bash
npm run lint        # ESLint checks
npm run lint:fix    # Auto-fix lint issues
npm run format      # Prettier code formatting
```

> ✅ **Code Quality**: Enforced via ESLint + Prettier  
> ✅ **Error Handling**: Centralized + logged via Winston  
> ✅ **Input Validation**: Sequelize model constraints + manual checks

---

## 📦 Deployment

### Docker (Production)
```dockerfile
# Multi-stage build recommended for production
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
CMD ["node", "server.js"]
```

### Environment Variables (Production)
- Use **strong secrets** for `JWT_SECRET` and `REFRESH_SECRET`
- Set `NODE_ENV=production`
- Restrict `FRONTEND_URL` to your domain (e.g., `https://app.agilemind.com`)
- Use managed MySQL/Redis services (AWS RDS, ElastiCache, etc.)

---

Got it ✅
Since your README already has **MySQL** and **AI Engine** sections, I’ll generate a **Redis section** in the same style. This will explain **what Redis is used for (token blacklist / caching)**, how to run it (Docker / local / cloud), and how to configure it.

Here’s the **Redis section** you can directly add into your `README.md`:

---

## 🔄 Redis Setup

Redis is used in **AgileMind** for:

* **Token Blacklist** → Secure logout by invalidating JWT refresh tokens
* **Session Caching** → Store temporary auth/session data for performance
* **Scalability** → Enables horizontal scaling without losing session data

### 1. Run Redis with Docker

```bash
docker run --name redis-server -p 6379:6379 -d redis
```

This starts a Redis container on port `6379`.

### 2. Verify Redis is Running

```bash
docker ps    # check container is up
docker logs redis-server
```

Or connect with CLI:

```bash
docker exec -it redis-server redis-cli ping
# Should return: PONG
```

### 3. Environment Variables

In your `.env`:

```env
# Redis
REDIS_URL=redis://localhost:6379
```

If running inside **Docker Compose**, use the service name instead:

```env
REDIS_URL=redis://redis:6379
```

### 4. Cloud Deployment (Production)

For production, it is recommended to use a **managed Redis service**:

* [Redis Cloud (Free Tier)](https://redis.com/try-free/)
* AWS ElastiCache for Redis
* Azure Cache for Redis
* Google Memorystore

Update `.env`:

```env
REDIS_URL=redis://:<password>@<redis-host>:6379
```

### 5. Integration in Backend

Redis is initialized in `src/config/redis.js` and injected into **Auth Service**:

* On **logout** → access/refresh tokens are stored in Redis blacklist
* On **login** → system checks if token is blacklisted before allowing access

---

⚡ With Redis enabled, **AgileMind** ensures secure logout, scalable token management, and faster auth verification.

---

👉 Do you want me to also **add a docker-compose.yml service block** for Redis (so it spins up together with MySQL + backend)?

## 📄 License

This project is licensed under the **MIT License** – see [LICENSE](LICENSE) for details.

---

## 🙌 Contributors

- **Jayawardhana L S** (IT22563200) – Planning & Task Automation
- **Weerapperuma B E** (IT22584236) – Daily Scrum Assistant
- **Kappagoda K M L P K** (IT22579140) – Retrospective Automation
- **Ishani S G C** (IT22617378) – Project Governance Dashboard

Supervised by:  
- Mr. Vishan Jayasinghearachchi  
- Ms. Poojani Gunathilake

---

> **AgileMind**: *From Zero to Hero in Agile Transformation* 🚀  
> *"Let the AI handle the admin — you focus on building great software."*