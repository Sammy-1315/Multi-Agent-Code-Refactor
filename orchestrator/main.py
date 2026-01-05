"""
Docstring for orchestrator.main

* Use this module to run the orchestrator component of the project

* This will use redis message queue to dispatch tasks to agents, and also listen for incoming
    results from the agents

* It will also conduct diff-based edits once all results are received
"""
import redis
import json
import time
import sys
r = redis.Redis(host='redis', port=6379, db=0)

print("Orchestrator is running", flush=True)

try:
    r.ping()
    print("Orchestrator connected to Redis!", flush=True)
except Exception as e:
    print(f"Redis connection failed: {e}", flush=True)
    sys.exit(1)




task = {"task_id": 13, "description": "Sammy is kinda goated ngl"}
r.lpush("performance_tasks", json.dumps(task))
print(f"Dispatched task: {task}", flush=True)

time.sleep(5)
