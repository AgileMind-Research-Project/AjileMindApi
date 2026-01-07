# LLM and Chatbot Setup Guide

Complete guide to set up and use the RAG-based Document Chatbot with LLM integration.

## Table of Contents
1. [Quick Setup](#quick-setup)
2. [LLM Providers](#llm-providers)
3. [Configuration](#configuration)
4. [Architecture](#architecture)
5. [API Usage](#api-usage)
6. [Features](#features)
7. [Troubleshooting](#troubleshooting)

---

## Quick Setup

### 1. Install Dependencies

All required packages are already in `requirements.txt`:
```bash
cd AjileMindApi
pip install -r requirements.txt
```

Key packages:
- `langchain` - LLM framework
- `langchain-openai` - OpenAI integration
- `openai` - OpenAI Python client

### 2. Get an API Key

#### For OpenAI (Recommended)
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

### 3. Configure Environment

Update `.env` file:
```dotenv
# LLM Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7
LLM_PROVIDER=openai
USE_RAG_WITH_LLM=true

# RAG Configuration
RAG_CHUNK_SIZE=1000
RAG_OVERLAP=100
RAG_TOP_K_RESULTS=5
```

### 4. Start the Server

```bash
python main.py
```

You should see:
```
INFO: OpenAI RAG Service initialized with model: gpt-4
```

### 5. Test the Chatbot

Use the frontend or API to:
1. Upload or select a document
2. Ask questions about the document
3. Get AI-generated answers based on document content

---

## LLM Providers

### OpenAI (Recommended)

**Pros:**
- Most capable models (GPT-4, GPT-3.5-turbo)
- Best for complex reasoning
- Good context understanding

**Setup:**
```dotenv
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4
LLM_PROVIDER=openai
```

**Models Available:**
- `gpt-4` - Most capable, higher cost
- `gpt-4-turbo` - Better performance/cost ratio
- `gpt-3.5-turbo` - Fastest, lowest cost

**Pricing:**
- GPT-4: $0.03-0.06 per 1K tokens
- GPT-3.5-turbo: $0.0005-0.0015 per 1K tokens

### Anthropic Claude (Optional)

**Pros:**
- Excellent for document analysis
- Large context window (100K tokens)
- Good reasoning

**Setup:**
```bash
# Install additional package
pip install langchain-anthropic

# Configure .env
ANTHROPIC_API_KEY=your-key
LLM_PROVIDER=anthropic
```

### Google Gemini (Optional)

**Pros:**
- Free tier available
- Good for general queries
- Fast responses

**Setup:**
```bash
# Install additional package
pip install langchain-google-genai

# Configure .env
GOOGLE_API_KEY=your-key
LLM_PROVIDER=gemini
```

---

## Configuration

### Environment Variables

```dotenv
# Core LLM Settings
OPENAI_API_KEY=                    # Your OpenAI API key
OPENAI_MODEL=gpt-4                # Model to use
OPENAI_MAX_TOKENS=2000            # Max response length
OPENAI_TEMPERATURE=0.7            # Creativity level (0-1)
LLM_PROVIDER=openai               # Which provider to use
USE_RAG_WITH_LLM=true            # Enable RAG functionality

# RAG Settings
RAG_CHUNK_SIZE=1000              # Document chunk size
RAG_OVERLAP=100                  # Chunk overlap for context
RAG_TOP_K_RESULTS=5              # Number of relevant chunks to use
```

### Key Settings Explained

**OPENAI_TEMPERATURE** (0.0 - 2.0)
- 0.0 = Deterministic, factual (recommended for RAG)
- 0.7 = Balanced (default)
- 1.5+ = Creative, varied responses

**RAG_CHUNK_SIZE** (100 - 2000)
- Smaller (500) = More granular, faster retrieval
- Larger (2000) = More context, longer processing
- Recommended: 1000

**RAG_TOP_K_RESULTS** (1 - 10)
- Number of document chunks to include as context
- 3-5 recommended for balance

---

## Architecture

### System Architecture

```
User Query
    ↓
RAG Service
    ↓
├─→ Document Chunking
│   └─→ Split large documents into manageable chunks
│
├─→ Relevance Retrieval
│   └─→ Find most relevant chunks for the query
│
└─→ LLM Processing
    ├─→ Prepare context-aware prompt
    ├─→ Send to OpenAI/Claude/Gemini
    └─→ Return formatted response
```

### Component Breakdown

#### 1. **Document Service** (`document_service.py`)
- Manages document storage and retrieval
- Handles document metadata (title, date, category)
- Provides document content for RAG

#### 2. **RAG Service** (`rag_service.py`)
- **Base Class**: `RAGServiceBase`
  - Document chunking
  - Relevance scoring
  - Context retrieval

- **Simple RAG**: `SimpleRAGService`
  - No LLM required
  - Keyword matching and templates
  - Fallback option

- **OpenAI RAG**: `RAGServiceWithOpenAI`
  - Full LLM integration
  - Natural language understanding
  - Production-ready

#### 3. **LLM Utilities** (`llm_utils.py`)
- `LLMFactory`: Create LLM instances
- `PromptTemplates`: Predefined prompts
- `LLMResponseFormatter`: Format responses
- `TokenCounter`: Count and truncate tokens

#### 4. **Documents API** (`documents.py`)
- `/documents/` - List all documents
- `/documents/{id}` - Get specific document
- `/documents/dates` - Get unique upload dates
- `/documents?date=X` - Filter by date
- `/documents/chat` - RAG chatbot endpoint
- `/documents/upload` - Upload new documents

---

## API Usage

### 1. Upload a Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "doc_title=My Document" \
  -F "category=research"
```

**Response:**
```json
{
  "id": 1,
  "doc_title": "My Document",
  "uploaded_date": "2024-12-24",
  "category": "research",
  "doc_content": "..."
}
```

### 2. Get Available Document Dates

```bash
curl -X GET http://localhost:8000/api/v1/documents/dates \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "uploaded_date": "2024-12-24",
    "count": 5
  },
  {
    "uploaded_date": "2024-12-23",
    "count": 3
  }
]
```

### 3. Get Documents by Date

```bash
curl -X GET "http://localhost:8000/api/v1/documents?date=2024-12-24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
[
  {
    "id": 1,
    "doc_title": "Document 1",
    "uploaded_date": "2024-12-24",
    "category": "research"
  }
]
```

### 4. Chat with Document (Core Feature)

```bash
curl -X POST http://localhost:8000/api/v1/documents/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "query": "What are the main points discussed?"
  }'
```

**Request Schema:**
```json
{
  "document_id": 1,
  "query": "Your question here"
}
```

**Response:**
```json
{
  "document_id": 1,
  "document_title": "My Document",
  "user_query": "What are the main points discussed?",
  "chatbot_response": "Based on the document, the main points are...",
  "timestamp": "2024-12-24T10:30:00"
}
```

### 5. Search Documents

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "search keywords",
    "limit": 10
  }'
```

---

## Features

### ✅ Core Features Implemented

1. **Document Management**
   - Upload PDF, TXT, DOCX files
   - Filter by date and category
   - Full-text search

2. **RAG Chatbot**
   - Intelligent document chunking
   - Relevance-based context retrieval
   - Natural language Q&A

3. **LLM Integration**
   - OpenAI GPT-4/GPT-3.5
   - Automatic fallback to Simple RAG
   - Error handling and logging

4. **Authentication**
   - Token-based auth (JWT)
   - Tenant isolation
   - User context in all requests

5. **Document Processing**
   - Automatic chunk creation
   - Overlap management
   - Configurable parameters

### 🚀 Advanced Features Available

1. **Multiple LLM Providers**
   ```python
   # Easy to add Anthropic, Google, etc.
   LLMFactory.get_llm("anthropic")
   ```

2. **Token Management**
   ```python
   from app.services.llm_utils import TokenCounter
   
   count = TokenCounter.count_tokens(long_text)
   truncated = TokenCounter.truncate_for_model(text, max_tokens=2000)
   ```

3. **Prompt Customization**
   ```python
   from app.services.llm_utils import PromptTemplates
   
   prompt = PromptTemplates.format_rag_prompt(
       document_title="My Doc",
       document_content="...",
       user_query="What is this?"
   )
   ```

---

## Troubleshooting

### Issue: "OpenAI API key not configured"

**Solution:**
1. Check `.env` file has `OPENAI_API_KEY`
2. Key must start with `sk-`
3. Verify key has API access (not exhausted)
4. Run: `echo $OPENAI_API_KEY` to verify

### Issue: 401 Unauthorized on chat endpoint

**Solution:**
1. Ensure token is passed: `Authorization: Bearer YOUR_TOKEN`
2. Token must be valid and not expired
3. User must have access to the document

### Issue: Empty or no response from chatbot

**Solutions:**
1. Document might be too short - add more content
2. Query words don't match document content
3. Check logs: `grep "RAG response" logs/`
4. Try simpler query

### Issue: Slow response times

**Solutions:**
1. Reduce `RAG_CHUNK_SIZE` (process faster)
2. Reduce `RAG_TOP_K_RESULTS` (fewer chunks)
3. Use `gpt-3.5-turbo` (faster than GPT-4)
4. Check network/API rate limits

### Issue: Incomplete answers

**Solution:**
Increase `OPENAI_MAX_TOKENS`:
```dotenv
OPENAI_MAX_TOKENS=4000
```

### Issue: LLM module not found

**Solution:**
```bash
pip install langchain langchain-openai openai
pip install -r requirements.txt --upgrade
```

---

## Performance Tips

### 1. Optimize Document Chunking
```dotenv
# For large documents
RAG_CHUNK_SIZE=1500
RAG_OVERLAP=200
RAG_TOP_K_RESULTS=3
```

### 2. Use Cost-Effective Model
```dotenv
# Instead of:
OPENAI_MODEL=gpt-4

# Use:
OPENAI_MODEL=gpt-3.5-turbo
```

### 3. Batch Operations
- Upload documents during off-peak hours
- Process searches in bulk
- Cache frequent queries

### 4. Monitor Usage
```python
from app.services.llm_utils import TokenCounter

# Check token usage before API calls
tokens = TokenCounter.count_tokens(document_text)
```

---

## Next Steps

1. **Deploy to Production**
   - Use environment-specific configs
   - Set up monitoring and logging
   - Configure rate limiting

2. **Enhance RAG**
   - Add vector embeddings (Pinecone, Weaviate)
   - Implement semantic search
   - Use multi-document context

3. **Optimize Costs**
   - Implement response caching
   - Use cheaper models for simple queries
   - Monitor API usage

4. **Advanced Features**
   - Document summarization
   - Multi-language support
   - Citation tracking

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Enable DEBUG mode in `.env`
3. Review API response errors
4. Check OpenAI account status and quotas
