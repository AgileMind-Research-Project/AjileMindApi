from llama_cpp import Llama
import os
import json

# --- (Configuration) ---
MODEL_FOLDER = "models"
MODEL_FILE = "mistral-7b-instruct-v0.2.Q4_K_S.gguf"
MODEL_PATH = os.path.join(os.getcwd(), MODEL_FOLDER, MODEL_FILE)

# --- 1. Load The LLM ---
print(f"Loading Model from: {MODEL_PATH}")
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=0, n_ctx=2048, verbose=False
    )
    print("✅ Model Loaded Successfully.")
except Exception as e:
    print(f"❌ Error Loading Model: {e}")
    exit()

# --- 2. Listener Agent Function 
def analyze_update(text_input):
    """

    """
    prompt = f"""
    You are a Standup Analyzer. Classify the update into JSON.
    
    ### STRICT INSTRUCTIONS:
    1. Output ONLY valid JSON.
    2. Use ONLY one of the following categories: ["TASK", "PLAN", "BLOCKER"].
    3. Do NOT invent new categories like "DEPLOYMENT" or "TESTING". Map them to "TASK".

    Example 1:
    Input: I deployed the code.
    Output: {{"category": "TASK", "description": "Deployed the code", "status": "Done"}}
    
    Example 2:
    Input: I am stuck on the API.
    Output: {{"category": "BLOCKER", "description": "API issue", "status": "Stuck"}}
    
    ---
    Input: {text_input}
    Output:
    """
    
    try:
        response = llm(prompt, max_tokens=256, stop=["}"], temperature=0.01, echo=False)
        output_text = response["choices"][0]["text"].strip()
        
        if not output_text.endswith("}"):
            output_text += "}"
            
        start_idx = output_text.find("{")
        if start_idx != -1:
            output_text = output_text[start_idx:]
            
        return json.loads(output_text)
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
        return None

# --- 3. Mock Tools --

def tool_update_jira(task_details):
    print(f"\n[🔨 ACTION: JIRA] Creating new Jira Ticket...")
    print(f"   └── Summary: {task_details.get('description')}")
    print(f"   └── Status:  {task_details.get('status')}")
    print("   ✅ Jira Updated Successfully (Mock).")

def tool_resolve_blocker(blocker_details):
    print(f"\n[🚨 ACTION: BLOCKER RESOLVER] Critical Issue Detected!")
    print(f"   └── Issue: {blocker_details.get('description')}")
    print("   🔍 Searching Knowledge Base for solutions...")
    print("   💡 Suggestion: Check the 'Auth Middleware' documentation or ask Senior Dev 'Chamara'.")

# --- 4. The Orchestrator ---
def run_agentic_flow(user_input):
    print(f"\n🗣️ User says: '{user_input}'")
    print("   ... Analyzing ...")
    
    # 1. Listener Agent
    result = analyze_update(user_input)
    
    if result:
        category = result.get("category")
        print(f"   🎯 Detected Category: {category}")
        
        # 2. Decision Logic
        if category == "TASK" or category == "PLAN":
            tool_update_jira(result)
        elif category == "BLOCKER":
            tool_resolve_blocker(result)
        else:
            print("   ℹ️ No specific action required.")
    else:
        print("   ❌ Failed to analyze input.")

# --- 5. Main Execution Loop ---
if __name__ == "__main__":
    # Test Case 1: Normal Progress 
    run_agentic_flow("I successfully deployed the frontend to the dev server.")
    
    # Test Case 2: බාධකයක් (Blocker)
    run_agentic_flow("I can't proceed because the database connection is timing out.")