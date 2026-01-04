# standup_agent.py

from llama_cpp import Llama
import os
import time
import json

# 1. LLM ගොනුවට Path එක සකසන්න
# ඔබගේ project directory එකේම ගොනුව ඇති බව උපකල්පනය කරයි
MODEL_FILE_NAME = "modal/mistral-7b-instruct-v0.2.Q4_K_S.gguf"
MODEL_PATH = os.path.join(os.getcwd(), MODEL_FILE_NAME)

print(f"Loading Model from: {MODEL_PATH}")

# 2. LLM එක Load කරන්න
# n_gpu_layers=0: GPU (2GB) භාවිතා නොකර, සම්පූර්ණයෙන්ම CPU/RAM මත ධාවනය වීමට
# n_ctx: Context window size (input/output) - 2048 සාමාන්‍යයි.
start_time = time.time()
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=0,  
        n_ctx=2048,      
        verbose=False    # Loading messages පෙන්වන්නේ නැත
    )
    load_time = time.time() - start_time
    print(f"✅ Model Loaded Successfully in {load_time:.2f} seconds.")
except Exception as e:
    print(f"❌ Error Loading LLM: {e}")
    exit()

# 3. Few-Shot Prompt එක සකස් කරන්න (JSON Output සඳහා උපදෙස් දෙන්න)
# මෙහිදී ඔබට ඔබේම Few-Shot උදාහරණ එකතු කළ හැකිය
STANDUP_PROMPT = f"""
You are a Standup Analyzer Agent. Your task is to classify a single standup update and output a JSON object.

Output ONLY the JSON object.

Example 1 (Few-Shot):
Input: I fixed the bug in the authentication module and started testing.
Output: {{"category": "TASK", "description": "Fixed auth bug, started testing", "status": "Done"}}

Example 2 (Few-Shot):
Input: I can't connect to the staging database because the firewall is blocking me. I need IT help.
Output: {{"category": "BLOCKER", "description": "Firewall blocking access to staging DB", "status": "Waiting for IT"}}

---
INSTRUCTION: Analyze the following update.
UPDATE: I'll work on the new user registration page UI tomorrow.
Output: 
"""

# 4. Agentic Action: LLM වෙත Prompt එක යවන්න
print("\n--- Sending Prompt to LLM Agent ---")
try:
    response_stream = llm(
        STANDUP_PROMPT,
        max_tokens=200, 
        stop=["\n"], # LLM එක JSON එකෙන් පසු නවතී
        temperature=0.01, # නිරවද්‍යතාවය සඳහා අඩු උෂ්ණත්වයක්
        echo=False
    )
    
    # ප්‍රතිචාරය ලබා ගැනීම
    llm_output = response_stream["choices"][0]["text"].strip()
    
    print("\n✅ LLM Output Received:")
    print(llm_output)
    
    # JSON Parsing පරීක්ෂා කිරීම (Agentic Logic සඳහා වැදගත්)
    parsed_json = json.loads(llm_output)
    print("\nParsed JSON Category:", parsed_json.get("category"))
    
except Exception as e:
    print(f"\n❌ LLM Inference Error: {e}")
    print("This might be due to incorrect JSON output or slow CPU.")