# AI/ML Module

## Overview
AI and Machine Learning components for intelligent automation and analytics.

## Structure

```
ai/
├── nlp/                          # Natural Language Processing
│   ├── transcript_processor.py  # Audio/text transcription
│   ├── blocker_detector.py      # Blocker detection
│   ├── sentiment_analyzer.py    # Sentiment analysis
│   ├── summarizer.py            # Text summarization
│   └── README.md
├── ml/                           # Machine Learning
│   ├── task_predictor.py        # Task estimation
│   ├── risk_analyzer.py         # Risk prediction
│   ├── capacity_planner.py      # Capacity forecasting
│   ├── anomaly_detector.py      # Anomaly detection
│   └── README.md
├── models/                       # Trained ML models
│   └── .gitkeep
└── __init__.py
```

## NLP Components

### 1. Transcript Processor
- Converts audio to text using Whisper/speech APIs
- Extracts key topics and entities
- Identifies speakers
- Timestamps important moments

```python
from app.ai.nlp import TranscriptProcessor

processor = TranscriptProcessor()
result = await processor.process_audio(audio_file)
# Returns: transcript, speakers, topics, timestamps
```

### 2. Blocker Detector
- Uses NLP to identify blockers from text
- Classifies blocker severity
- Extracts affected tasks
- Suggests resolutions

```python
from app.ai.nlp import BlockerDetector

detector = BlockerDetector()
blockers = detector.detect_blockers(transcript)
# Returns: List[Blocker] with severity and context
```

### 3. Sentiment Analyzer
- Analyzes team sentiment from text
- Tracks sentiment trends
- Identifies concerns
- Measures team morale

```python
from app.ai.nlp import SentimentAnalyzer

analyzer = SentimentAnalyzer()
sentiment = analyzer.analyze(feedback_text)
# Returns: score (-1 to 1), emotion labels
```

### 4. Summarizer
- Generates concise summaries
- Creates release notes
- Extracts action items
- Highlights key points

## ML Components

### 1. Task Predictor
- Predicts task effort
- Estimates story points
- Suggests assignees
- Forecasts completion time

```python
from app.ai.ml import TaskPredictor

predictor = TaskPredictor()
prediction = predictor.predict_effort(task_description)
# Returns: estimated_hours, story_points, confidence
```

### 2. Risk Analyzer
- Identifies project risks
- Calculates probability and impact
- Suggests mitigation strategies
- Tracks risk evolution

```python
from app.ai.ml import RiskAnalyzer

analyzer = RiskAnalyzer()
risks = analyzer.analyze_project(project_data)
# Returns: List[Risk] with recommendations
```

### 3. Capacity Planner
- Forecasts team capacity
- Balances workload
- Considers historical velocity
- Optimizes assignments

```python
from app.ai.ml import CapacityPlanner

planner = CapacityPlanner()
plan = planner.plan_sprint(team_data, sprint_goals)
# Returns: recommended_capacity, assignments
```

### 4. Anomaly Detector
- Detects unusual patterns
- Identifies bottlenecks
- Predicts delays
- Alerts stakeholders

## AI Integration

### OpenAI Integration
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
```

### spaCy NLP
```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp(text)

# Extract entities
entities = [(ent.text, ent.label_) for ent in doc.ents]
```

## Model Training

```bash
# Train custom model
python -m app.ai.ml.train \
    --model task_predictor \
    --data data/training_data.csv \
    --output app/ai/models/

# Evaluate model
python -m app.ai.ml.evaluate \
    --model app/ai/models/task_predictor.pkl \
    --test-data data/test_data.csv
```

## Performance Optimization

1. **Model Caching** - Cache loaded models in memory
2. **Batch Processing** - Process multiple items together
3. **Async Operations** - Non-blocking AI calls
4. **GPU Acceleration** - Use GPU for inference if available
5. **Model Quantization** - Reduce model size

## Best Practices

1. **Version models** - Track model versions
2. **Monitor accuracy** - Track prediction quality
3. **Handle failures** - Graceful degradation
4. **Log predictions** - For debugging and improvement
5. **A/B testing** - Compare model versions
6. **Feedback loop** - Learn from corrections

---

**Related:** [Services](../services/README.md), [Tasks](../tasks/README.md)
