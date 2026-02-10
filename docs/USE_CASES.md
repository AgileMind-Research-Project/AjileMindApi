# AgileMind Use Cases

## 1. Platform & Tenant Management
*   **Tenant Registration**: Public user registers a company (Tenant). System extracts domain (e.g., `company.com`), creates a dedicated database, and provisions initial admin.
*   **Domain-Based Login**: System routes login requests to the correct tenant database based on the email domain provided.
*   **Platform Health Check**: Monitor status of all internal modules (AI, DB, Redis) via a unified health endpoint.

## 2. User Management (RBAC)
*   **Invite User**: Admin invites users. System assigns roles (Scrum Master, Developer) and sends temporary credentials.
*   **Role Management**: Super Admins define granular permissions (e.g., `["projects.read", "reports.create"]`) stored in the `roles` table.

## 3. Project & Sprint Management
*   **Create Project**: Setup new project with architecture details (Monolith/Microservices) and optionally sync from Jira.
*   **Sprint Planning**: Define sprint duration, goals, and assign backlog items.
*   **Delay Analysis Calculation**:
    *   **Trigger**: End of Sprint or On-Demand.
    *   **Logic**: Execute `DelayCalculationService`. Compare planned vs. actual story points.
    *   **Output**: Risk level (LOW/MEDIUM/HIGH) and forecasted project end date.

## 4. Intelligent Risk Management
*   **Calculate Project Risk**:
    *   **Logic**: Run weighted interactions of Bugs, Blockers, Workload, and Timeline Conflicts.
    *   **Output**: A normalized Risk Score (0-100%).
*   **AI Risk Recommendations (Agent)**:
    *   **Input**: High-risk project metadata.
    *   **Process**: AI Agent analyzes risk factors using Few-Shot prompting patterns.
    *   **Output**: 3-5 specific, actionable remediation steps (e.g., "Reduce Sprint Scope by 15%").

## 5. Knowledge Management (RAG)
*   **Document Ingestion**: Upload PDF/DOCX. System chunks content and generates vector embeddings.
*   **"Chat with Docs"**:
    *   **User**: Asks "What are the compliance requirements for feature X?"
    *   **System**: Retrieves top-k relevant chunks -> LLM synthesizes answer -> Returns citation.

## 6. Meeting Intelligence
*   **Transcript Processing**: Upload meeting recording/transcript.
*   **Chain-of-Thought Extraction**:
    *   AI analyzes text to identify tasks, status updates, and blockers.
    *   Generates reasoning trace ("User said 'I'm stuck on API', therefore Status=BLOCKED").
*   **Auto-Generate Reports**: Create "Minutes of Meeting" or "Retrospective Summary" from raw transcripts using predefined Templates.

## 7. Integrations
*   **Jira Two-Way Sync**:
    *   **Pull**: Fetch issues/sprints from Jira Cloud to local DB.
    *   **Push**: Update Jira ticket status when changed in AgileMind.

## 8. Communication
*   **Real-time Chat**: Team members communicate in project-specific channels (powered by Redis Pub/Sub).
*   **Smart Notifications**: Receive alerts for High Risk levels, assigned Tasks, or Mention in Chat.
