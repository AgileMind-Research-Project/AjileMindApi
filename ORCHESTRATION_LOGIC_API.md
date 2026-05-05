# 🧠 AgileMind Orchestration Modules: Logic API Reference

This document summarizes the internal logic and core functions of the AI-powered orchestration modules (Predictive Planning, Task Assignment, Task Decomposition, and Sprint Management).

---

## 🏗️ 1. Task Assignment Logic (`Assign_Tasks`)
**Module**: `assign_tasks_to_developers`
**Primary Endpoint**: `lambda_handler`

### Core Functions:
*   **`assign_tasks_to_developers(project_id, tenant_table, tenant_db)`**
    *   **Logic**: Intelligent workload balancing using multi-factor scoring.
    *   **Scoring**: `Score = (TechMatch * 10) + (StackMatch * 5) + Experience + (WorkHistory * 3) - (Workload * 0.5)`
*   **`fetch_developers_from_db(tenant, project)`**
    *   **Data**: Retrieves stacks, technologies, and experience levels.
*   **`get_unassigned_parent_tasks(project_id, tenant)`**
    *   **Data**: Identifies unassigned backlog items for processing.

---

## 📊 2. AI Prioritization Logic (`Backlog_Prioritize`)
**Module**: `Backlog_prioritize`
**Primary Endpoint**: `train_and_prioritize`

### Core Functions:
*   **`train_and_prioritize(historical_csv, backlog_items)`**
    *   **Engine**: SentenceTransformer (`all-MiniLM-L6-v2`) + Linear Regression + KMeans.
*   **`calculate_wsjf(...)`**
    *   **Formula**: `(Business Value + Urgency + Risk Reduction) / Story Points`.
*   **`kmeans_moscow_clustering(...)`**
    *   **Result**: Automatic categorization into MoSCoW buckets (Must/Should/Could/Won't).

---

## ✂️ 3. Task Decomposition Logic (`Task_Split`)
**Module**: `split_task`
**Primary Endpoint**: `split_backlog_tasks`

### Core Functions:
*   **`extract_subtasks_advanced(summary, description, ...)`**
    *   **Engine**: `spaCy` NLP for semantic graph analysis.
    *   **Action**: Detects verbs and technical nouns to form sub-task summaries.
*   **`detect_task_tags(text, tag_indicators)`**
    *   **Logic**: Auto-labels tasks with categories (Backend, Frontend, DevOps, UI).
*   **`get_dynamic_keywords(project_id, tenant)`**
    *   **Logic**: Extracts nouns and verbs from existing project context for better accuracy.

---

## 🔄 4. Jira Integration Logic (`Get_Backlog`)
**Module**: `get_backlogData`
**Primary Endpoint**: `sync_backlog`

### Core Functions:
*   **`sync_jira_backlog(tenant)`**
    *   **Action**: Orchestrates the sync between Atlassian Cloud and local DB.
*   **`fetch_jira_backlog(jira_url, email, api_token, project_key)`**
    *   **Engine**: `atlassian-python-api`.
*   **`transform_jira_issue(issue, project_id)`**
    *   **Logic**: Maps Jira fields to local schema (Priority, Severity, Story Points).

---

## 🎬 5. Sprint Review Management (`Sprint_Review`)
**Module**: `sprint_review`
**Primary Endpoint**: `lambda_handler`

### Core Functions:
*   **`generate_sprint_review_slides(...)`**
    *   **Logic**: Calculates Velocity, KPI stats, and Bug severity distributions.
*   **`process_project(project, tenant, redis_client)`**
    *   **Action**: Generates formatted slide summaries and posts them to Redis project channels.
*   **`get_active_sprint(project_id, tenant)`**
    *   **Data**: Retrieves the current timeframe for review generation.

---

> [!TIP]
> These modules are designed to run as serverless orchestration layers, integrating with the main `AjileMindApi` to provide deep cognitive automation for project workflows.
