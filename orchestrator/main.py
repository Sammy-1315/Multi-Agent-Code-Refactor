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

print("Orchestrator running", flush=True)

try:
    r.ping()
    print("Orchestrator connected to Redis", flush=True)
except Exception as e:
    print(f"Redis connection failed: {e}", flush=True)
    sys.exit(1)




task1 = {"task_id": 13, "description": "Sammy is kinda goated(performance)"}
task2 = {"task_id": 14, "description": "Sammy is kinda goated(security)"}
task3 = {"task_id": 15, "description": "Sammy is kinda goated(style)"}


r.lpush("performance_tasks", json.dumps(task1))
r.lpush("security_tasks", json.dumps(task2))
r.lpush("style_tasks", json.dumps(task3))

print("Dispatched test tasks to each agent", flush=True)

num = 0
while True:
    rtask = r.brpop('orchestrator_tasks', timeout=0)
    if rtask:
        num += 1
        task = json.loads(rtask[1])
        print(f"Received task: {task}", flush=True)
        if num == 3:
            break
        

