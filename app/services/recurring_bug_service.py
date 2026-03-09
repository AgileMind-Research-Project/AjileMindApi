"""
Recurring Bug Service

Simplified approach:
1. Store only actual bugs (not general issues)
2. Use hash to identify similar bugs
3. Bugs with same hash appearing 2+ times = recurring
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
import hashlib
import re

from app.db.database import Database
from app.core.logger import logger

# Keywords that indicate actual software bugs (not general process issues)
BUG_KEYWORDS = [
    'bug', 'error', 'crash', 'exception', 'fail', 'broken', 'fix', 'fixed',
    'defect', 'issue', 'problem', 'not working', 'doesnt work', "doesn't work",
    'cannot', "can't", 'unable', 'incorrect', 'wrong', 'unexpected',
    'null', 'undefined', 'timeout', 'memory leak', 'performance',
    'slow', 'hang', 'freeze', 'stuck', '500', '404', '403', '401',
    'api', 'database', 'server', 'client', 'frontend', 'backend',
    'login', 'authentication', 'authorization', 'permission',
    'display', 'render', 'layout', 'ui', 'ux', 'button', 'form',
    'submit', 'save', 'load', 'fetch', 'request', 'response',
    'validation', 'input', 'output', 'data', 'missing', 'duplicate',
    'regression', 'compatibility', 'browser', 'mobile', 'responsive'
]


class RecurringBugService:
    """Service for managing recurring bugs"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def _is_bug_related(self, text: str) -> bool:
        """Check if text describes an actual software bug"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in BUG_KEYWORDS)
    
    def _generate_bug_hash(self, text: str) -> str:
        """
        Generate hash for bug text to find similar bugs.
        Normalizes text: lowercase, remove extra spaces, remove common words
        """
        # Normalize
        text = text.lower().strip()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        # Remove common filler words for better matching
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'been', 'be', 
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                      'could', 'should', 'may', 'might', 'must', 'shall', 'can',
                      'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                      'from', 'as', 'into', 'through', 'during', 'before', 'after',
                      'above', 'below', 'between', 'under', 'again', 'further',
                      'then', 'once', 'here', 'there', 'when', 'where', 'why',
                      'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some',
                      'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                      'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
                      'because', 'until', 'while', 'this', 'that', 'these', 'those',
                      'still', 'yet', 'also', 'keep', 'keeps', 'keeping', 'it', 'its'}
        words = [w for w in text.split() if w not in stop_words and len(w) > 2]
        normalized = ' '.join(sorted(words))  # Sort for consistency
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def store_bug(
        self,
        tenant_schema: str,
        project_id: int,
        report_id: int,
        transcript_id: int,
        bug_title: str,
        source_section: str,
        meeting_date: Optional[date] = None,
        bug_description: Optional[str] = None
    ) -> Optional[int]:
        """Store a bug from a report"""
        try:
            bug_hash = self._generate_bug_hash(bug_title)
            meeting_date_val = meeting_date or date.today()
            
            query = f"""
                INSERT INTO `{tenant_schema}`.recurring_bugs 
                (project_id, report_id, transcript_id, bug_title, bug_description, 
                 source_section, bug_hash, meeting_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open')
            """
            
            result = await self.db.execute_query(
                query,
                (
                    project_id,
                    report_id,
                    transcript_id,
                    bug_title[:500],  # Truncate if too long
                    bug_description,
                    source_section,
                    bug_hash,
                    meeting_date_val
                ),
                commit=True,
                schema=tenant_schema
            )
            
            bug_id = result if result else None
            logger.info(f"Stored bug: '{bug_title[:50]}...' (hash: {bug_hash[:8]})")
            return bug_id
            
        except Exception as e:
            logger.error(f"Error storing bug: {e}")
            return None
    
    async def store_bugs_from_report(
        self,
        tenant_schema: str,
        project_id: int,
        report_id: int,
        transcript_id: int,
        report_content: Dict[str, Any],
        report_type: str,
        meeting_date: Optional[date] = None
    ) -> int:
        """Extract and store only actual bugs from a report (filters using keywords)"""
        bugs_stored = 0
        
        try:
            if report_type == 'retrospective':
                # Extract from what_didnt_go_well (only bug-related items)
                items = report_content.get('what_didnt_go_well', [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.strip() and self._is_bug_related(item):
                            result = await self.store_bug(
                                tenant_schema, project_id, report_id, transcript_id,
                                item.strip(), 'what_didnt_go_well', meeting_date
                            )
                            if result:
                                bugs_stored += 1
                
                # Extract from action_points (only bug fix items)
                actions = report_content.get('action_points', [])
                if isinstance(actions, list):
                    for action in actions:
                        action_text = ''
                        if isinstance(action, dict):
                            action_text = action.get('action', action.get('task', ''))
                        elif isinstance(action, str):
                            action_text = action
                        
                        if action_text and action_text.strip() and self._is_bug_related(action_text):
                            result = await self.store_bug(
                                tenant_schema, project_id, report_id, transcript_id,
                                action_text.strip(), 'action_points', meeting_date
                            )
                            if result:
                                bugs_stored += 1
            
            elif report_type == 'daily_standup':
                # Extract from team_updates -> blockers (only bug-related)
                team_updates = report_content.get('team_updates', [])
                if isinstance(team_updates, list):
                    for update in team_updates:
                        if isinstance(update, dict):
                            blockers = update.get('blockers', [])
                            if isinstance(blockers, list):
                                for blocker in blockers:
                                    if isinstance(blocker, str) and blocker.strip() and self._is_bug_related(blocker):
                                        result = await self.store_bug(
                                            tenant_schema, project_id, report_id, transcript_id,
                                            blocker.strip(), 'blockers', meeting_date
                                        )
                                        if result:
                                            bugs_stored += 1
                
                # Extract from blockers_summary (new developer-centric format)
                blockers_summary = report_content.get('blockers_summary', [])
                if isinstance(blockers_summary, list):
                    for bs in blockers_summary:
                        if isinstance(bs, dict):
                            desc = bs.get('description') or bs.get('title', '')
                            if desc and desc.strip() and self._is_bug_related(desc):
                                result = await self.store_bug(
                                    tenant_schema, project_id, report_id, transcript_id,
                                    desc.strip(), 'blockers_summary', meeting_date
                                )
                                if result:
                                    bugs_stored += 1
                
                # Also check for standalone blockers field (legacy format)
                standalone_blockers = report_content.get('blockers', [])
                if isinstance(standalone_blockers, list):
                    for blocker in standalone_blockers:
                        if isinstance(blocker, str) and blocker.strip() and self._is_bug_related(blocker):
                            result = await self.store_bug(
                                tenant_schema, project_id, report_id, transcript_id,
                                blocker.strip(), 'blockers', meeting_date
                            )
                            if result:
                                bugs_stored += 1
            
            elif report_type == 'sprint_meeting':
                # Extract from issues_and_risks (only bug-related)
                issues = report_content.get('issues_and_risks', report_content.get('issues_risks', []))
                if isinstance(issues, list):
                    for issue in issues:
                        if isinstance(issue, str) and issue.strip() and self._is_bug_related(issue):
                            result = await self.store_bug(
                                tenant_schema, project_id, report_id, transcript_id,
                                issue.strip(), 'issues_and_risks', meeting_date
                            )
                            if result:
                                bugs_stored += 1
            
            logger.info(f"Stored {bugs_stored} bugs from {report_type} report {report_id}")
            return bugs_stored
            
        except Exception as e:
            logger.error(f"Error storing bugs from report: {e}")
            return bugs_stored
    
    async def list_bugs(
        self,
        tenant_schema: str,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        show_all: bool = False,  # False = only recurring (2+), True = show all
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List bugs grouped by hash.
        By default, only shows recurring bugs (mention_count >= 2)
        """
        try:
            where_clauses = []
            params: List[Any] = []
            
            if project_id:
                where_clauses.append("rb.project_id = %s")
                params.append(project_id)
            
            if status:
                where_clauses.append("rb.status = %s")
                params.append(status)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # HAVING clause filters for recurring (2+) unless show_all is True
            # MySQL doesn't allow column aliases in HAVING, use COUNT(*) directly
            having_clause = "" if show_all else "HAVING COUNT(*) >= 2"
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total FROM (
                    SELECT bug_hash
                    FROM `{tenant_schema}`.recurring_bugs rb
                    WHERE {where_sql}
                    GROUP BY bug_hash
                    {having_clause}
                ) as grouped_bugs
            """
            count_result = await self.db.execute_query(count_query, tuple(params), fetch_one=True)
            total = count_result['total'] if count_result else 0
            
            # Get paginated grouped results
            offset = (page - 1) * page_size
            query = f"""
                SELECT 
                    bug_hash,
                    MIN(rb.id) as id,
                    rb.project_id,
                    MAX(rb.bug_title) as bug_title,
                    COUNT(*) as mention_count,
                    MIN(rb.meeting_date) as first_reported,
                    MAX(rb.meeting_date) as last_reported,
                    GROUP_CONCAT(DISTINCT rb.source_section) as sources,
                    MAX(rb.status) as status
                FROM `{tenant_schema}`.recurring_bugs rb
                WHERE {where_sql}
                GROUP BY bug_hash, rb.project_id
                {having_clause}
                ORDER BY mention_count DESC, last_reported DESC
                LIMIT %s OFFSET %s
            """
            fetch_params = params + [page_size, offset]
            
            results = await self.db.execute_query(query, tuple(fetch_params), fetch_all=True)
            
            # Format results
            bugs = []
            for row in results or []:
                first_reported = row['first_reported']
                last_reported = row['last_reported']
                
                bugs.append({
                    'id': row['id'],
                    'bug_hash': row['bug_hash'],
                    'project_id': row['project_id'],
                    'bug_title': row['bug_title'],
                    'mention_count': row['mention_count'],
                    'first_reported': first_reported.isoformat() if first_reported else None,
                    'last_reported': last_reported.isoformat() if last_reported else None,
                    'sources': row['sources'].split(',') if row['sources'] else [],
                    'status': row['status'],
                    'is_recurring': row['mention_count'] >= 2
                })
            
            return {
                'bugs': bugs,
                'total': total,
                'page': page,
                'page_size': page_size
            }
            
        except Exception as e:
            logger.error(f"Error listing bugs: {e}")
            raise
    
    async def get_bug_details(
        self,
        tenant_schema: str,
        bug_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get all occurrences of a bug by its hash"""
        try:
            query = f"""
                SELECT 
                    rb.*,
                    t.title as transcript_title
                FROM `{tenant_schema}`.recurring_bugs rb
                LEFT JOIN `{tenant_schema}`.transcripts t ON rb.transcript_id = t.id
                WHERE rb.bug_hash = %s
                ORDER BY rb.meeting_date DESC
            """
            
            results = await self.db.execute_query(query, (bug_hash,), fetch_all=True)
            
            if not results:
                return None
            
            # Format result
            occurrences = []
            for row in results:
                meeting_date = row['meeting_date']
                occurrences.append({
                    'id': row['id'],
                    'bug_title': row['bug_title'],
                    'source_section': row['source_section'],
                    'meeting_date': meeting_date.isoformat() if meeting_date else None,
                    'transcript_id': row['transcript_id'],
                    'transcript_title': row.get('transcript_title'),
                    'report_id': row['report_id'],
                    'status': row['status']
                })
            
            first_row = results[0]
            first_reported = occurrences[-1]['meeting_date'] if occurrences else None
            last_reported = occurrences[0]['meeting_date'] if occurrences else None
            
            return {
                'bug_hash': bug_hash,
                'bug_title': first_row['bug_title'],
                'project_id': first_row['project_id'],
                'mention_count': len(occurrences),
                'is_recurring': len(occurrences) >= 2,
                'first_reported': first_reported,
                'last_reported': last_reported,
                'occurrences': occurrences
            }
            
        except Exception as e:
            logger.error(f"Error getting bug details: {e}")
            raise
    
    async def update_bug_status(
        self,
        tenant_schema: str,
        bug_hash: str,
        status: str
    ) -> bool:
        """Update status for all occurrences of a bug"""
        try:
            query = f"""
                UPDATE `{tenant_schema}`.recurring_bugs
                SET status = %s, updated_at = NOW()
                WHERE bug_hash = %s
            """
            
            await self.db.execute_query(query, (status, bug_hash), commit=True)
            return True
            
        except Exception as e:
            logger.error(f"Error updating bug status: {e}")
            return False
    
    async def create_backlog_item(
        self,
        tenant_schema: str,
        bug_hash: str
    ) -> Optional[str]:
        """Create a backlog item for a recurring bug"""
        try:
            # Get bug details
            bug = await self.get_bug_details(tenant_schema, bug_hash)
            if not bug:
                raise ValueError("Bug not found")
            
            # Generate backlog ID
            backlog_id = f"BUG-{int(datetime.now().timestamp() * 1000)}"
            
            # Determine priority based on mention count
            mention_count = bug['mention_count']
            if mention_count >= 4:
                priority = 'high'
                severity = 'critical'
            elif mention_count >= 3:
                priority = 'high'
                severity = 'high'
            elif mention_count >= 2:
                priority = 'medium'
                severity = 'medium'
            else:
                priority = 'low'
                severity = 'low'
            
            # Create description
            description = (
                f"RECURRING BUG - Mentioned {mention_count} times\n\n"
                f"First reported: {bug['first_reported']}\n"
                f"Last reported: {bug['last_reported']}\n\n"
                f"Occurrences:\n"
            )
            for occ in bug['occurrences'][:5]:  # Show last 5 occurrences
                description += f"- {occ['meeting_date']}: {occ['source_section']}\n"
            
            # Create backlog item
            query = f"""
                INSERT INTO `{tenant_schema}`.project_backlog
                (id, project_id, summary, description, issue_type, status, 
                 priority, severity, is_jira, created_at)
                VALUES (%s, %s, %s, %s, 'bug', 'todo', %s, %s, 0, NOW())
            """
            
            await self.db.execute_query(
                query,
                (
                    backlog_id,
                    bug['project_id'],
                    f"[Recurring] {bug['bug_title'][:200]}",
                    description,
                    priority,
                    severity
                ),
                commit=True
            )
            
            # Update bug status to 'resolved' (being worked on)
            await self.update_bug_status(tenant_schema, bug_hash, 'resolved')
            
            logger.info(f"Created backlog item {backlog_id} for recurring bug {bug_hash[:8]}")
            return backlog_id
            
        except Exception as e:
            logger.error(f"Error creating backlog item: {e}")
            raise
