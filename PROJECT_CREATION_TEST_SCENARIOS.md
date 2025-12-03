"""
Project Creation Workflow - Test Scenarios

This document outlines the test scenarios for the project creation feature
with manual key entry and database storage only after Jira success.
"""

# ============================================
# TEST SCENARIO 1: Successful Project Creation
# ============================================

"""
Steps:
1. User enters project details manually (including key)
2. Frontend sends POST request to /api/v1/projects/
3. Backend validates input
4. Backend checks database for duplicates (pre-validation)
5. Backend creates project in Jira Cloud
6. ✅ Jira returns success with project ID
7. Backend saves to database with Jira project ID
8. Backend returns success response

Expected Result:
- Project created in Jira ✅
- Project saved in database ✅
- User receives success message ✅
"""

test_request_success = {
    "project_name": "Test Project 2025",
    "key": "TEST2025",  # Manually entered
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "description": "Test project",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
}

expected_response_success = {
    "success": True,
    "message": "Project created successfully in Jira and database",
    "data": {
        "id": 10039,  # From Jira
        "project_name": "Test Project 2025",
        "key": "TEST2025",
        "project_type": "software",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "jira_url": "https://agilmind.atlassian.net/projects/TEST2025",
        "created_at": "2025-12-01T10:30:00"
    }
}

# ============================================
# TEST SCENARIO 2: Jira Creation Fails
# ============================================

"""
Steps:
1. User enters project details manually
2. Frontend sends POST request
3. Backend validates input
4. Backend checks database (passes)
5. Backend attempts to create in Jira
6. ❌ Jira returns error (duplicate key)
7. Backend does NOT save to database
8. Backend returns error to user

Expected Result:
- Project NOT created in Jira ❌
- Project NOT saved in database ❌
- User receives error message ✅
- Database remains unchanged ✅
"""

test_request_duplicate_key = {
    "project_name": "Another Project",
    "key": "SCRUM4",  # Already exists in Jira
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
}

expected_response_duplicate_key = {
    "detail": "Project key already exists: Project 'Agile Scrum Project 2024' uses this project key."
}

# ============================================
# TEST SCENARIO 3: Database Pre-validation Catches Duplicate
# ============================================

"""
Steps:
1. User enters project details with existing key
2. Frontend sends POST request
3. Backend validates input
4. Backend checks database
5. ❌ Database check finds duplicate
6. Backend returns error BEFORE calling Jira
7. No Jira API call made

Expected Result:
- No Jira API call made ✅
- Project NOT saved in database ❌
- User receives error message ✅
- Fast failure (no unnecessary Jira call) ✅
"""

test_request_db_duplicate = {
    "project_name": "New Project",
    "key": "TEST2025",  # Already in database
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
}

expected_response_db_duplicate = {
    "detail": "Project with key 'TEST2025' already exists in database"
}

# ============================================
# TEST SCENARIO 4: Invalid Key Format
# ============================================

"""
Steps:
1. User enters invalid project key (lowercase)
2. Frontend validation catches it
3. OR Backend validation catches it
4. Error returned immediately

Expected Result:
- Validation error ✅
- No Jira call ✅
- No database operation ✅
"""

test_request_invalid_key = {
    "project_name": "Test Project",
    "key": "test123",  # Invalid: lowercase
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
}

expected_response_invalid_key = {
    "detail": [
        {
            "loc": ["body", "key"],
            "msg": "string does not match regex \"^[A-Z][A-Z0-9]*$\"",
            "type": "value_error.str.regex"
        }
    ]
}

# ============================================
# TEST SCENARIO 5: Jira Succeeds but Database Fails
# ============================================

"""
Steps:
1. User enters project details
2. Frontend sends POST request
3. Backend validates input
4. Backend checks database (passes)
5. Backend creates in Jira
6. ✅ Jira returns success with ID
7. Backend attempts to save to database
8. ❌ Database operation fails (connection error, constraint violation, etc.)
9. Backend returns error with Jira project ID

Expected Result:
- Project created in Jira ✅
- Project NOT in database ❌
- User receives error with Jira ID ✅
- Manual cleanup may be needed ⚠️

Note: This is a partial failure scenario that needs attention.
In production, consider implementing compensation logic or transaction rollback.
"""

expected_response_db_failure = {
    "detail": "Project created in Jira (ID: 10040) but failed to save to database: Connection error"
}

# ============================================
# WORKFLOW CONFIRMATION
# ============================================

"""
CONFIRMED WORKFLOW:

1. Frontend Form
   ✅ User manually enters ALL fields including project key
   ✅ Client-side validation (key format, date range)
   ✅ Key automatically converted to uppercase

2. Backend Processing
   ✅ Validate request data (Pydantic)
   ✅ Check authorization (role-based)
   ✅ Pre-validate database (quick duplicate check)
   ✅ Create in Jira FIRST
   ✅ ONLY if Jira succeeds, save to database
   ✅ Return combined result

3. Database Storage
   ✅ ONLY happens after successful Jira creation
   ✅ Uses project ID returned from Jira
   ✅ Stores all metadata with timestamps

4. Error Handling
   ✅ Validation errors → No Jira call, no DB write
   ✅ Duplicate in DB → No Jira call, fast failure
   ✅ Jira failure → No DB write, return Jira error
   ✅ DB failure → Jira already created, return error with ID
"""

# ============================================
# MANUAL TESTING CHECKLIST
# ============================================

"""
□ Test with valid data → Should succeed
□ Test with duplicate key in Jira → Should fail before DB write
□ Test with duplicate key in DB → Should fail immediately
□ Test with duplicate name in Jira → Should fail before DB write
□ Test with duplicate name in DB → Should fail immediately
□ Test with invalid key format → Should fail validation
□ Test with end_date before start_date → Should fail validation
□ Test with unauthorized user → Should fail authorization
□ Test with missing Jira integration → Should fail with 404
□ Test manual key entry → Should accept user input
□ Verify DB entry only after Jira success → Check database
□ Verify Jira URL in response → Should be valid
□ Verify project ID matches Jira → Should be same
"""

# ============================================
# CURL EXAMPLES FOR TESTING
# ============================================

"""
# 1. Create project with manual key
curl -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Manual Key Test",
    "key": "MKT2025",
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
  }'

# 2. Verify in database
SELECT * FROM projects WHERE `key` = 'MKT2025';

# 3. Check Jira
# Visit: https://agilmind.atlassian.net/projects/MKT2025

# 4. Test duplicate key (should fail)
curl -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Different Name",
    "key": "MKT2025",
    "project_type": "software",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "template": "com.pyxis.greenhopper.jira:gh-scrum-template"
  }'

Expected: Error about duplicate key, NO database entry created
"""
