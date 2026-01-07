-- Fix parent_task_id for all subtasks
-- This updates subtasks to properly link to their parent tasks

-- Update subtasks to set parent_task_id based on their ID pattern
-- Example: TAM-52-SUB-1 gets parent_task_id = TAM-52

UPDATE project_backlog
SET parent_task_id = SUBSTRING(id, 1, LOCATE('-SUB-', id) - 1)
WHERE id LIKE '%-SUB-%'
  AND (parent_task_id IS NULL OR parent_task_id = '');

-- Verify the update
SELECT 
    id,
    parent_task_id,
    summary
FROM project_backlog
WHERE id LIKE '%-SUB-%'
ORDER BY parent_task_id, id
LIMIT 20;
