#!/usr/bin/env python
"""
Ollama + Llama 3.2 Connection Tester

Test Ollama connectivity and Llama model availability
Run this before starting the full API to ensure everything is configured
"""

import requests
import sys
import time
from typing import Tuple, Dict
import subprocess
import platform

class OllamaConnectionTester:
    """Test Ollama connection and configuration"""
    
    def __init__(self, host: str = "http://localhost", port: int = 11434):
        self.host = host
        self.port = port
        self.base_url = f"{host}:{port}"
        self.results = []
    
    def log(self, message: str, status: str = "INFO"):
        """Log with status"""
        icons = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅ ",
            "ERROR": "❌ ",
            "WARNING": "⚠️ ",
            "TESTING": "🧪 "
        }
        print(f"{icons.get(status, '  ')} {message}")
    
    def test_connection(self) -> bool:
        """Test basic connection to Ollama"""
        self.log(f"Testing connection to {self.base_url}...", "TESTING")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                self.log(f"Connected to Ollama at {self.base_url}", "SUCCESS")
                self.results.append(("Connection", True, None))
                return True
            else:
                error = f"Status {response.status_code}: {response.text}"
                self.log(f"Connection failed: {error}", "ERROR")
                self.results.append(("Connection", False, error))
                return False
                
        except requests.exceptions.ConnectionError:
            error = f"Cannot connect to {self.base_url}"
            self.log(error, "ERROR")
            self.log("Make sure Ollama is running: ollama serve", "WARNING")
            self.results.append(("Connection", False, error))
            return False
            
        except Exception as e:
            error = str(e)
            self.log(f"Error: {error}", "ERROR")
            self.results.append(("Connection", False, error))
            return False
    
    def test_models(self) -> Tuple[bool, Dict]:
        """Test available models"""
        self.log("Checking available models...", "TESTING")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code != 200:
                error = f"Failed to fetch models: {response.status_code}"
                self.log(error, "ERROR")
                self.results.append(("Models Check", False, error))
                return False, {}
            
            data = response.json()
            models = data.get("models", [])
            
            if not models:
                error = "No models found. Run: ollama pull llama3.2"
                self.log(error, "WARNING")
                self.results.append(("Models Check", False, error))
                return False, {}
            
            self.log(f"Found {len(models)} model(s):", "SUCCESS")
            for model in models:
                model_name = model.get("name", "unknown")
                model_size = model.get("size", 0)
                size_gb = model_size / (1024**3)
                self.log(f"  • {model_name} ({size_gb:.2f} GB)")
            
            # Check for llama3.2
            model_names = [m.get("name", "") for m in models]
            has_llama = any("llama" in name for name in model_names)
            
            if has_llama:
                self.results.append(("Models Check", True, None))
                return True, {"count": len(models), "names": model_names}
            else:
                error = "No Llama model found. Run: ollama pull llama3.2"
                self.log(error, "WARNING")
                self.results.append(("Models Check", False, error))
                return False, {"count": len(models), "names": model_names}
                
        except Exception as e:
            error = str(e)
            self.log(f"Error fetching models: {error}", "ERROR")
            self.results.append(("Models Check", False, error))
            return False, {}
    
    def test_model_inference(self, model: str = "llama3.2") -> bool:
        """Test if model can generate response"""
        self.log(f"Testing inference with {model}...", "TESTING")
        self.log("(This may take 30-60 seconds on first run)", "INFO")
        
        try:
            # Test with short prompt
            prompt = "What is AI? Answer in one sentence."
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120  # 2 minute timeout for inference
            )
            
            if response.status_code != 200:
                error = f"Inference failed: {response.status_code}"
                self.log(error, "ERROR")
                self.results.append(("Model Inference", False, error))
                return False
            
            data = response.json()
            generated_text = data.get("response", "").strip()
            
            if generated_text:
                self.log(f"Model responded successfully!", "SUCCESS")
                self.log(f"Response: {generated_text[:100]}...", "INFO")
                self.results.append(("Model Inference", True, None))
                return True
            else:
                error = "Model returned empty response"
                self.log(error, "ERROR")
                self.results.append(("Model Inference", False, error))
                return False
                
        except requests.exceptions.Timeout:
            error = "Model inference timed out (>2 min)"
            self.log(error, "ERROR")
            self.log("Model might be loading. Try again in a moment.", "INFO")
            self.results.append(("Model Inference", False, error))
            return False
            
        except Exception as e:
            error = str(e)
            self.log(f"Error during inference: {error}", "ERROR")
            self.results.append(("Model Inference", False, error))
            return False
    
    def test_rag_pipeline(self) -> bool:
        """Test RAG pipeline (chunking + context)"""
        self.log("Testing RAG pipeline...", "TESTING")
        
        try:
            # Test document chunking
            test_doc = """
            Machine Learning is a subset of Artificial Intelligence.
            It focuses on creating systems that can learn from data.
            Deep learning uses neural networks with multiple layers.
            Natural Language Processing helps computers understand text.
            Computer Vision enables machines to interpret images.
            """
            
            # Simulate RAG chunking
            chunk_size = 100
            chunks = []
            for i in range(0, len(test_doc), chunk_size):
                chunk = test_doc[i:i+chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
            
            self.log(f"Document chunking: {len(chunks)} chunks created", "SUCCESS")
            
            # Test with model
            rag_prompt = f"""
            Document Content:
            {test_doc}
            
            Question: What is Machine Learning?
            Answer based only on the document:
            """
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": rag_prompt,
                    "stream": False,
                },
                timeout=120
            )
            
            if response.status_code == 200:
                self.log("RAG pipeline test successful!", "SUCCESS")
                self.results.append(("RAG Pipeline", True, None))
                return True
            else:
                error = f"RAG pipeline test failed: {response.status_code}"
                self.log(error, "ERROR")
                self.results.append(("RAG Pipeline", False, error))
                return False
                
        except Exception as e:
            error = str(e)
            self.log(f"Error in RAG pipeline: {error}", "ERROR")
            self.results.append(("RAG Pipeline", False, error))
            return False
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for test_name, success, error in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name}")
            if error:
                print(f"      → {error}")
        
        print("="*60)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Ready to use Ollama RAG chatbot!")
            return True
        else:
            print("\n⚠️  Some tests failed. Check errors above.")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("\n" + "="*60)
        print("OLLAMA + LLAMA 3.2 CONNECTION TESTER")
        print("="*60 + "\n")
        
        # Test 1: Connection
        if not self.test_connection():
            self.print_summary()
            return False
        
        print()
        
        # Test 2: Models
        success, models_info = self.test_models()
        if not success or not models_info:
            self.print_summary()
            return False
        
        print()
        
        # Test 3: Inference
        if not self.test_model_inference():
            self.print_summary()
            return False
        
        print()
        
        # Test 4: RAG Pipeline
        self.test_rag_pipeline()
        
        print()
        
        return self.print_summary()


def check_ollama_installed() -> bool:
    """Check if Ollama is installed"""
    print("Checking if Ollama is installed...\n")
    
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ Ollama found: {result.stdout.strip()}\n")
            return True
        else:
            print("❌ Ollama not found in PATH\n")
            return False
            
    except FileNotFoundError:
        print("❌ Ollama not found. Install from: https://ollama.com/download\n")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}\n")
        return False


def check_ollama_running() -> bool:
    """Check if Ollama server is running"""
    print("Checking if Ollama server is running...\n")
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama server is running\n")
            return True
    except:
        pass
    
    print("⚠️  Ollama server is NOT running")
    print("Run in a terminal: ollama serve\n")
    
    if platform.system() == "Windows":
        print("Tip: Ollama should auto-start on Windows. Check System Tray.")
    elif platform.system() == "Darwin":  # macOS
        print("Tip: Check if Ollama is in the menu bar (macOS).")
    else:  # Linux
        print("Tip: Run in background: nohup ollama serve > ollama.log 2>&1 &")
    
    print()
    return False


def main():
    """Main test runner"""
    print("\n")
    
    # Check if Ollama is installed
    if not check_ollama_installed():
        print("Please install Ollama from: https://ollama.com/download")
        return False
    
    # Check if Ollama server is running
    if not check_ollama_running():
        print("Please start Ollama server with: ollama serve")
        return False
    
    # Run connection tests
    tester = OllamaConnectionTester()
    success = tester.run_all_tests()
    
    print("\n" + "="*60)
    if success:
        print("NEXT STEPS:")
        print("1. Ensure Ollama server is running: ollama serve")
        print("2. Update AjileMindApi/.env with:")
        print("   LLM_PROVIDER=ollama")
        print("   OLLAMA_MODEL=llama3.2")
        print("3. Start API: python main.py")
        print("4. Run demo: python test_rag_chatbot.py")
    else:
        print("TROUBLESHOOTING:")
        print("1. Make sure Ollama is running: ollama serve")
        print("2. Check model is installed: ollama list")
        print("3. Pull model if needed: ollama pull llama3.2")
        print("4. Check port 11434 is not blocked")
    print("="*60 + "\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
