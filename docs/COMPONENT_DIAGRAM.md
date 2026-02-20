# AgileMind Component Diagram

This diagram visualizes the internal structure of the **Backend Monolith**, mapping the flow from complete list of API Controllers -> Business Services -> Data Access Layer.

```mermaid
C4Component
    title AgileMind Backend Component Diagram (Full Modular Monolith)

    Container_Boundary(api, "API Layer (FastAPI Controllers)") {
        Component(authCtrl, "Auth", "auth.py", "Login/Reg")
        Component(userCtrl, "Users", "users.py", "User Mgmt")
        Component(roleCtrl, "Roles", "roles.py", "RBAC")
        Component(otpCtrl, "OTP", "otp.py", "One-Time PW")
        Component(projCtrl, "Projects", "projects.py", "Project CRUD")
        Component(backCtrl, "Backlog", "backlog.py", "Items/Import")
        Component(prioCtrl, "Backlog Prio", "backlog_priority.py", "Ranking")
        Component(docCtrl, "Documents", "documents.py", "Files/RAG")
        Component(transCtrl, "Transcripts", "transcripts.py", "Meetings")
        Component(chatCtrl, "Chat", "redis_chat.py", "Real-time")
        Component(riskCtrl, "Risk", "riskparameters.py", "Risk Calc")
        Component(repCtrl, "Reports", "reports.py", "GenAI Reports")
        Component(relCtrl, "Release Notes", "release_notes.py", "AI Release Notes")
        Component(notifCtrl, "Notifications", "notifications.py", "Alerts")
        Component(auditCtrl, "Audit", "audit.py", "Logs")
        Component(jiraCtrl, "Jira", "jira.py", "Integration")
        Component(tempCtrl, "Templates", "templates.py", "Report Tmpl")
        Component(platCtrl, "Platform", "platform.py", "Public API")
    }

    Container_Boundary(services, "Service Layer (Business Logic)") {
        Component(authSvc, "Auth Svc", "auth_service.py", "Auth Logic")
        Component(otpSvc, "OTP Svc", "otp_service.py", "Email OTP")
        Component(projSvc, "Project Svc", "project_service.py", "Core Logic")
        Component(delaySvc, "Delay Svc", "delay_calculation_service.py", "Sprint Algo")
        Component(backSvc, "Backlog Svc", "backlog_service.py", "Item Logic")
        Component(jiraBackSvc, "Jira Backlog Svc", "jira_backlog_service.py", "Sync Logic")
        Component(docSvc, "Document Svc", "document_service.py", "File Ops")
        Component(ragSvc, "RAG Svc", "rag_service.py", "Embeddings/Search")
        Component(transSvc, "Transcript Svc", "transcript_service.py", "Parsing")
        Component(riskSvc, "Risk Svc", "risk_calculation_service.py", "Weighted Logic")
        Component(recSvc, "Rec Svc", "recommendation_service.py", "AI Agent")
        Component(repSvc, "Report Svc", "report_service.py", "Report Gen")
        Component(llmRepSvc, "LLM Report Svc", "llm_report_service.py", "AI Summaries")
        Component(relSvc, "Release Note Svc", "release_note_service.py", "Drafting")
        Component(chatSvc, "Chat Svc", "redis_chat_service.py", "Redis Backend")
        Component(notifSvc, "Notif Svc", "notification_service.py", "Dispatch")
        Component(jiraSvc, "Jira Svc", "jira_service.py", "API Client")
        Component(tempSvc, "Template Svc", "template_service.py", "CRUD")
        Component(emailSvc, "Email Svc", "email_service.py", "SMTP")
        Component(llmSvc, "LLM Svc", "llm_service.py", "Model Client")
    }

    Container_Boundary(data, "Data Access Layer") {
        Component(tenantRepo, "Tenant Repo", "tenant_user_repository.py", "Users")
        Component(projRepo, "Project Repo", "project_repository.py", "Projects")
        Component(backRepo, "Backlog Repo", "backlog_repository.py", "Items")
        Component(auditRepo, "Audit Repo", "audit_repository.py", "Logs")
        Component(passRepo, "Password Repo", "password_reset_repository.py", "Tokens")
        ComponentDb(db, "Direct DB", "SQLAlchemy", "Generic Access")
    }

    System_Boundary(ext, "External") {
        System_Ext(llm, "LLM", "OpenAI/Ollama")
        System_Ext(jira, "Jira", "Cloud")
        System_Ext(mail, "SMTP", "Email")
    }

    ContainerDb(redis, "Redis", "Pub/Sub")

    %% Relations
    Rel(authCtrl, authSvc, "Calls")
    Rel(userCtrl, authSvc, "Calls")
    Rel(otpCtrl, otpSvc, "Calls")
    Rel(projCtrl, projSvc, "Calls")
    Rel(projCtrl, delaySvc, "Calls")
    Rel(backCtrl, backSvc, "Calls")
    Rel(docCtrl, docSvc, "Calls")
    Rel(docCtrl, ragSvc, "Search")
    Rel(transCtrl, transSvc, "Calls")
    Rel(riskCtrl, riskSvc, "Calc")
    Rel(riskCtrl, recSvc, "Advice")
    Rel(repCtrl, repSvc, "Calls")
    Rel(chatCtrl, chatSvc, "Msg")
    Rel(notifCtrl, notifSvc, "Alert")
    Rel(jiraCtrl, jiraSvc, "Sync")
    
    Rel(authSvc, tenantRepo, "DB")
    Rel(otpSvc, mail, "Send")
    Rel(projSvc, projRepo, "DB")
    Rel(backSvc, backRepo, "DB")
    Rel(auditCtrl, auditRepo, "DB")
    
    Rel(ragSvc, llmSvc, "Embed")
    Rel(recSvc, llmSvc, "Reasoning")
    Rel(llmRepSvc, llmSvc, "Summary")
    Rel(llmSvc, llm, "API")
    
    Rel(chatSvc, redis, "Pub/Sub")
```
