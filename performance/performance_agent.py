import redis
import sys
import time
from shared.schemas import RefactorTask, RefactorResult, TaskStatus

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def test_redis():
    """Verify connection to Redis."""
    try:
        r.ping()
        print("Performance Agent connected to Redis", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)

def main():
    test_redis()
    print("Performance Agent is listening for tasks...", flush=True)

    while True:
        rtask = r.brpop('performance_tasks', timeout=0)
        
        if rtask:
            try:
                task_data = rtask[1]
                task = RefactorTask.model_validate_json(task_data)
                print(f"Recieved task: {task.task_id} for file: {task.file_name}", flush=True)
                
                # REFACTORING GOES HERE
                time.sleep(2)
                
                result = RefactorResult(
                    task_id=task.task_id,
                    agent_type=task.agent_type,
                    status=TaskStatus.COMPLETED,
                    diff=f"--- {task.file_name}\n+++ {task.file_name}\n- # Mock performance optimization",
                    explanation="Performance agent processed the file successfully."
                )

                r.lpush("orchestrator_tasks", result.model_dump_json())
                print(f"Performance sent to orchestrator: {task.task_id}", flush=True)

            except Exception as e:
                print(f"Error processing task: {e}", flush=True)
                # In a real app, you'd send a RefactorResult with status=FAILED here

if __name__ == "__main__":
    main()















# import redis
# import json
# import time
# import sys
# r = redis.Redis(host='redis', port=6379, db=0)

# print("Performance Agent is running", flush=True)
# r = redis.Redis(host='redis', port=6379, db=0, socket_timeout=5)

# try:
#     r.ping()
#     print("Performance Agent connected to Redis!", flush=True)
# except Exception as e:
#     print(f"Redis connection failed: {e}", flush=True)
#     sys.exit(1)


# while True:
#     rtask = r.brpop('performance_tasks', timeout=0)
#     if rtask:
#         task = json.loads(rtask[1])
#         print(f"Received task: {task}", flush=True)
#         time.sleep(2)
        
#         resp = {"task_id": 13, "description": "Performance agent response back to the orchestrator"}
#         r.lpush("orchestrator_tasks", json.dumps(resp))
#         print(f"Sent orchestrator task(Performance): {task['task_id']}", flush=True) 
#         break