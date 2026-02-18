
import ollama
import sys

def check_ollama():
    try:
        print("Checking Ollama status...")
        models = ollama.list()
        print("Ollama is reachable.")
        print(f"Available models: {models}")
        return True
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return False

if __name__ == "__main__":
    success = check_ollama()
    sys.exit(0 if success else 1)
