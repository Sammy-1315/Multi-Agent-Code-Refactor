"""
Docstring for orchestrator.main

* Use this module to run the orchestrator component of the project
* This will use redis message queue to dispatch tasks to agents, and also listen for incoming
    results from the agents
* It will also conduct diff-based edits once all results are received
"""


import redis
import uuid
import sys
from shared.schemas import RefactorTask, RefactorResult, AgentType, TaskStatus
from typing import List
from pathlib import Path
from unidiff import PatchSet
# Connect to Redis
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def test_redis():
    # test redis connection
    try:
        r.ping()
        print("Orchestrator connected to Redis", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)



def send_tasks(file_name: str):
    # send pydantic tasks to each message queue
    batch_id = str(uuid.uuid4())
    
    tasks = [
        RefactorTask(task_id=batch_id, file_name=file_name, agent_type=AgentType.PERFORMANCE),
        RefactorTask(task_id=batch_id, file_name=file_name, agent_type=AgentType.SECURITY),
        RefactorTask(task_id=batch_id, file_name=file_name, agent_type=AgentType.STYLE),
    ]

    for task in tasks:
        queue_name = f"{task.agent_type.value}_tasks"
        # .model_dump_json() handles the serialization properly
        r.lpush(queue_name, task.model_dump_json())
        print(f"Dispatched {task.agent_type.value} task (ID: {task.task_id})", flush=True)

    return batch_id




def listen_for_results(expected_count: int):
    # listens until all results are collected
    results = []
    
    while len(results) < expected_count:
        raw_data = r.brpop('orchestrator_tasks', timeout=0)
        
        if raw_data:
            try:
                result = RefactorResult.model_validate_json(raw_data[1])
                results.append(result)
                print(f"Received result from {result.agent_type.value} (Status: {result.status.value})", flush=True)
            except Exception as e:
                print(f"Error parsing agent result: {e}", flush=True)

    print("All agent results collected.", flush=True)
    return results




if __name__ == "__main__":
    test_redis()
    
    # Mock file data for testing
    TEST_FILENAME = "/app/shared/test_file.py"
    current_batch_id = send_tasks(TEST_FILENAME)

    all_results = listen_for_results(expected_count=3)
    
    











# """
# Docstring for orchestrator.main

# * Use this module to run the orchestrator component of the project

# * This will use redis message queue to dispatch tasks to agents, and also listen for incoming
#     results from the agents

# * It will also conduct diff-based edits once all results are received
# """
# import redis
# import json
# import time
# import sys
# r = redis.Redis(host='redis', port=6379, db=0)

# print("Orchestrator running", flush=True)

# def test_redis():
#     try:
#         r.ping()
#         print("Orchestrator connected to Redis", flush=True)
#     except Exception as e:
#         print(f"Redis connection failed: {e}", flush=True)
#         sys.exit(1)


# def send_tasks():

#     task1 = {"task_id": 13, "description": "Sammy is kinda goated(performance)"}
#     task2 = {"task_id": 14, "description": "Sammy is kinda goated(security)"}
#     task3 = {"task_id": 15, "description": "Sammy is kinda goated(style)"}

#     r.lpush("performance_tasks", json.dumps(task1))
#     r.lpush("security_tasks", json.dumps(task2))
#     r.lpush("style_tasks", json.dumps(task3))

#     print("Dispatched test tasks to each agent", flush=True)

# def listen_tasks():
#     num = 0
#     while True:
#         rtask = r.brpop('orchestrator_tasks', timeout=0)
#         if rtask:
#             num += 1
#             task = json.loads(rtask[1])
#             print(f"Received task: {task}", flush=True)
#             if num == 3:
#                 break
        

