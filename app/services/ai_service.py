"""
AI Service for Transcript Analysis
======================================================
Primary:  Two-pass deterministic regex parser
          (global TAM-ID scan + nearest-speaker lookup)
Fallback: Ollama LLM (llama3.2:1b, num_ctx=8192) for unstructured text
Final  :  OpenAI GPT-4 cloud fallback
"""

import re
import json
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Ollama options — tuned for llama3.2:1b (fast, low RAM local model)
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_OPTIONS = {
    "temperature":    0.1,
    "num_ctx":        4096,   # prompt + transcript + output all fit without overflow
    "num_predict":    1500,
    "top_k":          10,
    "top_p":          0.9,
    "repeat_penalty": 1.1,
    "seed":           42,
    "num_thread":     4,
}

OLLAMA_CONNECT_TIMEOUT = 10
OLLAMA_READ_TIMEOUT    = 600   # 10 min — extended for large transcripts on local hardware
OPENAI_TOTAL_TIMEOUT   = 120


class AIService:

    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "ollama").strip().lower()
        self.openai_api_key  = settings.OPENAI_API_KEY
        self.openai_model    = settings.OPENAI_MODEL
        self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_chat_url = f"{self.ollama_base_url}/api/chat"
        self.local_model     = settings.OLLAMA_MODEL   # e.g. "llama3.2:1b"

        logger.info(
            "[AIService] Ready | "
            f"Provider={self.provider} | "
            f"Ollama {self.local_model} @ {self.ollama_base_url} (ctx=4096) | "
            f"OpenAI {self.openai_model}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC — main entry point called by the meetings endpoint
    # ─────────────────────────────────────────────────────────────────────────
    async def analyze_transcript(self, transcript_content: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Always uses Ollama LLM — handles any transcript format without assumptions.
        Falls back to regex parsers if LLM fails/times out, then OpenAI as last resort.
        All results are deduplicated before returning.
        """
        empty = {"tasks": [], "leave_info": [], "bugs": []}
        tc = transcript_content or ""

        has_task_ids = bool(re.search(r"\b[A-Z]{1,10}-\d+\b", tc))
        task_id_count = len(re.findall(r"\b[A-Z]{1,10}-\d+\b", tc))
        line_count = tc.count("\n") + 1
        transcript_type = "STRUCTURED (has task IDs)" if has_task_ids else "FREE-FORM (no task IDs)"

        logger.info("=" * 70)
        logger.info("[TRANSCRIPT ANALYSIS STARTED]")
        logger.info(f"  Length      : {len(tc)} chars | {line_count} lines")
        logger.info(f"  Type        : {transcript_type}")
        logger.info(f"  Task IDs    : {task_id_count} found")
        if self.provider == "openai":
            logger.info("  Strategy    : OpenAI LLM first → Regex fallback")
            logger.info(f"  Model       : {self.openai_model} (OpenAI)")
        else:
            logger.info("  Strategy    : Ollama LLM first → Regex fallback → OpenAI fallback")
            logger.info(f"  Model       : {self.local_model} @ {self.ollama_base_url}")
        logger.info(f"  Timeout     : {OLLAMA_READ_TIMEOUT}s")
        logger.info("=" * 70)

        prompt = self._build_llm_prompt(tc, category)
        result = None

        # ── Step 1: LLM (provider-specific) ──────────────────────────────────
        if self.provider == "openai":
            logger.info("[STEP 1] Sending to OpenAI LLM ...")
            result = await self._call_openai(prompt)
            if result and (result.get("tasks") or result.get("leave_info") or result.get("bugs")):
                result = self._deduplicate(result)
                logger.info(
                    f"[RESULT] ✓ Source=OPENAI_LLM | "
                    f"tasks={len(result.get('tasks', []))} | "
                    f"leaves={len(result.get('leave_info', []))} | "
                    f"bugs={len(result.get('bugs', []))}"
                )
                logger.info("=" * 70)
                return result
            logger.warning("[STEP 1] OpenAI LLM returned empty or timed out.")
        else:
            logger.info("[STEP 1] Sending to Ollama LLM ...")
            result = await self._call_ollama(prompt)
            if result and (result.get("tasks") or result.get("leave_info") or result.get("bugs")):
                result = self._deduplicate(result)
                logger.info(
                    f"[RESULT] ✓ Source=OLLAMA_LLM | "
                    f"tasks={len(result.get('tasks', []))} | "
                    f"leaves={len(result.get('leave_info', []))} | "
                    f"bugs={len(result.get('bugs', []))}"
                )
                logger.info("=" * 70)
                return result
            logger.warning("[STEP 1] Ollama LLM returned empty or timed out.")

        # ── Step 2: Regex fallback ────────────────────────────────────────────
        logger.info("[STEP 2] Trying regex parsers as fallback ...")
        if has_task_ids:
            logger.info(f"  Task IDs detected ({task_id_count}) — running structured + conversational parsers.")
            structured = self._parse_structured_transcript(tc)
            convo      = self._parse_conversational_transcript(tc)
            logger.info(
                f"  Structured parser : {len(structured['tasks'])} tasks, {len(structured['leave_info'])} leaves"
            )
            logger.info(
                f"  Conversational parser: {len(convo['tasks'])} tasks, {len(convo['leave_info'])} leaves"
            )
            seen = {t["task_id"] for t in structured["tasks"]}
            for t in convo["tasks"]:
                if t["task_id"] not in seen:
                    structured["tasks"].append(t)
                    seen.add(t["task_id"])
            leave_keys = {(l["developer_name"], l["leave_date"]) for l in structured["leave_info"]}
            for l in convo["leave_info"]:
                key = (l["developer_name"], l["leave_date"])
                if key not in leave_keys:
                    structured["leave_info"].append(l)
                    leave_keys.add(key)
            if structured["tasks"] or structured["leave_info"]:
                structured = self._deduplicate(structured)
                logger.info(
                    f"[RESULT] ✓ Source=REGEX_FALLBACK | "
                    f"tasks={len(structured['tasks'])} | "
                    f"leaves={len(structured['leave_info'])}"
                )
                logger.info("=" * 70)
                return structured
        else:
            logger.warning("  No task IDs in transcript — regex parsers skipped.")

        logger.warning("[STEP 2] Regex parsers returned nothing.")

        # ── Step 3: OpenAI fallback (only when Ollama is the provider) ───────
        if self.provider == "openai":
            logger.warning("[STEP 3] OpenAI already tried. No additional fallback configured.")
            logger.info("=" * 70)
            return empty

        logger.info("[STEP 3] Trying OpenAI cloud fallback ...")
        openai_ok = (
            self.openai_api_key
            and "your-openai-key" not in self.openai_api_key
            and self.openai_api_key != "sk-your-openai-key-here"
        )
        if not openai_ok:
            logger.error(
                "[STEP 3] No valid OpenAI key configured."
            )
            return empty

        result = await self._call_openai(prompt)
        if result and (result.get("tasks") or result.get("leave_info") or result.get("bugs")):
            result = self._deduplicate(result)
            logger.info(
                f"[RESULT] ✓ Source=OPENAI_FALLBACK | "
                f"tasks={len(result.get('tasks', []))} | "
                f"leaves={len(result.get('leave_info', []))} | "
                f"bugs={len(result.get('bugs', []))}"
            )
        else:
            logger.error("[RESULT] ✗ Source=NONE | All methods failed.")
        logger.info("=" * 70)
        return result if result else empty

    # ─────────────────────────────────────────────────────────────────────────
    # DEDUPLICATOR — removes duplicate task_ids and duplicate leave entries
    # ─────────────────────────────────────────────────────────────────────────
    def _deduplicate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove duplicate tasks (by task_id, keep first occurrence)
        and duplicate leave entries (by developer_name + leave_date, keep first).
        Logs how many duplicates were removed.
        """
        # Tasks — deduplicate by task_id
        seen_tasks: set = set()
        unique_tasks = []
        for t in result.get("tasks", []):
            tid = (t.get("task_id") or "").upper()
            if tid and tid not in seen_tasks:
                seen_tasks.add(tid)
                unique_tasks.append(t)
        dup_tasks = len(result.get("tasks", [])) - len(unique_tasks)

        # Leave — deduplicate by (developer_name, leave_date)
        seen_leaves: set = set()
        unique_leaves = []
        for l in result.get("leave_info", []):
            key = (l.get("developer_name", "").lower(), l.get("leave_date", ""))
            if key not in seen_leaves:
                seen_leaves.add(key)
                unique_leaves.append(l)
        dup_leaves = len(result.get("leave_info", [])) - len(unique_leaves)

        # Bugs — deduplicate by (title, reporter, severity)
        seen_bugs: set = set()
        unique_bugs = []
        for b in result.get("bugs", []):
            key = (b.get("title", "").lower().strip(), b.get("reporter", "").lower(), b.get("severity", "Medium"))
            if key not in seen_bugs:
                seen_bugs.add(key)
                unique_bugs.append(b)
        dup_bugs = len(result.get("bugs", [])) - len(unique_bugs)

        if dup_tasks or dup_leaves or dup_bugs:
            logger.warning(
                f"[Dedup] Removed {dup_tasks} task(s), "
                f"{dup_leaves} leave(s), and {dup_bugs} bug(s)."
            )

        return {"tasks": unique_tasks, "leave_info": unique_leaves, "bugs": unique_bugs}

    def _compress_transcript(self, transcript: str) -> str:
        """
        Extract only the lines relevant to TAM task assignments and leave info.
        For each line containing a TAM-XXX ID, include 4 lines before and 6 lines
        after (to capture the assignee question and the effort reply).
        Also include lines mentioning leave/absence.
        Reduces a 4500-char transcript to ~800 chars so the 1b model can complete
        comfortably within timeout.
        """
        lines = transcript.splitlines()
        total = len(lines)
        keep: set = set()

        for i, line in enumerate(lines):
            if re.search(r"TAM-\d+", line, re.IGNORECASE):
                # include surrounding context window
                for j in range(max(0, i - 4), min(total, i + 7)):
                    keep.add(j)
            if re.search(r"\bleave\b|\babsence\b|\boff\b", line, re.IGNORECASE):
                for j in range(max(0, i - 1), min(total, i + 2)):
                    keep.add(j)

        if not keep:
            # no TAM-IDs found — send full transcript
            return transcript

        result_lines = [lines[i] for i in sorted(keep)]
        compressed = "\n".join(result_lines)
        logger.debug(f"[Compress] Kept {len(keep)}/{total} lines")
        return compressed

    # ─────────────────────────────────────────────────────────────────────────
    # 1a. STRUCTURED TWO-PASS PARSER (inline effort format)
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_structured_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Two-pass parser — format-agnostic.

        Pass 1: Walk every line and build a line→speaker index.
        Pass 2: For every task/leave line look up the current speaker.

        Speaker line formats handled:
          [10:08] user@example.com (ROLE)   ← socket_server auto format
          [10:08] user@example.com           ← no role
          [10:08] Display Name (ROLE)        ← display name (non-email username)
          user@example.com (ROLE)            ← bare email
          (DEVELOPER)                        ← role-only, skip, carry prev speaker

        Task formats (any dash/separator variant):
          Summary (TAM-123) – 16h
          Summary (TAM-123) - 16h
          Summary (TAM-123) — 16h
          Summary (TAM-123)  16h            ← space separator
          - Summary (TAM-123) – 6 SP        ← bullet prefix
        """
        tasks:    list = []
        leaves:   list = []
        seen_ids: set  = set()

        # ── Compiled patterns ──────────────────────────────────────────────────

        # Timestamp + email (most specific — try first)
        # Handles: [10:00] email@domain.com, [10:00] [email@domain.com](mailto:...), [10:00] [email@domain.com]
        ts_email_re = re.compile(
            r"\[?\d{1,2}:\d{2}\]?\s+(?:\[)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})(?:\])?(?:\(mailto:[^)]+\))?",
            re.IGNORECASE,
        )
        # Timestamp + any display name (generic fallback)
        ts_name_re = re.compile(
            r"^\[?\d{1,2}:\d{2}\]?\s+(.+?)(?:\s+\([A-Z_]{2,20}\))?\s*$",
            re.IGNORECASE,
        )
        # Bare "email" or "email (ROLE)" on its own line (handles markdown links and bullets/dashes)
        bare_email_re = re.compile(
            r"^(?:[-*]\s+)?(?:\[)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})(?:\])?(?:\(mailto:[^)]+\))?\s*(?:\(\w+\))?\s*$",
            re.IGNORECASE,
        )
        # Role-only line, e.g. " (DEVELOPER)"
        role_only_re = re.compile(r"^\s*\([A-Z_]{2,20}\)\s*$")

        # Task — any LETTERS-NUMBER prefix, accepts: – — - − ‒ or whitespace as separator
        task_re = re.compile(
            r"(.+?)\s*\(([A-Z]{1,10}-\d+)\)\s*"
            r"[\u2012\u2013\u2014\u2212\-\s:]*\s*"
            r"(\d+(?:\.\d+)?)\s*(h(?:ours?)?|SP|story\s*points?)",
            re.IGNORECASE,
        )

        # Leave detection
        month_map = {
            "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
            "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
        }
        # Range: "on leave from March 10 to March 11, 2026" or "leave from 10 to 12 March"
        leave_range_re = re.compile(
            r"(?:on\s+leave|leave)\s+from\s+(?:(\w+)\s+)?(\d{1,2})\s+to\s+(?:(\w+)\s+)?(\d{1,2})(?:,?\s*(\d{4}))?",
            re.IGNORECASE,
        )
        # Single day: "on leave March 11, 2026" or "on leave on March 11"
        leave_single_re = re.compile(
            r"(?:on\s+leave|leave)\s+(?:on\s+)?"
            r"(january|february|march|april|may|june|july|august|september|october|november|december)"
            r"\s+(\d{1,2})(?:,?\s*(\d{4}))?",
            re.IGNORECASE,
        )

        # ── Pass 1: Build line → speaker index ────────────────────────────────
        lines = transcript.splitlines()
        speaker_at: list = [None] * len(lines)
        current_speaker: Optional[str] = None

        for i, raw in enumerate(lines):
            line = raw.strip()

            # Role-only line: carry speaker forward
            if role_only_re.match(line):
                speaker_at[i] = current_speaker
                continue

            # Timestamp + email (highest priority)
            m = ts_email_re.search(line)
            if m:
                current_speaker = m.group(1).strip()
                speaker_at[i]   = current_speaker
                continue

            # Bare email line
            m = bare_email_re.match(line)
            if m and "@" in m.group(1):
                current_speaker = m.group(1).strip()
                speaker_at[i]   = current_speaker
                continue

            # Timestamp + display name (non-email)
            if re.match(r"^\[?\d{1,2}:\d{2}\]?", line):
                m = ts_name_re.match(line)
                if m:
                    candidate = m.group(1).strip()
                    if candidate:
                        current_speaker = candidate
                        speaker_at[i]   = current_speaker
                        continue

            # Plain content — carry speaker forward
            speaker_at[i] = current_speaker

        # ── Pass 2: Extract tasks and leaves ──────────────────────────────────
        for i, raw in enumerate(lines):
            line    = raw.strip()
            speaker = speaker_at[i]

            # Task
            m = task_re.search(line)
            if m:
                raw_name = m.group(1)
                task_id  = m.group(2).upper()          # e.g. TAM-198, SA-12
                effort_v = float(m.group(3))
                effort   = int(effort_v) if effort_v == int(effort_v) else effort_v
                summary  = re.sub(
                    r"^[\-\u2013\u2014\u2212\u2022*\s]+", "", raw_name
                ).strip()
                if task_id not in seen_ids:
                    seen_ids.add(task_id)
                    tasks.append({
                        "task_id":     task_id,
                        "summary":     summary,
                        "description": self._make_description(summary),
                        "effort":      effort,
                        "assignee":    speaker,
                        "tags":        [],
                    })
                continue

            # Leave — check for multiple matches per line
            for lr in leave_range_re.finditer(line):
                if speaker:
                    m1 = lr.group(1)
                    d1 = int(lr.group(2))
                    m2 = lr.group(3)
                    d2 = int(lr.group(4))
                    year = int(lr.group(5)) if lr.group(5) else 2026
                    
                    mon_num = month_map.get((m1 or m2 or "").lower(), 3)
                    # Simple within-month range (handles 10 to 11)
                    if d1 <= d2:
                        for day in range(d1, d2 + 1):
                            leaves.append({
                                "developer_name": speaker,
                                "leave_date":     f"{year}-{mon_num:02d}-{day:02d}",
                                "leave_hours":    8,
                                "leave_type":     "Full Day",
                                "reason":         "On leave",
                            })
            
            for ls in leave_single_re.finditer(line):
                if speaker:
                    mon_num = month_map.get(ls.group(1).lower(), 3)
                    day     = int(ls.group(2))
                    year    = int(ls.group(3)) if ls.group(3) else 2026
                    leaves.append({
                        "developer_name": speaker,
                        "leave_date":     f"{year}-{mon_num:02d}-{day:02d}",
                        "leave_hours":    8,
                        "leave_type":     "Full Day",
                        "reason":         "On leave",
                    })

        return {"tasks": tasks, "leave_info": leaves}

    # ─────────────────────────────────────────────────────────────────────────
    # 1b. CONVERSATIONAL Q&A PARSER (dialog assignment format)
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_conversational_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Handles transcripts where tasks are assigned via dialog:
          A: 'Can you handle TAM-198?'
          B: 'Yes, I can.'  → B is assignee
          A: 'How long?'
          B: '16 hours.'    → effort=16

        Also handles:
          - Self-assignment: 'I will manage TAM-56 – 16h'
          - Comma-continued IDs: 'TAM-223, 222, 224, 225' → each expanded
          - Any LETTERS-NUMBER prefix (not only TAM-)
        """
        tasks:    list = []
        leaves:   list = []
        seen_ids: set  = set()

        task_id_re  = re.compile(r"\b([A-Z]{1,10}-\d+(?:-[A-Z0-9-]+)?)\b", re.IGNORECASE)
        # Comma-continuation: 'TAM-223, 222, 224, 225' or 'TAM-75, 76, 77'
        short_id_re = re.compile(r"\b([A-Z]{1,10})-(\d+)(?:\s*(?:,|\band\b)\s*(\d+))+", re.IGNORECASE)
        effort_re   = re.compile(
            r"(\d+(?:\.\d+)?)\s*(hours?|h\b|story\s*points?|sp\b|days?)",
            re.IGNORECASE,
        )
        accept_re   = re.compile(
            r"\b(yes|sure|can do|i can|i'll|i will|will do|ok\b|okay|absolutely|definitely|complete|completed|finish|finished|resolved|closed|done)\b",
            re.IGNORECASE,
        )
        self_re     = re.compile(r"\b(i will|i'll|i can|i am going to|i'm going to|my first task|my next task|i worked on|i handled|i improved|i implemented|i also worked)\b", re.IGNORECASE)
        bare_email_re = re.compile(r"^(?:\*\s+)?(?:\[)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})(?:\])?(?:\(mailto:[^)]+\))?\s*(?:\([A-Z_]+\))?\s*$", re.IGNORECASE)
        ts_email_re   = re.compile(r"^\[?\d{1,2}:\d{2}\]?\s+(?:\[)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", re.IGNORECASE)
        # Range: "on leave from May 10 to May 11, 2026" or "leave from 10 to 12 May"
        leave_range_re = re.compile(
            r"(?:on\s+leave|leave)\s+from\s+(?:(\w+)\s+)?(\d{1,2})\s+to\s+(?:(\w+)\s+)?(\d{1,2})(?:,?\s*(\d{4}))?",
            re.IGNORECASE,
        )
        # Single day: "on leave March 11, 2026" or "on leave on March 11"
        leave_single_re = re.compile(
            r"(?:on\s+leave|leave)\s+(?:on\s+)?"
            r"(january|february|march|april|may|june|july|august|september|october|november|december)"
            r"\s+(\d{1,2})(?:,?\s*(\d{4}))?",
            re.IGNORECASE,
        )
        month_map = {
            "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
            "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
        }

        # ── Build speaker blocks ────────────────────────────────────────────
        lines = transcript.splitlines()
        blocks: list = []   # [(speaker, [content_lines])]
        cur_speaker: Optional[str] = None
        cur_lines:   list = []

        for raw in lines:
            stripped = raw.strip()
            m = ts_email_re.match(stripped)
            if m:
                if cur_speaker is not None:
                    blocks.append((cur_speaker, cur_lines))
                cur_speaker = m.group(1).strip()
                cur_lines   = []
            elif cur_speaker is not None:
                cur_lines.append(stripped)
        if cur_speaker is not None:
            blocks.append((cur_speaker, cur_lines))

        # ── Expand comma-continued IDs and collect per-block task IDs ──────
        def expand_ids(text: str) -> list:
            """Return all task IDs found, expanding comma continuations."""
            expanded = text
            for m in short_id_re.finditer(text):
                prefix = m.group(1).upper()
                nums   = re.findall(r"\d+", m.group(0))
                replacement = " ".join(f"{prefix}-{n}" for n in nums)
                expanded = expanded.replace(m.group(0), replacement, 1)
            return [m.group(0).upper() for m in task_id_re.finditer(expanded)]

        # ── Process each block ──────────────────────────────────────────────
        for bi, (speaker, block_lines) in enumerate(blocks):
            block_text = " ".join(block_lines)

            # Leave detection — check for multiple matches per block
            for lr in leave_range_re.finditer(block_text):
                m1 = lr.group(1)
                d1 = int(lr.group(2))
                m2 = lr.group(3)
                d2 = int(lr.group(4))
                year = int(lr.group(5)) if lr.group(5) else 2026
                
                mon_num = month_map.get((m1 or m2 or "").lower(), 3)
                if d1 <= d2:
                    for day in range(d1, d2 + 1):
                        leaves.append({
                            "developer_name": speaker,
                            "leave_date":     f"{year}-{mon_num:02d}-{day:02d}",
                            "leave_hours":    8,
                            "leave_type":     "Full Day",
                            "reason":         "On leave",
                        })
            
            for ls in leave_single_re.finditer(block_text):
                mon_num = month_map.get(ls.group(1).lower(), 3)
                day     = int(ls.group(2))
                year    = int(ls.group(3)) if ls.group(3) else 2026
                leaves.append({
                    "developer_name": speaker,
                    "leave_date":     f"{year}-{mon_num:02d}-{day:02d}",
                    "leave_hours":    8,
                    "leave_type":     "Full Day",
                    "reason":         "On leave",
                })

            all_ids = expand_ids(block_text)
            if not all_ids:
                continue

            # Find addressee: bare email on its own line inside this block
            addressee: Optional[str] = None
            for bl in block_lines:
                em = bare_email_re.match(bl)
                if em and "@" in em.group(1) and em.group(1).lower() != speaker.lower():
                    addressee = em.group(1)
                    break

            is_self = bool(self_re.search(block_text))

            if addressee:
                # Q&A: look ahead for effort from the addressee
                assignee = addressee
                effort   = 0
                for fbi in range(bi + 1, min(bi + 10, len(blocks))):
                    fs, fl = blocks[fbi]
                    if fs.lower() == addressee.lower():
                        em = effort_re.search(" ".join(fl))
                        if em:
                            ev     = float(em.group(1))
                            effort = int(ev) if ev == int(ev) else ev
                            break

            elif is_self:
                # Self-assignment: effort may be inline or in a follow-up block
                assignee = speaker
                em = effort_re.search(block_text)
                if em:
                    ev     = float(em.group(1))
                    effort = int(ev) if ev == int(ev) else ev
                else:
                    effort = 0
                    for fbi in range(bi + 1, min(bi + 4, len(blocks))):
                        fs, fl = blocks[fbi]
                        if fs.lower() == speaker.lower():
                            em = effort_re.search(" ".join(fl))
                            if em:
                                ev     = float(em.group(1))
                                effort = int(ev) if ev == int(ev) else ev
                                break

            else:
                # No addressee, no self — check next block for acceptance
                if bi + 1 >= len(blocks):
                    continue
                ns, nl = blocks[bi + 1]
                nt = " ".join(nl)
                if ns.lower() == speaker.lower() or not accept_re.search(nt):
                    continue
                assignee = ns
                em = effort_re.search(nt)
                if em:
                    ev     = float(em.group(1))
                    effort = int(ev) if ev == int(ev) else ev
                else:
                    effort = 0
                    for fbi in range(bi + 2, min(bi + 8, len(blocks))):
                        fs, fl = blocks[fbi]
                        if fs.lower() == ns.lower():
                            em = effort_re.search(" ".join(fl))
                            if em:
                                ev     = float(em.group(1))
                                effort = int(ev) if ev == int(ev) else ev
                                break

            for tid in all_ids:
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    tasks.append({
                        "task_id":     tid,
                        "assignee":    assignee,
                        "effort":      effort,
                        "summary":     None,
                        "description": None,
                        "tags":        [],
                    })

        return {"tasks": tasks, "leave_info": leaves}

    def _make_description(self, summary: str) -> str:
        """Generate a clean one-sentence description from a task summary."""
        s = summary.strip()
        w = s.lower()

        # verb-prefix rules — most common Agile task verbs
        patterns = [
            (r"^set[\s-]?up\b",          lambda: f"Set up {s[s.index(' ')+1:].strip()} for the project."),
            (r"^add\b",                   lambda: f"Add {s[4:].strip()} to the system."),
            (r"^implement\b",             lambda: f"Implement {s[10:].strip()} for the platform."),
            (r"^create\b",                lambda: f"Create {s[7:].strip()} for the project."),
            (r"^prepare\b",               lambda: f"Prepare {s[8:].strip()} as required."),
            (r"^improve\b",               lambda: f"Improve {s[8:].strip()} for better performance."),
            (r"^refactor\b",              lambda: f"Refactor {s[8:].strip()} for improved maintainability."),
            (r"^deploy\b|^deployment\b",  lambda: f"Deploy the application: {s.lower()}."),
            (r"^define\b",                lambda: f"Define {s[7:].strip()} clearly and comprehensively."),
            (r"^design\b",                lambda: f"Design {s[7:].strip()} with scalability in mind."),
            (r"^prioriti[sz]e\b",         lambda: f"Prioritise {s[11:].strip()} for the sprint."),
            (r"^backlog\b",               lambda: f"Conduct {s.lower()} for the sprint."),
            (r"^stag\b",                  lambda: f"Execute staging step: {s.lower()}."),
            (r"^high.level\b",            lambda: f"Design and document the {s.lower()}."),
            (r"^requirement\b",           lambda: f"Conduct {s.lower()} to gather system requirements."),
            (r"^oauth",                   lambda: f"Implement {s} across supported identity providers."),
            (r"^ci/cd|^cicd\b",           lambda: f"Modernise the CI/CD pipeline: {s.lower()}."),
            (r"^security\b",              lambda: f"Run security scan and remediate findings: {s.lower()}."),
        ]
        for pattern, gen in patterns:
            if re.match(pattern, w):
                try:
                    return gen()
                except Exception:
                    break

        return f"{s}."

    # ─────────────────────────────────────────────────────────────────────────
    # 2. OLLAMA CALLER (llama3.2:1b local model)
    # ─────────────────────────────────────────────────────────────────────────
    async def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        logger.info(
            f"[Ollama] -> {self.ollama_chat_url} | model={self.local_model}"
        )
        payload = {
            "model":   self.local_model,
            "messages": [
                {
                    "role":    "system",
                    "content": (
                        "You are a precise meeting-transcript analyst. "
                        "Output ONLY a single valid JSON object — no prose, "
                        "no markdown fences, no extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream":  False,
            "format":  "json",
            "options": OLLAMA_OPTIONS,
        }
        timeout = aiohttp.ClientTimeout(
            connect=OLLAMA_CONNECT_TIMEOUT,
            total=OLLAMA_READ_TIMEOUT,
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.ollama_chat_url, json=payload, timeout=timeout
                ) as response:
                    if response.status != 200:
                        body = await response.text()
                        logger.error(f"[Ollama] HTTP {response.status}: {body[:300]}")
                        return None

                    raw     = await response.json()
                    content = raw.get("message", {}).get("content", "").strip()
                    total_s = raw.get("total_duration", 0) / 1e9
                    tokens  = raw.get("eval_count", "?")
                    logger.info(
                        f"[Ollama] Done | tokens={tokens} | "
                        f"time={total_s:.1f}s | len={len(content)}"
                    )

                    if not content:
                        logger.warning("[Ollama] Empty content in response.")
                        return None

                    parsed = self._parse_json_response(content)
                    if parsed.get("tasks") or parsed.get("leave_info"):
                        logger.info(
                            f"[Ollama] Extracted {len(parsed.get('tasks', []))} tasks, "
                            f"{len(parsed.get('leave_info', []))} leaves."
                        )
                        return parsed

                    logger.warning(f"[Ollama] Returned empty collections. Raw output: {content[:500]}")
                    return None

        except asyncio.TimeoutError:
            logger.error(
                f"[Ollama] Timed out after {OLLAMA_READ_TIMEOUT}s. "
                f"Pull model: `ollama pull {self.local_model}`"
            )
        except aiohttp.ClientConnectorError:
            logger.error(
                f"[Ollama] Cannot connect to {self.ollama_chat_url}. "
                "Start with: `ollama serve`"
            )
        except Exception as exc:
            logger.error(f"[Ollama] Error: {type(exc).__name__}: {exc}", exc_info=True)

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # 3. OPENAI CALLER (cloud fallback)
    # ─────────────────────────────────────────────────────────────────────────
    async def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        logger.info(f"[OpenAI] -> model={self.openai_model}")
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type":  "application/json",
        }
        body = {
            "model": self.openai_model,
            "messages": [
                {
                    "role":    "system",
                    "content": "You are a meeting analyst. Output ONLY valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature":     0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers, json=body,
                    timeout=aiohttp.ClientTimeout(total=OPENAI_TOTAL_TIMEOUT),
                ) as response:
                    if response.status == 200:
                        result  = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        usage   = result.get("usage", {})
                        logger.info(
                            f"[OpenAI] Done | "
                            f"prompt={usage.get('prompt_tokens', '?')} "
                            f"completion={usage.get('completion_tokens', '?')}"
                        )
                        parsed = self._parse_json_response(content)
                        logger.info(
                            f"[OpenAI] Extracted {len(parsed.get('tasks', []))} tasks, "
                            f"{len(parsed.get('leave_info', []))} leaves."
                        )
                        return parsed

                    err = await response.text()
                    logger.error(f"[OpenAI] HTTP {response.status}: {err[:300]}")

        except asyncio.TimeoutError:
            logger.error(f"[OpenAI] Timed out after {OPENAI_TOTAL_TIMEOUT}s.")
        except Exception as exc:
            logger.error(f"[OpenAI] Error: {type(exc).__name__}: {exc}", exc_info=True)

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # LLM PROMPT — works for any transcript type (structured or free-form)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_llm_prompt(self, transcript: str, category: Optional[str] = None) -> str:
        # Detect any Jira-style task ID: one-or-more uppercase letters + dash + digits
        # e.g. TAM-198, SA-1212, PROJ-42, BACKEND-5
        has_task_ids = bool(re.search(r"\b[A-Z]{1,10}-\d+\b", transcript))

        cat_check = (category or "").lower().replace(" ", "_").strip()
        # If it's a generic 'sprint_meeting', check if the transcript mentions 'Planning' in the header
        is_planning_content = "planning" in transcript.lower()[:500]
        is_sprint_review = (cat_check == "sprint_review") or (cat_check == "sprint_meeting" and not is_planning_content)

        if is_sprint_review:
            task_rules = (
                "MEETING TYPE: SPRINT REVIEW\n"
                "In this meeting, developers present their work on specific tasks (by ID). The team discusses if the task is finished.\n\n"
                "YOUR MISSION:\n"
                "1. Find EVERY task ID mentioned (format: TAM-XXX, PROJ-XXX, etc).\n"
                "2. For each task, extract: \n"
                "   - task_id: The ID found in the text.\n"
                "   - summary: A short title for the task.\n"
                "   - assignee: The developer who worked on/is presenting the task.\n"
                "   - meeting_status: Crucial! Categorize as 'Completed', 'Partially Complete', 'Incomplete', or 'Moved to Next Sprint' based on the conversation.\n"
                "   - description: 1 sentence describing what was done or why it's not finished.\n"
                "   - effort: Always 0. Do NOT track or invent time/effort hours for Sprint Reviews.\n"
                "3. ACCURACY RULE: Only extract task IDs and information that are EXPLICITLY confirmed in the transcript. DO NOT invent IDs. DO NOT guess effort.\n"
                "4. Only extract task assignments and 'bugs'. Leave info is NOT needed for this meeting type.\n"
                "5. Output format: A single JSON object with 'tasks' and 'bugs' arrays.\n\n"
            )
        elif has_task_ids:
            task_rules = (
                "HOW ASSIGNMENTS WORK IN THIS TRANSCRIPT:\n"
                "- One person ASKS another: 'can you handle XYZ-123?'\n"
                "- The other person ACCEPTS: 'Yes, I can'\n"
                "- Then they give effort: 'Around 16 hours' or '6 story points'\n"
                "- The ASSIGNEE is the person who ACCEPTS (says yes), NOT the person asking.\n\n"
                "TASK RULES:\n"
                "1. Find EVERY task ID (format: LETTERS-NUMBER, e.g. TAM-198, SA-12, PROJ-5).\n"
                "2. For each task ID, assignee = person who agreed to do it.\n"
                "3. effort = number only (hours or story points as stated, 0 if not mentioned).\n"
                "4. Do NOT skip any task ID. Do NOT invent task IDs.\n\n"
                "EXAMPLE (do NOT copy these names into your output — use real people from the transcript):\n"
                "  [10:08] manager@company.com\n"
                "  developer@company.com, can you handle PROJ-10?\n"
                "  [10:08] developer@company.com\n"
                "  Yes, I can. Around 16 hours.\n"
                "  → task_id=PROJ-10, assignee=developer@company.com, effort=16\n\n"
            )
        else:
            task_rules = (
                "HOW ASSIGNMENTS WORK IN THIS TRANSCRIPT:\n"
                "- Tasks are described in natural language (no task IDs).\n"
                "- Find every work item, feature, bug, or task someone is assigned to.\n"
                "- Generate sequential task IDs: TASK-1, TASK-2, TASK-3, etc.\n\n"
                "TASK RULES:\n"
                "1. Extract EVERY task, work item, or assignment mentioned.\n"
                "2. assignee = the person assigned to do it (name or email).\n"
                "3. effort = number only (hours or days stated, 0 if not mentioned).\n"
                "4. Generate sequential task_ids: TASK-1, TASK-2, ...\n\n"
                "EXAMPLE:\n"
                "  'John will handle the login page, about 2 days'\n"
                "  → task_id=TASK-1, assignee=John, effort=2\n\n"
            )

        if is_sprint_review:
            # Sprint review doesn't need leave info, but needs bug extraction
            extra_rules = (
                "BUG RULES:\n"
                "- Find any bugs, issues, or defects mentioned that were DISCOVERED during the review.\n"
                "- title: Short name of the bug.\n"
                "- reporter: Who found it or is speaking about it.\n"
                "- severity: 'High', 'Medium', or 'Low' (guess based on tone if not stated).\n"
                "- description: 1 sentence about the bug behavior.\n\n"
            )
            output_format = (
                "OUTPUT FORMAT (JSON only, no markdown, no explanation):\n"
                '{"tasks":[{"task_id":"PROJ-1","summary":"...","description":"...","assignee":"real_person@domain.com","effort":0,"meeting_status":"Completed"}],'
                '"bugs":[{"title":"...","reporter":"...","severity":"Medium","description":"..."}]}\n\n'
                "DO NOT include 'leave_info' in the output.\n\n"
            )
        else:
            extra_rules = (
                "LEAVE RULES:\n"
                "- Extract every mention of leave, absence, day off, or holiday.\n"
                "- developer_name: EXACTLY the email or name of the speaker who said they are on leave.\n"
                "  DO NOT use example names. Use only real names/emails from the transcript.\n"
                "- leave_date: format YYYY-MM-DD.\n"
                "  If a date RANGE is given (e.g. March 10 to March 13), create ONE entry PER DAY.\n"
                "  If a SINGLE date is given (e.g. March 11), create exactly ONE entry for that day.\n"
                "- leave_hours: 8 for full day (default). Use 4 only if 'half day' is explicitly stated.\n"
                "- leave_type: 'Full Day' (default). Use 'Half Day' only if explicitly stated.\n"
                "- reason: 'On leave'.\n\n"
                "IMPORTANT: Do NOT copy any names or dates from the examples below into your answer.\n"
                "  Only extract leave information that actually appears in the TRANSCRIPT section.\n\n"
            )
            output_format = (
                "OUTPUT FORMAT (JSON only, no markdown, no explanation):\n"
                '{"tasks":[{"task_id":"PROJ-1","summary":"...","description":"...","assignee":"real_person@domain.com","effort":8}],'
                '"leave_info":['
                '{"developer_name":"real_person@domain.com","leave_date":"2026-03-10","leave_hours":8,"leave_type":"Full Day","reason":"On leave"},'
                '{"developer_name":"real_person@domain.com","leave_date":"2026-03-11","leave_hours":8,"leave_type":"Full Day","reason":"On leave"}'
                "]}\n\n"
                "REMINDER: If a range like 'March 10 to 11' is mentioned, you MUST output TWO separate entries in the 'leave_info' array.\n\n"
            )

        role = "sprint review" if is_sprint_review else "sprint planning"
        return (
            f"You are an Agile {role} assistant. "
            f"Extract ALL task assignments AND {'bug' if is_sprint_review else 'leave'} information from the meeting transcript below.\n\n"
            + task_rules
            + extra_rules
            + output_format
            + f"TRANSCRIPT:\n{transcript}\n\n"
            "Now output the JSON:"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC — emotion / sentiment analysis of a transcript
    # ─────────────────────────────────────────────────────────────────────────
    async def analyze_emotion(self, transcript_content: str) -> Dict[str, Any]:
        """
        Analyse the emotional tone and team sentiment from a meeting transcript.
        Returns overall sentiment, energy level, key emotions, and per-speaker notes.
        Uses Ollama first, falls back to OpenAI if needed.
        """
        empty = {
            "overall_sentiment": "neutral",
            "overall_score": 0.5,
            "energy_level": "medium",
            "key_emotions": [],
            "speaker_sentiments": [],
            "summary": "Emotion analysis could not be completed.",
        }
        tc = (transcript_content or "").strip()
        if not tc:
            return empty

        # Truncate very large transcripts to keep prompt manageable
        preview = tc[:6000] if len(tc) > 6000 else tc

        prompt = (
            "You are an expert meeting analyst specialised in team dynamics and emotional intelligence.\n"
            "Analyse the following meeting transcript and return ONLY a valid JSON object.\n\n"
            "Required JSON schema:\n"
            "{\n"
            '  "overall_sentiment": "<positive|neutral|negative>",\n'
            '  "overall_score": <float 0.0 to 1.0, where 1.0 = very positive>,\n'
            '  "energy_level": "<high|medium|low>",\n'
            '  "key_emotions": ["<emotion1>", "<emotion2>", ...],\n'
            '  "speaker_sentiments": [\n'
            '    {"speaker": "<name>", "sentiment": "<positive|neutral|negative>", "notes": "<brief observation>"}\n'
            "  ],\n"
            '  "summary": "<2-3 sentence overall emotional summary of the meeting>"\n'
            "}\n\n"
            "Rules:\n"
            "- Be concise and factual based on the transcript only.\n"
            "- key_emotions should list 2-5 dominant emotions observed (e.g. enthusiasm, frustration, focus, anxiety, confidence).\n"
            "- speaker_sentiments: include only speakers who are clearly identifiable.\n"
            "- Return ONLY the JSON — no extra text, no markdown fences.\n\n"
            f"TRANSCRIPT:\n{preview}"
        )

        logger.info(f"[EmotionAnalysis] Starting | len={len(tc)} chars")
        result = await self._call_ollama(prompt)
        if result and isinstance(result, dict) and "overall_sentiment" in result:
            logger.info(f"[EmotionAnalysis] ✓ Ollama | sentiment={result.get('overall_sentiment')}")
            return {**empty, **result}

        logger.warning("[EmotionAnalysis] Ollama failed — trying OpenAI fallback")
        openai_ok = (
            self.openai_api_key
            and "your-openai-key" not in self.openai_api_key
            and self.openai_api_key != "sk-your-openai-key-here"
        )
        if openai_ok:
            result = await self._call_openai(prompt)
            if result and isinstance(result, dict) and "overall_sentiment" in result:
                logger.info(f"[EmotionAnalysis] ✓ OpenAI | sentiment={result.get('overall_sentiment')}")
                return {**empty, **result}

        logger.error("[EmotionAnalysis] All methods failed — returning empty result")
        return empty

    # ─────────────────────────────────────────────────────────────────────────
    # JSON PARSER — 3-layer fallback for LLM responses
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        logger.debug(f"[Parser] Preview: {content[:300]}")

        def _try(text: str) -> Optional[Dict]:
            try:
                return json.loads(text)
            except Exception:
                return None

        cleaned = content.strip()

        # Layer 1: strip markdown code fences, then parse
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence:
            r = _try(fence.group(1))
            if r is not None:
                return r

        # Layer 2: extract outermost { ... } block
        f, l = cleaned.find("{"), cleaned.rfind("}")
        if f != -1 and l != -1:
            candidate = "".join(
                c for c in cleaned[f : l + 1]
                if c.isprintable() or c in "\n\r\t"
            )
            r = _try(candidate)
            if r is not None:
                return r

        # Layer 3: greedy regex last resort
        gm = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if gm:
            r = _try(gm.group())
            if r is not None:
                return r

        logger.error(f"[Parser] All parse attempts failed.\n{content[:600]}")
        return {"tasks": [], "leave_info": []}


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
