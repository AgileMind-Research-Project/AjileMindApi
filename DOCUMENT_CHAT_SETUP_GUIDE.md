# Document Chat RAG Feature - Setup Guide

This guide will help you set up and use the new Document Chat feature with RAG (Retrieval-Augmented Generation) architecture.

## 🎯 Overview

The Document Chat feature allows users to:
- Upload PDF documents (e.g., sprint reports, documentation)
- Ask natural language questions about the documents
- Get AI-generated answers with source references
- Maintain chat history

**Architecture**: RAG (Retrieval-Augmented Generation)
- **Vector Database**: ChromaDB (stores document embeddings locally)
- **LLM**: Ollama (runs locally or on remote GPU server)
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)

---

## 📋 Prerequisites

### 1. Install Ollama

**Windows/Mac/Linux**:
```bash
# Visit https://ollama.ai and download installer
# Or use curl (Linux/Mac):
curl -fsSL https://ollama.ai/install.sh | sh
```

**Verify Installation**:
```bash
ollama --version
```

### 2. Pull LLM Model

```bash
# Pull llama2 (7GB model)
ollama pull llama2

# Or use smaller/different models:
# ollama pull mistral
# ollama pull codellama
# ollama pull phi
```

**Start Ollama Server** (if not running):
```bash
ollama serve
```

The server will run at `http://localhost:11434`

---

## 🔧 Backend Setup

### Step 1: Install Python Packages

The packages are already installed, but if needed:

```powershell
pip install chromadb pypdf sentence-transformers ollama langchain langchain-community tiktoken
```

### Step 2: Create Database Tables

Run the SQL migration to add document tables:

```powershell
# If using local MySQL
mysql -u root -p agilemind_db < document_chat_schema.sql

# If using remote MySQL (Railway)
mysql -u root -p -h metro.proxy.rlwy.net -P 58760 agilemind_db < document_chat_schema.sql
```

Or run this SQL manually in MySQL Workbench:

```sql
CREATE TABLE IF NOT EXISTS DOCUMENTS (
    DOCUMENT_ID VARCHAR(50) PRIMARY KEY,
    TENANT_ID VARCHAR(50) NOT NULL,
    USER_ID VARCHAR(50) NOT NULL,
    FILENAME VARCHAR(255) NOT NULL,
    FILE_SIZE INT NOT NULL,
    TOTAL_CHUNKS INT NOT NULL,
    STATUS ENUM('processing', 'ready', 'failed') DEFAULT 'processing',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    INDEX IDX_TENANT (TENANT_ID)
);

CREATE TABLE IF NOT EXISTS CHAT_HISTORY (
    CHAT_ID VARCHAR(50) PRIMARY KEY,
    TENANT_ID VARCHAR(50) NOT NULL,
    USER_ID VARCHAR(50) NOT NULL,
    QUESTION TEXT NOT NULL,
    ANSWER TEXT NOT NULL,
    SOURCES JSON,
    MODEL VARCHAR(50),
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (TENANT_ID) REFERENCES TENANTS(TENANT_ID) ON DELETE CASCADE,
    FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    INDEX IDX_TENANT (TENANT_ID)
);
```

### Step 3: Verify Configuration

Check your `.env` file has these settings:

```env
# LLM Configuration
LLM_API_URL=http://localhost:11434
LLM_MODEL_NAME=llama2
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000

# Vector Database
CHROMA_PERSIST_DIR=./data/chroma_db
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

# Document Processing
MAX_FILE_SIZE_MB=10
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Step 4: Create Data Directory

```powershell
# Create directory for ChromaDB persistence
New-Item -Path ".\data\chroma_db" -ItemType Directory -Force
```

### Step 5: Start Backend

```powershell
python main.py
```

The API will be available at `http://localhost:8000`

---

## 🧪 Testing the API

### 1. Upload a PDF Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

**Response**:
```json
{
  "success": true,
  "message": "Document uploaded and processed successfully",
  "document_id": "doc_abc123",
  "filename": "sprint_report.pdf",
  "total_chunks": 15,
  "total_characters": 12450
}
```

### 2. List Documents

```bash
curl -X GET http://localhost:8000/api/v1/documents/list \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Ask a Question

```bash
curl -X POST http://localhost:8000/api/v1/documents/chat/ask \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the sprint velocity?",
    "top_k": 5
  }'
```

**Response**:
```json
{
  "success": true,
  "question": "What is the sprint velocity?",
  "answer": "Based on the sprint report, the velocity is 45 story points...",
  "sources": [
    {
      "filename": "sprint_report.pdf",
      "chunk_index": 3,
      "relevance_score": 0.89
    }
  ],
  "model": "llama2",
  "has_context": true,
  "response_time_ms": 1245.5
}
```

### 4. Get Chat History

```bash
curl -X GET http://localhost:8000/api/v1/documents/chat/history?limit=50 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Delete a Document

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/doc_abc123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Health Check

```bash
curl -X GET http://localhost:8000/api/v1/documents/health \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🌐 Frontend Integration

See `DOCUMENT_CHAT_FRONTEND_GUIDE.md` for complete React integration guide.

**Quick Start**:

```typescript
// Upload document
const formData = new FormData();
formData.append('file', pdfFile);
await axios.post('/api/v1/documents/upload', formData, {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Ask question
const response = await axios.post('/api/v1/documents/chat/ask', {
  question: 'What is the sprint velocity?',
  top_k: 5
}, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 🔄 Production Deployment (Remote LLM)

### Option 1: Use Remote GPU Server

Update `.env`:
```env
# Change from local to remote LLM server
LLM_API_URL=https://your-gpu-server.com:11434
```

**Setup Remote Ollama**:
```bash
# On GPU server
ollama serve --host 0.0.0.0:11434

# Allow external connections
export OLLAMA_HOST=0.0.0.0:11434
```

### Option 2: Use Cloud LLM Services

Modify `app/services/llm_service.py` to integrate with:
- OpenAI API
- Anthropic Claude API
- Hugging Face Inference API
- AWS Bedrock
- Azure OpenAI

Example for OpenAI:
```python
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": full_prompt}]
)
```

---

## 📊 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload PDF document |
| GET | `/api/v1/documents/list` | List all documents |
| DELETE | `/api/v1/documents/{id}` | Delete document |
| POST | `/api/v1/documents/chat/ask` | Ask question (RAG) |
| GET | `/api/v1/documents/chat/history` | Get chat history |
| GET | `/api/v1/documents/health` | System health check |

**Authentication**: All endpoints require JWT Bearer token

---

## 🛠️ Troubleshooting

### Issue: "No module named 'chromadb'"
```powershell
pip install chromadb
```

### Issue: "Ollama connection refused"
```powershell
# Start Ollama server
ollama serve
```

### Issue: "Model not found"
```powershell
# Pull the model
ollama pull llama2
```

### Issue: "ChromaDB permission denied"
```powershell
# Check directory permissions
icacls .\data\chroma_db
```

### Issue: "Slow LLM responses"
- Use a smaller model: `ollama pull phi` (2GB)
- Reduce `LLM_MAX_TOKENS` in `.env`
- Consider GPU acceleration
- Use remote GPU server

### Issue: "PDF extraction fails"
- Ensure PDF has extractable text (not scanned images)
- Use OCR for scanned PDFs (requires additional setup)
- Check file size < 10MB

---

## 📈 Performance Optimization

### 1. Use Faster Embedding Model
```env
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2  # Fast (default)
# or
EMBEDDING_MODEL_NAME=paraphrase-MiniLM-L3-v2  # Faster, less accurate
```

### 2. Adjust Chunk Settings
```env
CHUNK_SIZE=500  # Smaller chunks = faster search, less context
CHUNK_OVERLAP=100  # Less overlap = fewer chunks
```

### 3. Limit Context Chunks
```python
# In chat query
{
  "question": "...",
  "top_k": 3  # Retrieve fewer chunks
}
```

### 4. Use GPU for Ollama
```bash
# Ollama automatically uses GPU if available
nvidia-smi  # Check GPU availability
```

---

## 🔐 Security Considerations

1. **File Upload**: 
   - Max size enforced (10MB)
   - PDF validation
   - Malware scanning (add ClamAV integration)

2. **Multi-tenant Isolation**:
   - Documents isolated by `tenant_id`
   - Vector DB collections per tenant
   - JWT authentication required

3. **Rate Limiting**:
   - Consider adding rate limits for uploads
   - Throttle expensive LLM queries

4. **Data Privacy**:
   - Documents stored locally in ChromaDB
   - No data sent to external services (if using local Ollama)
   - GDPR compliant with proper deletion

---

## 🎓 How RAG Works

1. **Upload Phase**:
   ```
   PDF → Extract Text → Split into Chunks → Generate Embeddings → Store in Vector DB
   ```

2. **Query Phase**:
   ```
   User Question → Generate Embedding → Search Vector DB → 
   Retrieve Top K Chunks → Pass to LLM with Context → Generate Answer
   ```

3. **Vector Similarity**:
   - Uses cosine similarity between embeddings
   - Higher score = more relevant chunk

---

## 📚 Additional Resources

- **Ollama Documentation**: https://ollama.ai/docs
- **ChromaDB Documentation**: https://docs.trychroma.com
- **Sentence Transformers**: https://www.sbert.net
- **LangChain**: https://python.langchain.com

---

## ✅ Quick Verification Checklist

- [ ] Ollama installed and running
- [ ] LLM model pulled (`ollama list`)
- [ ] Python packages installed
- [ ] Database tables created
- [ ] `.env` configured
- [ ] ChromaDB directory created
- [ ] Backend started successfully
- [ ] Can upload PDF
- [ ] Can ask questions
- [ ] Frontend integrated (if applicable)

---

## 🎉 You're Ready!

The Document Chat feature is now fully integrated into your AgileMind platform. Users can upload sprint reports, documentation, and other PDFs, then ask questions to get AI-powered insights!

**Next Steps**:
1. Test with sample PDF documents
2. Integrate frontend React component
3. Customize prompts in `llm_service.py`
4. Add additional document types (Word, Excel)
5. Implement document sharing between users
6. Add real-time streaming responses
