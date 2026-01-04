"""
Test Agent Setup
Quick test script to verify the agent is working correctly
"""
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_model_file():
    """Test if model file exists"""
    from config import MODEL_PATH
    
    print("\n" + "=" * 60)
    print("Testing Model File")
    print("=" * 60)
    
    if Path(MODEL_PATH).exists():
        file_size = Path(MODEL_PATH).stat().st_size / (1024 ** 3)  # Size in GB
        print(f"✓ Model file found: {MODEL_PATH}")
        print(f"✓ File size: {file_size:.2f} GB")
        return True
    else:
        print(f"✗ Model file not found: {MODEL_PATH}")
        return False


def test_model_loading():
    """Test model loading"""
    print("\n" + "=" * 60)
    print("Testing Model Loading")
    print("=" * 60)
    
    try:
        from model_loader import get_model
        
        print("Loading model (this may take a few moments)...")
        model = get_model()
        print("✓ Model loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Model loading failed: {str(e)}")
        logger.error("Model loading error", exc_info=True)
        return False


def test_simple_inference():
    """Test simple inference"""
    print("\n" + "=" * 60)
    print("Testing Simple Inference")
    print("=" * 60)
    
    try:
        from agent_service import create_agent
        
        print("Creating agent...")
        agent = create_agent()
        
        print("\nSending test query: 'What is agile methodology?'")
        response = agent.chat("What is agile methodology? Answer in 2 sentences.")
        
        print(f"\n✓ Response received:")
        print(f"{response}\n")
        return True
    except Exception as e:
        print(f"✗ Inference failed: {str(e)}")
        logger.error("Inference error", exc_info=True)
        return False


def test_conversation():
    """Test multi-turn conversation"""
    print("\n" + "=" * 60)
    print("Testing Multi-turn Conversation")
    print("=" * 60)
    
    try:
        from agent_service import create_agent
        
        agent = create_agent()
        
        # First message
        print("\n[1] User: What is a sprint?")
        response1 = agent.chat("What is a sprint? Answer in 1 sentence.")
        print(f"Agent: {response1}")
        
        # Follow-up message
        print("\n[2] User: How long is it?")
        response2 = agent.chat("How long is it typically?")
        print(f"Agent: {response2}")
        
        # Check history
        history = agent.get_history()
        print(f"\n✓ Conversation history contains {len(history)} exchanges")
        return True
    except Exception as e:
        print(f"✗ Conversation test failed: {str(e)}")
        logger.error("Conversation error", exc_info=True)
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MISTRAL 7B AGENT - SETUP VERIFICATION")
    print("=" * 60)
    
    results = {
        "Model File": test_model_file(),
        "Model Loading": False,
        "Simple Inference": False,
        "Conversation": False
    }
    
    # Only proceed with loading if model file exists
    if results["Model File"]:
        results["Model Loading"] = test_model_loading()
        
        # Only proceed with inference if model loaded
        if results["Model Loading"]:
            results["Simple Inference"] = test_simple_inference()
            results["Conversation"] = test_conversation()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Agent is ready to use!")
    else:
        print("✗ SOME TESTS FAILED - Please check the errors above")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error("Fatal error during testing", exc_info=True)
        sys.exit(1)
