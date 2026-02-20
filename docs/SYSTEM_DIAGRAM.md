# AgileMind System Architecture

This document provides a high-level overview of the AgileMind system architecture using a C4 Container diagram.

## System Diagram

```mermaid
C4Context
    title AgileMind System Architecture (Modular Monolith)
    
    Person(user, "User", "Platform User (Admin, PM, Team Member)")
    
    System_Boundary(agileMind, "AgileMind Platform") {
        
        Container(frontend, "Frontend", "Next.js / React", "Web Interface for users")
        
        Container(backend, "Backend Monolith", "FastAPI (Python)", "Single Deployment Unit containing all business logic modules")

        System_Boundary(modules, "Internal Modules (In-Process)") {
            Component(authMod, "Auth Module", "Python", "User Mgmt, JWT, Roles")
            Component(projectMod, "Project Module", "Python", "Projects, Sprints, Delay Algo")
            Component(backlogMod, "Backlog Module", "Python", "Backlog Items, Priorities")
            Component(docMod, "RAG Module", "Python / LangChain", "Document Parsing, Embeddings")
            Component(chatMod, "Chat Module", "Python / Redis", "Real-time Messaging")
            Component(reportMod, "Report Module", "Python / LLM", "AI Reports, Templates")
            Component(riskMod, "Risk Module", "Python", "Weighted Risk Algorithms")
            Component(jiraMod, "Jira Module", "Python", "Jira Integration Logic")
            Component(notifMod, "Notification Module", "Python", "Alerts & Updates")
        }

        ContainerDb(db, "Primary Database", "MySQL", "Multi-Tenant Data (Tenant Tables)")
        ContainerDb(redis, "Cache & PubSub", "Redis", "Session, Real-time Chat, Celery Broker")
        ContainerDb(vectorDb, "Vector Store", "pgvector / Chroma", "Document Embeddings for RAG")
    }

    System_Boundary(external, "External Services") {
        System_Ext(jira, "Jira Cloud", "Project & Issue Source")
        System_Ext(llm, "LLM Service", "OpenAI / Ollama", "GenAI Agents & Embeddings")
        System_Ext(email, "Email Service", "SMTP / SendGrid", "OTP & Notifications")
    }

    Rel(user, frontend, "Uses", "HTTPS")
    Rel(frontend, backend, "API Calls", "JSON/HTTPS")
    
    Rel(backend, authMod, "Calls")
    Rel(backend, projectMod, "Calls")
    Rel(backend, backlogMod, "Calls")
    Rel(backend, docMod, "Calls")
    Rel(backend, chatMod, "Calls")
    Rel(backend, riskMod, "Calls")
    
    Rel(authMod, db, "Reads/Writes")
    Rel(projectMod, db, "Reads/Writes")
    Rel(riskMod, db, "Reads/Writes")
    Rel(docMod, vectorDb, "Reads/Writes Embeddings")
    
    Rel(chatMod, redis, "Pub/Sub")
    
    Rel(jiraMod, jira, "Syncs with", "REST API")
    Rel(docMod, llm, "Embeddings/Answers", "API")
    Rel(reportMod, llm, "Generate Reports", "API")
    Rel(authMod, email, "Sends OTP", "SMTP")
    
    UpdateRelStyle(user, frontend, $offsetX="-40", $offsetY="-20")
    UpdateRelStyle(frontend, backend, $offsetX="-30", $offsetY="20")
    
```

## Data Flow Description

1.  **Authentication**: Users log in via the Frontend. The **Backend Monolith** receives the request, and the internal `Auth Module` validates credentials against the `Primary Database` and issues JWT tokens.
2.  **Project Management**: Project Managers interact with the internal `Project Module` to manage projects and sprints. Data is stored in the `Primary Database`.
3.  **Jira Integration**: The `Jira Module` connects to external Jira Cloud instances to sync projects and issues, enabling a unified view within the platform.
4.  **RAG & Documents**: Users upload documents which are processed by the `Document Module`. Text is extracted and sent to the external `LLM Service` to generate embeddings. The `Global Chat` and `Chat with Document` features retrieve these contexts to answer user queries.
5.  **Real-time Chat**: Messaging utilizes the `Chat Module` backed by `Redis` for real-time pub/sub capabilities.
6.  **Reporting**: The `Report Module` uses the external `LLM Service` to generate intelligent summaries and reports (MOM, Retrospectives) based on meeting transcripts and templates.
