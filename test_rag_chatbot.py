#!/usr/bin/env python
"""
RAG Chatbot Quick Test Script

Test the RAG-based document chatbot without needing frontend.
Run this after starting the API server.
"""

import requests
import json
import sys
from datetime import date

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "testuser"
PASSWORD = "TestPassword@123"

class ChatbotTester:
    """Test helper for RAG chatbot"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        print(f"[{level}] {message}")
    
    def login(self):
        """Authenticate and get token"""
        self.log("Logging in...")
        
        login_data = {
            "username": USERNAME,
            "password": PASSWORD
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.log(f"Login successful. Token: {self.token[:20]}...", "SUCCESS")
                return True
            else:
                self.log(f"Login failed: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Login error: {e}", "ERROR")
            return False
    
    def get_headers(self):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_documents(self):
        """Fetch all documents"""
        self.log("Fetching documents...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/documents",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                documents = response.json()
                self.log(f"Found {len(documents)} documents", "SUCCESS")
                
                for doc in documents[:5]:  # Show first 5
                    print(f"  - ID: {doc['id']}, Title: {doc['doc_title']}, "
                          f"Date: {doc['uploaded_date']}")
                
                return documents
            else:
                self.log(f"Failed to fetch documents: {response.text}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"Error fetching documents: {e}", "ERROR")
            return []
    
    def get_document_dates(self):
        """Fetch available document dates"""
        self.log("Fetching document dates...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/documents/dates",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                dates = response.json()
                self.log(f"Found {len(dates)} unique dates", "SUCCESS")
                
                for item in dates[:5]:  # Show first 5
                    print(f"  - Date: {item['uploaded_date']}, Count: {item['count']}")
                
                return dates
            else:
                self.log(f"Failed to fetch dates: {response.text}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"Error fetching dates: {e}", "ERROR")
            return []
    
    def create_test_document(self):
        """Create a test document"""
        self.log("Creating test document...")
        
        test_content = """
        Machine Learning is a subset of Artificial Intelligence that focuses on 
        creating systems that can learn from data and improve their performance 
        without being explicitly programmed.
        
        Key Machine Learning Concepts:
        
        1. Supervised Learning: The model learns from labeled training data. 
           Examples include linear regression, logistic regression, decision trees, 
           and support vector machines. The model uses input-output pairs to learn 
           the relationship between variables.
        
        2. Unsupervised Learning: The model learns from unlabeled data. 
           The goal is to discover hidden patterns or structures in the data. 
           Examples include clustering, dimensionality reduction, and association rules.
        
        3. Reinforcement Learning: The model learns by interacting with an environment, 
           receiving rewards or penalties based on its actions. This is used in 
           robotics, game playing, and autonomous systems.
        
        4. Deep Learning: A subfield of machine learning based on artificial neural networks 
           with multiple layers. It's particularly effective for image recognition, 
           natural language processing, and complex pattern recognition tasks.
        
        5. Feature Engineering: The process of creating new features from raw data to 
           improve model performance. Good features can significantly improve model accuracy.
        
        6. Model Evaluation: Assessing model performance using metrics like accuracy, 
           precision, recall, F1-score, and ROC-AUC curves.
        
        Applications of Machine Learning:
        - Healthcare: Disease diagnosis and prediction
        - Finance: Fraud detection and risk assessment
        - E-commerce: Recommendation systems
        - Transportation: Autonomous vehicles
        - Natural Language Processing: Translation, sentiment analysis
        """
        
        doc_data = {
            "doc_title": "Machine Learning Introduction",
            "doc_content": test_content,
            "uploaded_date": str(date.today()),
            "category": "technology"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/documents",
                headers=self.get_headers(),
                json=doc_data
            )
            
            if response.status_code == 201:
                doc = response.json()
                self.log(f"Document created: ID={doc['id']}, Title={doc['doc_title']}", "SUCCESS")
                return doc
            else:
                self.log(f"Failed to create document: {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Error creating document: {e}", "ERROR")
            return None
    
    def chat_with_document(self, document_id: int, query: str):
        """Chat with a document using RAG"""
        self.log(f"Chatting with document {document_id}...")
        self.log(f"Query: {query}")
        
        chat_data = {
            "document_id": document_id,
            "query": query
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/documents/chat",
                headers=self.get_headers(),
                json=chat_data
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log("Response received:", "SUCCESS")
                print(f"\nDocument: {result['document_title']}")
                print(f"Your Question: {result['user_query']}")
                print(f"\nChatbot Response:\n{result['chatbot_response']}")
                print(f"\nTimestamp: {result['timestamp']}\n")
                return result
            else:
                self.log(f"Failed to get response: {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Error chatting with document: {e}", "ERROR")
            return None
    
    def run_demo(self):
        """Run complete demo"""
        print("\n" + "="*60)
        print("RAG Document Chatbot Demo")
        print("="*60 + "\n")
        
        # Step 1: Login
        if not self.login():
            self.log("Failed to login. Exiting.", "ERROR")
            return False
        
        print()
        
        # Step 2: Get existing documents
        documents = self.get_documents()
        
        print()
        
        # Step 3: Get document dates
        dates = self.get_document_dates()
        
        print()
        
        # Step 4: Try to chat with first document if available
        if documents:
            doc = documents[0]
            print(f"\nChatting with document: {doc['doc_title']}\n")
            
            # Ask some sample questions
            sample_queries = [
                "What is this document about?",
                "What are the main topics covered?",
                "Provide a summary of the key points."
            ]
            
            for query in sample_queries:
                response = self.chat_with_document(doc['id'], query)
                if response is None:
                    break
                print("\n" + "-"*60 + "\n")
        else:
            self.log("No documents found. Creating a test document...", "INFO")
            print()
            
            doc = self.create_test_document()
            if doc:
                print("\nChatting with new document...\n")
                
                sample_queries = [
                    "What is Machine Learning?",
                    "What are the types of Machine Learning?",
                    "How is Machine Learning applied?"
                ]
                
                for query in sample_queries:
                    response = self.chat_with_document(doc['id'], query)
                    if response is None:
                        break
                    print("\n" + "-"*60 + "\n")
        
        print("="*60)
        self.log("Demo completed successfully!", "SUCCESS")
        print("="*60 + "\n")
        return True


def main():
    """Main entry point"""
    print("\nRAG Document Chatbot Test Script")
    print("================================\n")
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/documents/health", timeout=2)
        if response.status_code != 200:
            print("ERROR: API health check failed")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"ERROR: Cannot connect to API at {API_BASE_URL}")
        print(f"Make sure the API server is running: python main.py")
        print(f"Error: {e}")
        return False
    
    print("✓ API is running\n")
    
    # Run tester
    tester = ChatbotTester(API_BASE_URL)
    return tester.run_demo()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
