"""
Recurring Bug Detector Service

Detects recurring bugs by analyzing multiple report sources:
1. Retrospective - what_didnt_go_well, action_points
2. Daily Standup - blockers
3. Sprint Meeting - issues_and_risks
"""

import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from app.db.database import Database
from app.core.logger import logger


class RecurringBugDetector:
    """
    Detects recurring bugs by analyzing multiple report sources.
    Uses hash-based deduplication to track the same bug across meetings.
    Auto-escalates severity based on mention count.
    """
    
    # Keywords that indicate a bug/issue
    BUG_KEYWORDS = [
        'bug', 'issue', 'error', 'crash', 'failed', 'broken', 
        'not working', "doesn't work", "didn't work", 'problem', 'defect',
        'regression', 'fix', 'patch', 'hotfix', 'failing', 'exception',
        'timeout', 'slow', 'performance', 'memory leak', 'stuck'
    ]
    
    # Keywords for recurring issues
    RECURRING_KEYWORDS = [
        'again', 'still', 'keeps', 'repeatedly', 'same issue', 'recurring',
        'happening again', 'back again', 'not fixed', 'still broken',
        'continues to', 'persistent'
    ]
    
    def __init__(self, db: Database, tenant_schema: str):
        self.db = db
        self.tenant_schema = tenant_schema
    
    def _generate_bug_hash(self, description: str) -> str:
        """Generate a hash for deduplication based on normalized description"""
        # Normalize: lowercase, remove extra spaces
        normalized = ' '.join(description.lower().split())
        # Take first 200 chars for hashing to catch similar bugs
        normalized = normalized[:200]
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _extract_bug_category(self, description: str) -> str:
        """Categorize bug based on keywords"""
        desc_lower = description.lower()
        
        if any(kw in desc_lower for kw in ['api', 'endpoint', 'request', 'response', '500', '404', 'http', 'rest']):
            return 'api'
        elif any(kw in desc_lower for kw in ['ui', 'button', 'display', 'css', 'layout', 'frontend', 'component', 'render']):
            return 'ui'
        elif any(kw in desc_lower for kw in ['database', 'query', 'sql', 'db', 'connection', 'mysql', 'postgres']):
            return 'database'
        elif any(kw in desc_lower for kw in ['slow', 'performance', 'timeout', 'memory', 'cpu', 'lag', 'latency']):
            return 'performance'
        elif any(kw in desc_lower for kw in ['integration', 'jira', 'webhook', 'sync', 'third-party', 'external']):
            return 'integration'
        elif any(kw in desc_lower for kw in ['security', 'auth', 'permission', 'access', 'token', 'password']):
            return 'security'
        else:
            return 'other'
    
    def _is_bug_related(self, text: str) -> bool:
        """Check if text is bug/issue related"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.BUG_KEYWORDS)
    
    def _is_recurring_indicator(self, text: str) -> bool:
        """Check if text indicates a recurring issue"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.RECURRING_KEYWORDS)
    
    def _determine_severity(self, description: str, is_recurring: bool = False) -> str:
        """Determine severity based on keywords"""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ['critical', 'severe', 'major', 'crash', 'down', 'production', 'blocker']):
            return 'critical' if is_recurring else 'high'
        elif any(word in desc_lower for word in ['urgent', 'important', 'breaking', 'blocking']):
            return 'high'
        elif any(word in desc_lower for word in ['minor', 'small', 'trivial', 'cosmetic']):
            return 'low'
        else:
            return 'high' if is_recurring else 'medium'
    
    async def extract_bugs_from_retrospective(
        self, 
        report_content: Dict[str, Any],
        report_id: int,
        transcript_id: int,
        project_id: int,
        meeting_date: date
    ) -> List[Dict[str, Any]]:
        """Extract potential bugs from retrospective report"""
        bugs = []
        
        # Extract from what_didnt_go_well
        what_didnt_go_well = report_content.get('what_didnt_go_well', [])
        if isinstance(what_didnt_go_well, list):
            for item in what_didnt_go_well:
                if isinstance(item, str) and self._is_bug_related(item):
                    is_recurring = self._is_recurring_indicator(item)
                    bugs.append({
                        'description': item,
                        'source_type': 'retrospective_issues',
                        'severity': self._determine_severity(item, is_recurring),
                        'is_recurring_indicator': is_recurring
                    })
        
        # Extract from action_points (bugs that need fixing)
        action_points = report_content.get('action_points', [])
        if isinstance(action_points, list):
            for point in action_points:
                action_text = ''
                if isinstance(point, dict):
                    action_text = point.get('task', point.get('action', ''))
                elif isinstance(point, str):
                    action_text = point
                
                if action_text and self._is_bug_related(action_text):
                    is_recurring = self._is_recurring_indicator(action_text)
                    bugs.append({
                        'description': action_text,
                        'source_type': 'retrospective_actions',
                        'severity': self._determine_severity(action_text, is_recurring),
                        'is_recurring_indicator': is_recurring
                    })
        
        # Process and store each bug
        for bug in bugs:
            await self._upsert_recurring_bug(
                description=bug['description'],
                severity=bug['severity'],
                source_type=bug['source_type'],
                report_id=report_id,
                transcript_id=transcript_id,
                project_id=project_id,
                meeting_date=meeting_date
            )
        
        logger.info(f"Extracted {len(bugs)} potential bugs from retrospective report {report_id}")
        return bugs
    
    async def extract_bugs_from_daily_standup(
        self,
        report_content: Dict[str, Any],
        report_id: int,
        transcript_id: int,
        project_id: int,
        meeting_date: date
    ) -> List[Dict[str, Any]]:
        """Extract recurring blockers from daily standup (potential bugs)"""
        bugs = []
        
        # Check blockers section
        blockers = report_content.get('blockers', [])
        if isinstance(blockers, list):
            for blocker in blockers:
                if isinstance(blocker, str) and self._is_bug_related(blocker):
                    is_recurring = self._is_recurring_indicator(blocker)
                    bugs.append({
                        'description': blocker,
                        'source_type': 'daily_standup_blocker',
                        'severity': 'high',  # Blockers are high priority
                        'is_recurring_indicator': is_recurring
                    })
        
        for bug in bugs:
            await self._upsert_recurring_bug(
                description=bug['description'],
                severity=bug['severity'],
                source_type=bug['source_type'],
                report_id=report_id,
                transcript_id=transcript_id,
                project_id=project_id,
                meeting_date=meeting_date
            )
        
        logger.info(f"Extracted {len(bugs)} potential bugs from daily standup report {report_id}")
        return bugs
    
    async def extract_bugs_from_sprint_meeting(
        self,
        report_content: Dict[str, Any],
        report_id: int,
        transcript_id: int,
        project_id: int,
        meeting_date: date
    ) -> List[Dict[str, Any]]:
        """Extract issues/risks from sprint meeting"""
        bugs = []
        
        # Check issues_risks section
        issues = report_content.get('issues_risks', report_content.get('issues_and_risks', []))
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, str) and self._is_bug_related(issue):
                    is_recurring = self._is_recurring_indicator(issue)
                    bugs.append({
                        'description': issue,
                        'source_type': 'sprint_meeting_issue',
                        'severity': self._determine_severity(issue, is_recurring),
                        'is_recurring_indicator': is_recurring
                    })
        
        for bug in bugs:
            await self._upsert_recurring_bug(
                description=bug['description'],
                severity=bug['severity'],
                source_type=bug['source_type'],
                report_id=report_id,
                transcript_id=transcript_id,
                project_id=project_id,
                meeting_date=meeting_date
            )
        
        logger.info(f"Extracted {len(bugs)} potential bugs from sprint meeting report {report_id}")
        return bugs
    
    async def _upsert_recurring_bug(
        self,
        description: str,
        severity: str,
        source_type: str,
        report_id: int,
        transcript_id: int,
        project_id: int,
        meeting_date: date
    ) -> Optional[int]:
        """Insert new bug or update existing recurring bug"""
        bug_hash = self._generate_bug_hash(description)
        bug_category = self._extract_bug_category(description)
        
        # Format meeting_date
        meeting_date_str = meeting_date.isoformat() if isinstance(meeting_date, date) else str(meeting_date)
        
        # Check if bug already exists (by hash within same project)
        check_query = f"""
            SELECT id, mention_count, sources, first_reported_date, severity
            FROM `{self.tenant_schema}`.recurring_bugs
            WHERE bug_hash = %s AND project_id = %s AND status NOT IN ('resolved', 'dismissed', 'wont_fix')
        """
        existing = await self.db.execute_query(check_query, (bug_hash, project_id), fetch_all=True)
        
        source_entry = {
            'report_id': report_id,
            'transcript_id': transcript_id,
            'meeting_date': meeting_date_str,
            'source_type': source_type
        }
        
        if existing and len(existing) > 0:
            # Update existing bug - increment count and add source
            bug = existing[0]
            current_sources = json.loads(bug['sources']) if isinstance(bug['sources'], str) else (bug['sources'] or [])
            
            # Avoid duplicate sources (same report_id)
            if not any(s.get('report_id') == report_id for s in current_sources):
                current_sources.append(source_entry)
                new_mention_count = bug['mention_count'] + 1
                
                # Auto-escalate severity based on mention count
                new_severity = bug['severity']
                if new_mention_count >= 4:
                    new_severity = 'critical'
                elif new_mention_count >= 3:
                    new_severity = 'high'
                elif new_mention_count >= 2 and bug['severity'] == 'low':
                    new_severity = 'medium'
                
                update_query = f"""
                    UPDATE `{self.tenant_schema}`.recurring_bugs
                    SET mention_count = %s,
                        last_reported_date = %s,
                        sources = %s,
                        severity = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """
                await self.db.execute_query(
                    update_query, 
                    (new_mention_count, meeting_date_str, json.dumps(current_sources), new_severity, bug['id']),
                    commit=True
                )
                
                logger.info(f"Updated recurring bug {bug['id']}, now mentioned {new_mention_count} times, severity: {new_severity}")
                return bug['id']
            else:
                logger.debug(f"Bug already recorded from report {report_id}, skipping")
                return bug['id']
        else:
            # Insert new bug
            insert_query = f"""
                INSERT INTO `{self.tenant_schema}`.recurring_bugs
                (project_id, bug_hash, bug_description, bug_category, 
                 first_reported_date, last_reported_date, mention_count,
                 sources, severity, status)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, 'open')
            """
            result = await self.db.execute_query(
                insert_query, 
                (
                    project_id,
                    bug_hash,
                    description[:1000],  # Truncate to max length
                    bug_category,
                    meeting_date_str,
                    meeting_date_str,
                    json.dumps([source_entry]),
                    severity
                ),
                commit=True
            )
            
            bug_id = result.lastrowid if result else None
            logger.info(f"Created new bug {bug_id} for project {project_id}, category: {bug_category}")
            return bug_id
    
    async def get_recurring_bugs(
        self,
        project_id: Optional[int] = None,
        min_mentions: int = 1,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get bugs with optional filters"""
        where_clauses = ["mention_count >= %s"]
        params: List[Any] = [min_mentions]
        
        if project_id:
            where_clauses.append("project_id = %s")
            params.append(project_id)
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `{self.tenant_schema}`.recurring_bugs
            WHERE {where_sql}
        """
        count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0
        
        # Fetch bugs
        offset = (page - 1) * page_size
        fetch_params = params + [page_size, offset]
        
        query = f"""
            SELECT rb.*, p.project_name
            FROM `{self.tenant_schema}`.recurring_bugs rb
            LEFT JOIN `{self.tenant_schema}`.projects p ON rb.project_id = p.project_id
            WHERE {where_sql}
            ORDER BY 
                CASE WHEN rb.status = 'open' THEN 0 ELSE 1 END,
                rb.mention_count DESC, 
                rb.last_reported_date DESC
            LIMIT %s OFFSET %s
        """
        
        results = await self.db.execute_query(query, tuple(fetch_params), fetch_all=True)
        
        # Parse sources JSON
        bugs = []
        for row in results or []:
            bug = dict(row)
            if isinstance(bug.get('sources'), str):
                bug['sources'] = json.loads(bug['sources'])
            bugs.append(bug)
        
        return {
            'bugs': bugs,
            'total': total,
            'page': page,
            'page_size': page_size
        }
    
    async def get_bug(self, bug_id: int) -> Optional[Dict[str, Any]]:
        """Get a single bug by ID"""
        query = f"""
            SELECT rb.*, p.project_name
            FROM `{self.tenant_schema}`.recurring_bugs rb
            LEFT JOIN `{self.tenant_schema}`.projects p ON rb.project_id = p.project_id
            WHERE rb.id = %s
        """
        result = await self.db.execute_query(query, (bug_id,), fetch_one=True)
        
        if result:
            bug = dict(result)
            if isinstance(bug.get('sources'), str):
                bug['sources'] = json.loads(bug['sources'])
            return bug
        return None
    
    async def update_bug_status(
        self,
        bug_id: int,
        status: str,
        resolution_notes: Optional[str] = None,
        resolved_by: Optional[str] = None
    ) -> bool:
        """Update bug status"""
        resolved_date = datetime.now().date() if status == 'resolved' else None
        
        query = f"""
            UPDATE `{self.tenant_schema}`.recurring_bugs
            SET status = %s,
                resolution_notes = COALESCE(%s, resolution_notes),
                resolved_date = %s,
                resolved_by = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        await self.db.execute_query(
            query, 
            (status, resolution_notes, resolved_date, resolved_by, bug_id),
            commit=True
        )
        return True
    
    async def create_backlog_item_for_bug(
        self,
        bug_id: int,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """Create a backlog item for a recurring bug"""
        bug = await self.get_bug(bug_id)
        
        if not bug:
            return None
        
        # Generate backlog ID
        backlog_id = f"BUG-{int(datetime.now().timestamp() * 1000)}"
        
        # Map severity to priority
        severity_to_priority = {
            'critical': 'high',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        
        # Build description
        description = f"""**Recurring Bug Report**

This bug has been reported **{bug['mention_count']} times** across different meetings.

**Category:** {bug.get('bug_category', 'other')}
**Severity:** {bug.get('severity', 'medium')}
**First reported:** {bug.get('first_reported_date')}
**Last reported:** {bug.get('last_reported_date')}

**Description:**
{bug['bug_description']}

**Impact:**
{bug.get('impact_description', 'Not specified')}

---
*Auto-generated from recurring bug tracking*
"""
        
        # Create backlog item
        insert_query = f"""
            INSERT INTO `{self.tenant_schema}`.project_backlog
            (id, project_id, summary, description, issue_type, status, 
             priority, severity, is_jira, created_at)
            VALUES (%s, %s, %s, %s, 'bug', 'todo', %s, %s, 0, NOW())
        """
        
        await self.db.execute_query(
            insert_query,
            (
                backlog_id,
                bug['project_id'],
                f"[Recurring] {bug['bug_description'][:180]}",
                description,
                severity_to_priority.get(bug.get('severity', 'medium'), 'medium'),
                bug.get('severity', 'medium')
            ),
            commit=True
        )
        
        # Update bug with backlog reference
        update_query = f"""
            UPDATE `{self.tenant_schema}`.recurring_bugs
            SET backlog_item_id = %s, status = 'investigating'
            WHERE id = %s
        """
        await self.db.execute_query(update_query, (backlog_id, bug_id), commit=True)
        
        logger.info(f"Created backlog item {backlog_id} for recurring bug {bug_id}")
        return backlog_id
