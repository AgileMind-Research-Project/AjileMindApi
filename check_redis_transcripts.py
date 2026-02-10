
import sys
import os
import redis
import json

# Detected hardcoded credentials from app/core/redis_chat_client.py
redis_host = 'redis-12930.crce182.ap-south-1-1.ec2.cloud.redislabs.com'
redis_port = 12930
password = 'psPSNesjowZCqBOyeuoLPhy6ql4a29t9'

print(f"Using Cloud Redis: {redis_host}:{redis_port}")

print(f"Connecting to Redis...")
try:
    r = redis.Redis(host=redis_host, port=int(redis_port), password=password, decode_responses=True)
    r.ping()
    print("✅ Connected to Redis")
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    exit(1)

print("\nScanning for transcripts (meeting:*:transcript)...")
keys = r.keys('meeting:*:transcript')
print(f"Found {len(keys)} transcript(s)")

for key in keys:
    print(f"\nExample Key: {key}")
    try:
        data = r.hgetall(key)
        print(f"Date: {data.get('stored_at')}")
        print(f"Created By: {data.get('created_by')}")
        print(f"Metadata: {data.get('metadata')}")
        
        content = data.get('content', '')
        print("\n--- Content Preview (First 200 chars) ---")
        print(content[:200])
        print("-----------------------------------------")
    except Exception as e:
        print(f"Error reading key {key}: {e}")

if not keys:
    print("\nNo transcripts found. Try creating a meeting, sending messages, and ending it.")
