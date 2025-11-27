# Document Chat Frontend - React Component Guide

This guide explains how to integrate the document chat feature into your React frontend.

## Overview

The document chat feature allows users to:
1. Upload PDF files
2. Ask questions about uploaded documents
3. Get AI-generated answers with source references
4. View chat history

## API Endpoints

Base URL: `http://localhost:8000/api/v1/documents`

All endpoints require JWT authentication (`Authorization: Bearer <token>`)

### 1. Upload Document
```
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Body: { file: <PDF file> }
```

### 2. List Documents
```
GET /api/v1/documents/list
```

### 3. Delete Document
```
DELETE /api/v1/documents/{document_id}
```

### 4. Ask Question (RAG)
```
POST /api/v1/documents/chat/ask
Content-Type: application/json

Body: {
  "question": "What is the sprint velocity?",
  "document_ids": ["doc_123", "doc_456"],  // optional
  "top_k": 5  // optional, default: 5
}
```

### 5. Get Chat History
```
GET /api/v1/documents/chat/history?limit=50
```

### 6. Health Check
```
GET /api/v1/documents/health
```

## React Component Example

### DocumentChatPage.tsx

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1/documents';

interface Document {
  document_id: string;
  filename: string;
  file_size: number;
  total_chunks: number;
  uploaded_by: string;
  uploaded_at: string;
  status: string;
}

interface ChatMessage {
  question: string;
  answer: string;
  sources: Array<{
    filename: string;
    chunk_index: number;
    relevance_score: number;
  }>;
}

const DocumentChatPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Get JWT token from your auth context/storage
  const token = localStorage.getItem('access_token');
  
  const axiosConfig = {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  };

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE}/list`, axiosConfig);
      setDocuments(response.data.documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are supported');
      return;
    }

    setUploading(true);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API_BASE}/upload`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      alert('Document uploaded successfully!');
      loadDocuments(); // Reload list
      event.target.value = ''; // Reset input
    } catch (error: any) {
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleAskQuestion = async () => {
    if (!question.trim()) return;
    
    setLoading(true);
    
    try {
      const response = await axios.post(
        `${API_BASE}/chat/ask`,
        { question, top_k: 5 },
        axiosConfig
      );
      
      setChatHistory([
        {
          question: response.data.question,
          answer: response.data.answer,
          sources: response.data.sources
        },
        ...chatHistory
      ]);
      
      setQuestion(''); // Clear input
    } catch (error: any) {
      alert(`Query failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm('Delete this document?')) return;
    
    try {
      await axios.delete(`${API_BASE}/${docId}`, axiosConfig);
      loadDocuments();
    } catch (error) {
      alert('Failed to delete document');
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Document Chat</h1>
      
      {/* Upload Section */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Upload Document</h2>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          disabled={uploading}
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none p-2"
        />
        {uploading && <p className="mt-2 text-blue-600">Uploading...</p>}
      </div>

      {/* Documents List */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <h2 className="text-xl font-semibold mb-4">Uploaded Documents</h2>
        <div className="space-y-2">
          {documents.map(doc => (
            <div key={doc.document_id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <div>
                <p className="font-medium">{doc.filename}</p>
                <p className="text-sm text-gray-600">
                  {doc.total_chunks} chunks • {(doc.file_size / 1024).toFixed(1)} KB • {doc.status}
                </p>
              </div>
              <button
                onClick={() => handleDeleteDocument(doc.document_id)}
                className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Section */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">Ask Questions</h2>
        
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion()}
            placeholder="Ask a question about your documents..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            onClick={handleAskQuestion}
            disabled={loading || !question.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>

        {/* Chat History */}
        <div className="space-y-4">
          {chatHistory.map((msg, idx) => (
            <div key={idx} className="border-l-4 border-blue-500 pl-4">
              <p className="font-medium text-gray-800 mb-2">Q: {msg.question}</p>
              <p className="text-gray-700 mb-2">A: {msg.answer}</p>
              {msg.sources.length > 0 && (
                <div className="text-sm text-gray-600">
                  <p className="font-medium">Sources:</p>
                  <ul className="list-disc list-inside">
                    {msg.sources.map((src, i) => (
                      <li key={i}>
                        {src.filename} (chunk {src.chunk_index}) - {(src.relevance_score * 100).toFixed(1)}% relevant
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DocumentChatPage;
```

## Integration Steps

### 1. Install Dependencies
```bash
npm install axios
```

### 2. Add Route to Your App
```typescript
// In your routing file (e.g., App.tsx)
import DocumentChatPage from './pages/DocumentChatPage';

// Add to your routes
<Route path="/documents/chat" element={<DocumentChatPage />} />
```

### 3. Add Navigation Link
```tsx
<nav>
  <Link to="/documents/chat">Document Chat</Link>
</nav>
```

## API Service Layer (Optional)

For better organization, create an API service:

```typescript
// services/documentService.ts
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1/documents';

const getAuthConfig = () => ({
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

export const documentService = {
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/upload`, formData, {
      ...getAuthConfig(),
      headers: {
        ...getAuthConfig().headers,
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  listDocuments: async () => {
    return axios.get(`${API_BASE}/list`, getAuthConfig());
  },

  deleteDocument: async (docId: string) => {
    return axios.delete(`${API_BASE}/${docId}`, getAuthConfig());
  },

  askQuestion: async (question: string, documentIds?: string[], topK?: number) => {
    return axios.post(`${API_BASE}/chat/ask`, {
      question,
      document_ids: documentIds,
      top_k: topK
    }, getAuthConfig());
  },

  getChatHistory: async (limit: number = 50) => {
    return axios.get(`${API_BASE}/chat/history?limit=${limit}`, getAuthConfig());
  },

  checkHealth: async () => {
    return axios.get(`${API_BASE}/health`, getAuthConfig());
  }
};
```

## Environment Variables

Add to your `.env.local`:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_LLM_ENABLED=true
```

## Notes

1. **Authentication**: All endpoints require JWT token
2. **File Size**: Default max 10MB per PDF
3. **Supported Format**: PDF only
4. **Multi-tenant**: Documents are isolated by tenant
5. **Real-time Updates**: Consider adding WebSocket support for upload progress

## Troubleshooting

### CORS Issues
Make sure your backend `.env` has:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3008
```

### File Upload Fails
- Check file size limit (default 10MB)
- Ensure file is PDF format
- Verify JWT token is valid

### LLM Not Responding
- Ensure Ollama is running: `ollama serve`
- Check model is pulled: `ollama pull llama2`
- Verify `LLM_API_URL` in backend `.env`
