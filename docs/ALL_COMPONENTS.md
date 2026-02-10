# AgileMind System Components Reference

This document provides a comprehensive, readable list of all modules within the AgileMind Modular Monolith. Each module is broken down into its **API Controller** (Entry Point), **Business Service** (Logic), and **Data Access** (Repository/DB) layers.

---

## 1. Authentication & User Management
Handles user registration, login, role assignment, and security.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Auth Controller | `app/api/v1/auth.py` | Login, Register, Refresh Token, Password Reset flows. |
| **Controller** | User Controller | `app/api/v1/users.py` | User CRUD, Profile management, Invitations. |
| **Controller** | Role Controller | `app/api/v1/roles.py` | RBAC Role creation and assignment. |
| **Controller** | OTP Controller | `app/api/v1/otp.py` | One-Time Password generation and verification. |
| **Service** | Auth Service | `app/services/auth_service.py` | JWT generation, Password hashing, Login logic. |
| **Service** | OTP Service | `app/services/otp_service.py` | Email sending logic for OTPs. |
| **Repo** | Tenant User Repo | `app/db/repositories/tenant_user_repository.py` | DB access for `users` and `roles` tables. |
| **Repo** | Password Repo | `app/db/repositories/password_reset_repository.py` | DB access for password reset tokens. |

---

## 2. Project & Backlog Management
Core domain logic for managing agile projects, sprints, and tasks.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Project Controller | `app/api/v1/projects.py` | Create/List Projects, Sprint Management. |
| **Controller** | Backlog Controller | `app/api/v1/backlog.py` | Import Backlog (CSV/Excel), CRUD Items. |
| **Controller** | Priority Controller | `app/api/v1/backlog_priority.py` | Drag-and-drop prioritization logic. |
| **Service** | Project Service | `app/services/project_service.py` | Project creation logic, Jira Sync triggers. |
| **Service** | Delay Service | `app/services/delay_calculation_service.py` | **Algorithm**: Calculates Sprint delays vs plans. |
| **Service** | Backlog Service | `app/services/backlog_service.py` | Item processing, filtering. |
| **Repo** | Project Repo | `app/db/repositories/project_repository.py` | DB access for `projects` and `sprints`. |
| **Repo** | Backlog Repo | `app/db/repositories/backlog_repository.py` | DB access for `backlog_items`. |

---

## 3. Documents & RAG (Knowledge Base)
AI-powered document storage, search, and retrieval.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Document Controller | `app/api/v1/documents.py` | File Upload, "Chat with Docs" endpoint. |
| **Service** | Document Service | `app/services/document_service.py` | File parsing (PDF/DOCX), metadata storage. |
| **Service** | RAG Service | `app/services/rag_service.py` | **AI Agent**: Embeddings, Vector Search, LLM Context. |
| **Data** | Vector Store | `pgvector` / `Chroma` | Stores document embeddings (Implied). |

---

## 4. Risk & Intelligence
Advanced algorithms and AI agents for project health monitoring.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Risk Controller | `app/api/v1/riskparameters.py` | Configure params, View Risk Scores. |
| **Service** | Risk Service | `app/services/risk_calculation_service.py` | **Algorithm**: Weighted scoring (Bugs, Blockers, Time). |
| **Service** | Recommendation Svc | `app/services/recommendation_service.py` | **AI Agent**: Few-shot prompting for risk mitigation advice. |

---

## 5. Reports & Analytics
Generates meeting minutes and project status reports.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Report Controller | `app/api/v1/reports.py` | trigger report generation, Download PDF. |
| **Controller** | Release Note Ctrl | `app/api/v1/release_notes.py` | AI-generated release notes. |
| **Controller** | Transcript Ctrl | `app/api/v1/transcripts.py` | Upload Meeting Transcripts. |
| **Service** | Report Service | `app/services/report_service.py` | Orchestrates report assembly. |
| **Service** | LLM Report Svc | `app/services/llm_report_service.py` | **AI**: Summarizes text, extracts action items. |
| **Service** | Release Note Svc | `app/services/release_note_service.py` | Drafts notes from Jira/Task data. |

---

## 6. Communication
Real-time messaging and system notifications.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Chat Controller | `app/api/v1/redis_chat.py` | Chat history, Room management. |
| **Controller** | Notification Ctrl | `app/api/v1/notifications.py` | System alerts, Downtime warnings. |
| **Service** | Chat Service | `app/services/redis_chat_service.py` | Interface with Redis Pub/Sub. |
| **Service** | Notification Svc | `app/services/notification_service.py` | Dispatch logic. |
| **Data** | Redis | `Redis` | Message Broker & Cache. |

---

## 7. Integrations & System
External connectivity and platform maintenance.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Controller** | Jira Controller | `app/api/v1/jira.py` | Connect/Sync with Jira Cloud. |
| **Controller** | Audit Controller | `app/api/v1/audit.py` | View System Logs. |
| **Service** | Jira Service | `app/services/jira_service.py` | Jira REST API Client. |
| **Repo** | Audit Repo | `app/db/repositories/audit_repository.py` | DB access for `audit_logs`. |

---

## 8. AI Core and Utilities
Shared utilities for LLM interactions.

| Layer | Component Name | File Path | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Service** | LLM Service | `app/services/llm_service.py` | Generic client for OpenAI/Ollama. |
| **Utils** | LLM Utils | `app/services/llm_utils.py` | Prompt templates, Token counting. |
