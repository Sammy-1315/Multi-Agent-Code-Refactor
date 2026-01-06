import redis
import json
import time
import sys
r = redis.Redis(host='redis', port=6379, db=0)

print("Security Agent is running", flush=True)
r = redis.Redis(host='redis', port=6379, db=0, socket_timeout=5)

try:
    r.ping()
    print("Security Agent connected to Redis!", flush=True)
except Exception as e:
    print(f"Redis connection failed: {e}", flush=True)
    sys.exit(1)


while True:
    rtask = r.brpop('security_tasks', timeout=0)
    if rtask:
        task = json.loads(rtask[1])
        print(f"Received task: {task}", flush=True)
        time.sleep(2)
        
        resp = {"task_id": 14, "description": "Security agent response back to the orchestrator"}
        r.lpush("orchestrator_tasks", json.dumps(resp))
        print(f"Sent orchestrator task(Security): {task['task_id']}", flush=True) 
        break