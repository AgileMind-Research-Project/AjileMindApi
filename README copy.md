# Jira Automation — Developer & AI Reference Guide

> **Project:** AgileMind Jira Integration Scripts  
> **Instance:** `https://agilemind193.atlassian.net`  
> **Project Key:** `SCRUM4`  
> **Language:** Python 3.x  
> **Last Updated:** 2026-05-03

---

## Table of Contents

1. [Overview](#overview)
2. [Credentials & Configuration](#credentials--configuration)
3. [Scripts Reference](#scripts-reference)
   - [createproject.py](#1-createprojectpy)
   - [create_severity_field.py](#2-create_severity_fieldpy)
   - [create_bug_with_severity.py](#3-create_bug_with_severitypy)
   - [add_severity_to_screen.py](#4-add_severity_to_screenpy)
4. [Execution Order](#execution-order)
5. [How to Change Things](#how-to-change-things)
6. [Custom Field Reference](#custom-field-reference)
7. [Severity System Explained](#severity-system-explained)
8. [Common Errors & Fixes](#common-errors--fixes)
9. [Jira API Endpoints Used](#jira-api-endpoints-used)
10. [For AI Agents](#for-ai-agents)

---

## Overview

These scripts automate the following Jira Cloud tasks via the REST API v3:

```
createproject.py              → Creates a Scrum project (SCRUM4)
     │
create_severity_field.py      → Creates a "Severity" custom field with 5 options
     │
create_bug_with_severity.py   → Creates a Bug ticket and sets Severity value
     │
add_severity_to_screen.py     → Makes Severity visible in the Jira ticket UI
```

> **No Jira UI interaction needed** — everything runs via Python scripts.

---

## Credentials & Configuration

All scripts share the same credentials block at the top of each file:

```python
JIRA_URL  = "https://agilemind193.atlassian.net"
EMAIL     = "agilemind193@gmail.com"
API_TOKEN = "ATATT3xFfGF0..."    # Jira API token
```

### How to get a new API token:
1. Go to → https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Copy the token and paste it as `API_TOKEN`

### Authentication method used:
All scripts use **HTTP Basic Auth**:
```
Authorization: Basic base64(email:api_token)
```

---

## Scripts Reference

---

### 1. `createproject.py`

**Purpose:** Creates a new Scrum software project in Jira Cloud.

**Run:**
```powershell
python createproject.py
```

**Key configuration (edit at top of file):**
```python
PROJECT_KEY  = "SCRUM4"                     # ← Change to a new unique key
PROJECT_NAME = "Agile Scrum Project 2026"   # ← Change project name
PROJECT_TYPE = "software"                   # software | business | service_desk
PROJECT_TEMPLATE = "com.pyxis.greenhopper.jira:gh-scrum-template"
```

**What it creates:**
- A Scrum project with board and sprints enabled
- Project lead is automatically set to the authenticated user

**Output example:**
```
Project created successfully: SCRUM4 - Agile Scrum Project 2026
```

**How to change project type:**
| Value | Description |
|---|---|
| `software` | Scrum/Kanban project (default) |
| `business` | Business team-managed project |
| `service_desk` | IT Service Management project |

---

### 2. `create_severity_field.py`

**Purpose:** Creates a `Severity` custom field (Select List) in Jira with 5 ordered options.

**Run:**
```powershell
python create_severity_field.py
```

**What it creates:**
| Option | Internal Weight |
|---|---|
| Blocker | 5 (highest) |
| Critical | 4 |
| Major | 3 |
| Minor | 2 |
| Trivial | 1 (lowest) |

**How it works (3 API calls):**
```
POST /rest/api/3/field                              → Creates the field
GET  /rest/api/3/field/{field_id}/context           → Gets context ID
POST /rest/api/3/field/{id}/context/{ctxId}/option  → Adds the 5 options
```

**Output — copy this into other scripts:**
```
SEVERITY_FIELD_ID = 'customfield_10041'

SEVERITY_VALUE_MAP = {
    'blocker':  'Blocker',   # weight 5
    'critical': 'Critical',  # weight 4
    'major':    'Major',     # weight 3
    'minor':    'Minor',     # weight 2
    'trivial':  'Trivial',   # weight 1
}
```

> ⚠️ **Run this only ONCE.** If you run it again, Jira creates a duplicate field.  
> Check existing fields at: `GET /rest/api/3/field`

**How to change the field name:**
```python
field_payload = {
    "name": "Bug Severity",    # ← change this
    ...
}
```

---

### 3. `create_bug_with_severity.py`

**Purpose:** Creates a Bug issue in the SCRUM4 project with the Severity field populated.

**Run:**
```powershell
python create_bug_with_severity.py
```

**Key configuration (edit these before running):**
```python
PROJECT_KEY     = "SCRUM4"                         # ← target project
BUG_SUMMARY     = "Login page crashes on invalid input"  # ← bug title
BUG_DESCRIPTION = "Steps to reproduce: ..."        # ← bug details
SEVERITY_VALUE  = "Critical"  # ← Blocker | Critical | Major | Minor | Trivial
```

**How it works:**
```
Step 1 → GET  /rest/api/3/field          — auto-finds Severity field ID
Step 2 →                                 — builds issue payload
Step 3 → POST /rest/api/3/issue          — creates the Bug ticket
```

**The issue payload sent to Jira:**
```json
{
  "fields": {
    "project":        { "key": "SCRUM4" },
    "summary":        "Login page crashes on invalid input",
    "issuetype":      { "name": "Bug" },
    "priority":       { "name": "High" },
    "description":    { "type": "doc", "version": 1, "content": [...] },
    "customfield_10041": { "value": "Critical" }
  }
}
```

**How to change severity:**
```python
SEVERITY_VALUE = "Blocker"   # highest priority bug
SEVERITY_VALUE = "Critical"  # (default)
SEVERITY_VALUE = "Major"
SEVERITY_VALUE = "Minor"
SEVERITY_VALUE = "Trivial"   # lowest priority
```

**How to change issue type:**
```python
"issuetype": {"name": "Bug"}    # Bug (default)
"issuetype": {"name": "Story"}  # Story
"issuetype": {"name": "Task"}   # Task
"issuetype": {"name": "Epic"}   # Epic
```

**Output example:**
```
✅ Bug ticket created successfully!
  Issue Key  : SCRUM4-1
  Issue ID   : 10046
  Severity   : Critical (weight=4)
  URL        : https://agilemind193.atlassian.net/browse/SCRUM4-1
```

---

### 4. `add_severity_to_screen.py`

**Purpose:** Makes the Severity field **visible** in the Jira ticket UI.

> **Why is this needed?**  
> In Jira, creating a custom field via API only stores data — it does NOT  
> automatically show the field on the ticket screen. You must add the field  
> to the project's **Screen** for it to appear in the UI.

**Run:**
```powershell
python add_severity_to_screen.py
```

**How it works:**
```
Step 1 → GET  /rest/api/3/screens                          — lists all screens
Step 2 → GET  /rest/api/3/screens/{id}/tabs                — finds tabs per screen
         GET  /rest/api/3/screens/{id}/tabs/{tabId}/fields — checks if field exists
         POST /rest/api/3/screens/{id}/tabs/{tabId}/fields — adds field to screen
Step 3 → GET  /rest/api/3/issue/SCRUM4-1                   — verifies value visible
```

**Screens it updated (from the last run):**
| Screen ID | Screen Name | Result |
|---|---|---|
| 10011 | SCRUM4: Scrum Default Issue Screen | ✅ Added |
| 10012 | SCRUM4: Scrum Bug Screen | ✅ Added |
| 10013 | FV: Scrum Default Issue Screen | ✅ Added |
| 10014 | FV: Scrum Bug Screen | ✅ Added |

**Manual alternative (Jira UI):**
1. ⚙️ Jira Settings → Issues → Screens
2. Find **"SCRUM4: Scrum Bug Screen"** → Click **Configure**
3. In the "Add Field" dropdown → search **"Severity"** → click **Add**

---

## Execution Order

Run scripts in this exact order for a fresh setup:

```
1.  python createproject.py              # Create SCRUM4 project
        ↓
2.  python create_severity_field.py      # Create Severity custom field
        ↓  (note the SEVERITY_FIELD_ID printed)
3.  python create_bug_with_severity.py   # Create Bug with Severity value
        ↓
4.  python add_severity_to_screen.py     # Make field visible in Jira UI
```

---

## How to Change Things

### Change the project
Edit `PROJECT_KEY` in any script:
```python
PROJECT_KEY = "MYPROJECT"   # ← your project key
```

### Change the severity level on a bug
```python
SEVERITY_VALUE = "Blocker"   # in create_bug_with_severity.py
```

### Create a different issue type (Story/Task/Epic)
```python
"issuetype": {"name": "Story"}   # change "Bug" to any type
```

### Use a different Jira instance
```python
JIRA_URL  = "https://yourcompany.atlassian.net"
EMAIL     = "you@yourcompany.com"
API_TOKEN = "your_new_token"
```

### Add more custom field options
In `create_severity_field.py`, edit `SEVERITY_OPTIONS`:
```python
SEVERITY_OPTIONS = ["Blocker", "Critical", "Major", "Minor", "Trivial", "Enhancement"]
```

---

## Custom Field Reference

| Field | Field ID | Type | Values |
|---|---|---|---|
| Severity | `customfield_10041` | Select List | Blocker, Critical, Major, Minor, Trivial |
| Story Points | `customfield_10035` | Number | Any integer |
| Story Point Estimate | `customfield_10016` | Number | Any integer |
| Start Date | `customfield_10015` | Date | `YYYY-MM-DD` |

**How to use any custom field in issue creation:**
```python
# Select List field (like Severity):
"customfield_10041": {"value": "Critical"}

# Number field (like Story Points):
"customfield_10035": 5

# Date field:
"customfield_10015": "2026-05-10"
```

---

## Severity System Explained

The severity system maps **Jira option values** to **numeric weights** used by the ML prioritization engine (`Backlog_prioritize.py`):

```
Jira UI Value   API Payload                    Backlog Weight
─────────────   ───────────────────────────    ──────────────
Blocker      →  {"value": "Blocker"}       →   5  (highest)
Critical     →  {"value": "Critical"}      →   4
Major        →  {"value": "Major"}         →   3
Minor        →  {"value": "Minor"}         →   2
Trivial      →  {"value": "Trivial"}       →   1  (lowest)
```

**Used in `Backlog_prioritize.py` at line 100:**
```python
'severity': train_df['severity'].map({
    'blocker': 5, 'critical': 4, 'major': 3, 'minor': 2, 'trivial': 1
}).fillna(3).values
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `400 Bad Request` on project create | Invalid `projectTemplateKey` | Use `com.pyxis.greenhopper.jira:gh-scrum-template` exactly |
| `Severity field not found` | `create_severity_field.py` not run yet | Run `create_severity_field.py` first |
| Field set via API but not visible in UI | Field not added to screen | Run `add_severity_to_screen.py` |
| `Could not get tabs for screen` | Jira permission restriction on older screens | Safe to ignore — only SCRUM4 screens matter |
| `401 Unauthorized` | Wrong API token | Regenerate token at `id.atlassian.com` |
| Duplicate custom field created | `create_severity_field.py` run twice | Delete duplicate via Jira UI: Settings → Issues → Custom Fields |

---

## Jira API Endpoints Used

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/rest/api/3/project` | Create project |
| `POST` | `/rest/api/3/issuetype` | Create issue type |
| `POST` | `/rest/api/3/field` | Create custom field |
| `GET` | `/rest/api/3/field` | List all fields |
| `GET` | `/rest/api/3/field/{id}/context` | Get field context |
| `POST` | `/rest/api/3/field/{id}/context/{ctxId}/option` | Add field options |
| `POST` | `/rest/api/3/issue` | Create issue (bug/story/task) |
| `PUT` | `/rest/api/3/issue/{key}` | Update issue |
| `GET` | `/rest/api/3/screens` | List all screens |
| `GET` | `/rest/api/3/screens/{id}/tabs` | Get screen tabs |
| `POST` | `/rest/api/3/screens/{id}/tabs/{tabId}/fields` | Add field to screen |
| `GET` | `/rest/api/3/myself` | Get authenticated user info |

**Base URL for all calls:** `https://agilemind193.atlassian.net`  
**API version:** REST API v3  
**Auth:** Basic Auth — `base64(email:api_token)`

---

## For AI Agents

If you are an AI reading this document to understand or extend the codebase:

### Confirmed working constants:
```python
JIRA_URL          = "https://agilemind193.atlassian.net"
EMAIL             = "agilemind193@gmail.com"
PROJECT_KEY       = "SCRUM4"
SEVERITY_FIELD_ID = "customfield_10041"   # confirmed, created & verified
```

### Severity value injection pattern (always use this):
```python
issue_fields["customfield_10041"] = {"value": "Critical"}
# Options: "Blocker" | "Critical" | "Major" | "Minor" | "Trivial"
```

### Screen IDs for SCRUM4 (already configured):
```python
SCRUM4_SCREENS = {
    10011: "SCRUM4: Scrum Default Issue Screen",  # Severity ✅ added
    10012: "SCRUM4: Scrum Bug Screen",             # Severity ✅ added
}
```

### File responsibilities:
```
createproject.py           → project provisioning
create_severity_field.py   → one-time field + options setup
create_bug_with_severity.py → issue creation with custom fields
add_severity_to_screen.py   → screen/UI configuration
README.md                  → this file (documentation)
```

### Do NOT re-run:
- `create_severity_field.py` → will create a duplicate field
- `createproject.py` with same `PROJECT_KEY` → will fail (key already taken)
