#!/usr/bin/env python
"""
AI Extraction Test Runner
Runs the agent on a sample transcript and generates jira_updates.json
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from app.ai.task_extractor.agent_service import agent_service
from app.core.logger import logger


def load_transcript(filepath: str) -> str:
    """Load transcript from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def save_jira_updates(extractions: list, output_path: str):
    """Save extractions to JSON file."""
    # Convert Pydantic models to dicts
    updates = []
    for ext in extractions:
        update = {
            "ticket_id": ext.ticket_id,
            "status": ext.detected_status.value,
            "blocker": ext.blocker_description,
            "confidence": ext.ai_confidence_score,
            "context": ext.extracted_context,
            "reasoning": ext.ai_reasoning
        }
        updates.append(update)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updates, f, indent=2, ensure_ascii=False)
    
    return updates


def main():
    print("=" * 60)
    print("🤖 AI Extraction Agent - Chain of Thought Analysis")
    print("=" * 60)
    
    # Paths
    transcript_path = project_root / "test_data" / "sample_transcript.txt"
    output_path = project_root / "test_data" / "jira_updates.json"
    
    # Load transcript
    print(f"\n📄 Loading transcript from: {transcript_path}")
    
    if not transcript_path.exists():
        print(f"❌ Error: Transcript file not found: {transcript_path}")
        return 1
    
    transcript = load_transcript(str(transcript_path))
    print(f"   Loaded {len(transcript)} characters")
    
    # Run extraction
    print("\n🧠 Running AI extraction with Chain of Thought reasoning...")
    print("-" * 60)
    
    meeting_id = "TEST-MEETING-001"
    extractions, processing_time, debug_info = agent_service.extract_task_updates(
        transcript=transcript,
        meeting_id=meeting_id
    )
    
    print("-" * 60)
    
    # Display results
    print(f"\n✅ Extraction Complete!")
    print(f"   Processing time: {processing_time:.2f}ms")
    print(f"   Tasks extracted: {len(extractions)}")
    
    if extractions:
        print("\n📋 Extracted Task Updates:")
        print("-" * 60)
        
        for i, ext in enumerate(extractions, 1):
            status_emoji = {
                'DONE': '✅',
                'IN_PROGRESS': '🔄',
                'BLOCKED': '🚫',
                'TODO': '📝'
            }.get(ext.detected_status.value, '❓')
            
            print(f"\n{i}. {status_emoji} {ext.ticket_id}")
            print(f"   Status: {ext.detected_status.value}")
            if ext.blocker_description:
                print(f"   Blocker: {ext.blocker_description}")
            print(f"   Confidence: {ext.ai_confidence_score:.2f}")
            print(f"   Reasoning: {ext.ai_reasoning[:80]}...")
    
    # Save to JSON
    print(f"\n💾 Saving to: {output_path}")
    updates = save_jira_updates(extractions, str(output_path))
    print(f"   Saved {len(updates)} task updates to jira_updates.json")
    
    # Summary table
    print("\n" + "=" * 60)
    print("📊 Summary by Status:")
    status_counts = {}
    for ext in extractions:
        status = ext.detected_status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")
    
    print("=" * 60)
    print("✨ Agent completed successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
