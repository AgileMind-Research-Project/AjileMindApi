"""
Example: Testing Document Chat API

This script demonstrates how to use the Document Chat API endpoints.
"""

import requests
import json

# Configuration
API_BASE = "http://localhost:8000/api/v1"
USERNAME = "admin@sample.com"
PASSWORD = "Admin123!"

def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": USERNAME, "password": PASSWORD}
    )
    response.raise_for_status()
    return response.json()["data"]["tokens"]["access_token"]

def upload_document(token, file_path):
    """Upload a PDF document"""
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(
            f"{API_BASE}/documents/upload",
            headers=headers,
            files=files
        )
    
    response.raise_for_status()
    return response.json()

def list_documents(token):
    """List all uploaded documents"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/documents/list",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def ask_question(token, question, document_ids=None, top_k=5):
    """Ask a question about documents (RAG)"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "question": question,
        "top_k": top_k
    }
    
    if document_ids:
        payload["document_ids"] = document_ids
    
    response = requests.post(
        f"{API_BASE}/documents/chat/ask",
        headers=headers,
        json=payload
    )
    
    response.raise_for_status()
    return response.json()

def get_chat_history(token, limit=50):
    """Get chat history"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/documents/chat/history",
        headers=headers,
        params={"limit": limit}
    )
    response.raise_for_status()
    return response.json()

def delete_document(token, document_id):
    """Delete a document"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(
        f"{API_BASE}/documents/{document_id}",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

def check_health(token):
    """Check system health"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/documents/health",
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def main():
    """Main test flow"""
    print("=" * 60)
    print("Document Chat API - Example Test")
    print("=" * 60)
    
    try:
        # 1. Login
        print("\n1. Logging in...")
        token = login()
        print("✅ Login successful")
        
        # 2. Check health
        print("\n2. Checking system health...")
        health = check_health(token)
        print(f"✅ Vector DB Status: {health['vector_db_status']}")
        print(f"✅ LLM Status: {health['llm_status']['status']}")
        print(f"✅ Documents: {health['document_stats']['total_documents']}")
        
        # 3. Upload document (replace with your PDF path)
        pdf_path = "./sample_document.pdf"  # Change this!
        
        print(f"\n3. Uploading document: {pdf_path}")
        try:
            upload_result = upload_document(token, pdf_path)
            print(f"✅ Uploaded: {upload_result['filename']}")
            print(f"   Document ID: {upload_result['document_id']}")
            print(f"   Chunks: {upload_result['total_chunks']}")
            document_id = upload_result['document_id']
        except FileNotFoundError:
            print("⚠️  Sample PDF not found. Skipping upload test.")
            print("   Place a PDF file at './sample_document.pdf' to test upload.")
            document_id = None
        
        # 4. List documents
        print("\n4. Listing documents...")
        docs = list_documents(token)
        print(f"✅ Total documents: {docs['total']}")
        for doc in docs['documents'][:3]:  # Show first 3
            print(f"   - {doc['filename']} ({doc['status']}, {doc['total_chunks']} chunks)")
        
        # 5. Ask a question
        print("\n5. Asking a question...")
        question = "What is this document about?"
        
        try:
            answer = ask_question(token, question, top_k=3)
            print(f"✅ Question: {answer['question']}")
            print(f"✅ Answer: {answer['answer'][:200]}...")  # First 200 chars
            print(f"✅ Model: {answer['model']}")
            print(f"✅ Sources: {len(answer['sources'])} references")
            
            if answer['sources']:
                print("\n   Top sources:")
                for src in answer['sources'][:2]:
                    print(f"   - {src['filename']} (chunk {src['chunk_index']}, {src['relevance_score']:.2f} relevance)")
        
        except Exception as e:
            print(f"⚠️  Question failed: {str(e)}")
            print("   Make sure Ollama is running: ollama serve")
            print("   And model is pulled: ollama pull llama2")
        
        # 6. Get chat history
        print("\n6. Getting chat history...")
        history = get_chat_history(token, limit=5)
        print(f"✅ Total chats: {history['total']}")
        if history['chat_history']:
            latest = history['chat_history'][0]
            print(f"   Latest: {latest['question'][:50]}...")
        
        # 7. Optionally delete document
        # Uncomment to test deletion:
        # if document_id:
        #     print(f"\n7. Deleting document: {document_id}")
        #     delete_result = delete_document(token, document_id)
        #     print(f"✅ {delete_result['message']}")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
    
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
