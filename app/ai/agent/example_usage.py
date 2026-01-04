"""
Example Usage of Agent Service
Demonstrates how to use the Mistral 7B agent
"""
import logging
from agent_service import create_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def simple_chat_example():
    """Simple chat example"""
    print("=" * 60)
    print("Simple Chat Example")
    print("=" * 60)
    
    # Create agent
    agent = create_agent()
    
    # Single query
    response = agent.chat("What are the key principles of agile methodology?")
    print(f"\nUser: What are the key principles of agile methodology?")
    print(f"Agent: {response}\n")


def conversation_example():
    """Multi-turn conversation example"""
    print("=" * 60)
    print("Conversation Example")
    print("=" * 60)
    
    # Create agent
    agent = create_agent()
    
    # Multi-turn conversation
    questions = [
        "What is a sprint in agile?",
        "How long should a sprint typically be?",
        "What happens at the end of a sprint?"
    ]
    
    for question in questions:
        response = agent.chat(question)
        print(f"\nUser: {question}")
        print(f"Agent: {response}\n")
    
    # Show conversation history
    print("\nConversation History:")
    print("-" * 60)
    history = agent.get_history()
    for i, entry in enumerate(history, 1):
        print(f"\n[{i}] {entry['timestamp']}")
        print(f"User: {entry['user']}")
        print(f"Assistant: {entry['assistant'][:100]}...")


def custom_system_prompt_example():
    """Example with custom system prompt"""
    print("=" * 60)
    print("Custom System Prompt Example")
    print("=" * 60)
    
    # Create agent with custom system prompt
    custom_prompt = """You are a technical expert specializing in sprint planning 
    and task estimation. Provide detailed, practical advice with specific examples."""
    
    agent = create_agent(system_prompt=custom_prompt)
    
    response = agent.chat("How do I estimate story points for a new feature?")
    print(f"\nUser: How do I estimate story points for a new feature?")
    print(f"Agent: {response}\n")


def custom_parameters_example():
    """Example with custom generation parameters"""
    print("=" * 60)
    print("Custom Parameters Example")
    print("=" * 60)
    
    agent = create_agent()
    
    # More creative response (higher temperature)
    response = agent.generate_response(
        "Suggest 5 creative team-building activities for a remote team",
        temperature=0.9,
        max_tokens=500
    )
    print(f"\nUser: Suggest 5 creative team-building activities for a remote team")
    print(f"Agent (temperature=0.9): {response}\n")


def agile_use_cases():
    """Specific agile project management use cases"""
    print("=" * 60)
    print("Agile Project Management Use Cases")
    print("=" * 60)
    
    agent = create_agent()
    
    use_cases = [
        "Generate a sprint planning agenda for a 2-week sprint",
        "What questions should I ask in a sprint retrospective?",
        "How do I handle scope creep during a sprint?",
        "Create a template for daily standup meeting notes",
    ]
    
    for use_case in use_cases:
        print(f"\n{'=' * 60}")
        print(f"Use Case: {use_case}")
        print('=' * 60)
        response = agent.chat(use_case)
        print(f"\n{response}\n")
        
        # Clear history between use cases for independent responses
        agent.clear_history()


if __name__ == "__main__":
    try:
        print("\n" + "=" * 60)
        print("Mistral 7B Agent - Example Usage")
        print("=" * 60 + "\n")
        
        # Run examples
        simple_chat_example()
        print("\n" + "=" * 60 + "\n")
        
        conversation_example()
        print("\n" + "=" * 60 + "\n")
        
        custom_system_prompt_example()
        print("\n" + "=" * 60 + "\n")
        
        custom_parameters_example()
        print("\n" + "=" * 60 + "\n")
        
        agile_use_cases()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Error running examples: {str(e)}", exc_info=True)
