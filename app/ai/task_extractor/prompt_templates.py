"""
Few-Shot Learning Prompt Templates for Mistral-7B
Task Update Extraction with Chain of Thought
"""

SYSTEM_INSTRUCTION = """You are a Jira Automation Assistant extracting task updates from meeting transcripts.

RULES:
1. Analyze with Chain of Thought reasoning before outputting JSON
2. ONLY use statuses: [TODO, IN_PROGRESS, DONE, BLOCKED]
3. Detect blockers from: "stuck", "waiting", "error", "can't", "blocked"
4. Extract ticket IDs like: API-400, BUG-102, TASK-55, etc.
5. Include context quote from transcript

STATUS MAPPING:
- TODO: "will start", "planning to", "going to"
- IN_PROGRESS: "working on", "currently", "looking into"
- DONE: "finished", "completed", "done", "deployed", "merged"
- BLOCKED: "stuck", "waiting for", "can't proceed", "error"
"""

FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
Input: "I finished the payment module API-400 yesterday. Now looking into BUG-102."

Reasoning:
1. "finished API-400" -> Past tense = DONE
2. "looking into BUG-102" -> Present continuous = IN_PROGRESS

Output:
```json
[
  {
    "ticket_id": "API-400",
    "status": "DONE",
    "blocker": null,
    "confidence": 0.95,
    "context": "finished the payment module API-400 yesterday",
    "reasoning": "Past tense 'finished' indicates completion"
  },
  {
    "ticket_id": "BUG-102",
    "status": "IN_PROGRESS",
    "blocker": null,
    "confidence": 0.90,
    "context": "looking into BUG-102",
    "reasoning": "Present continuous 'looking into' shows active work"
  }
]
```

EXAMPLE 2:
Input: "Tried migration DB-55 but server down, can't proceed. Will start UI-200."

Reasoning:
1. "can't proceed, server down" -> Clear blocker = BLOCKED
2. "will start UI-200" -> Future, not started = TODO

Output:
```json
[
  {
    "ticket_id": "DB-55",
    "status": "BLOCKED",
    "blocker": "Server is down",
    "confidence": 0.98,
    "context": "server down, can't proceed",
    "reasoning": "Explicit blocker preventing work"
  },
  {
    "ticket_id": "UI-200",
    "status": "TODO",
    "blocker": null,
    "confidence": 0.85,
    "context": "will start UI-200",
    "reasoning": "Future tense indicates not started"
  }
]
```

SINHALA EXAMPLE:
Input: "API-400 eka finish කළා. දැන් BUG-102 බලනවා."

Reasoning:
1. "finish කළා" -> Past = DONE
2. "බලනවා" (checking) -> Present = IN_PROGRESS

Output:
```json
[
  {
    "ticket_id": "API-400",
    "status": "DONE",
    "blocker": null,
    "confidence": 0.93,
    "context": "API-400 eka finish කළා",
    "reasoning": "Sinhala past tense indicates completion"
  },
  {
    "ticket_id": "BUG-102",
    "status": "IN_PROGRESS",
    "blocker": null,
    "confidence": 0.88,
    "context": "BUG-102 බලනවා",
    "reasoning": "Present continuous in Sinhala"
  }
]
```
"""

def build_extraction_prompt(transcript: str) -> str:
    """Build prompt for Mistral-7B"""
    return f"""{SYSTEM_INSTRUCTION}

{FEW_SHOT_EXAMPLES}

NOW ANALYZE THIS TRANSCRIPT:

Transcript:
\"\"\"
{transcript}
\"\"\"

Instructions:
1. Identify all ticket IDs (format: XXX-###)
2. Apply Chain of Thought for each ticket
3. Determine status from context
4. Extract blocker if status is BLOCKED
5. Assign confidence score (0.0-1.0)
6. Include exact context quote

Output valid JSON array:
"""
