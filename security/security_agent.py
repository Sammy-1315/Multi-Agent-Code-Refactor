import redis
import sys
import time
from shared.schemas import RefactorTask, RefactorResult, TaskStatus

from google import genai
import os
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
config = {
    "response_mime_type": "application/json",
    "response_schema": RefactorResult,
}

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def test_redis():
    """Verify connection to Redis."""
    try:
        r.ping()
        print("Security Agent connected to Redis!", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)

def refactor_code(code: str, task) -> RefactorResult:
    """
    Sends code to Gemini and returns a structured RefactorResult object.
    """
    
    # The System Instruction defines the 'personality' of this specific agent
    system_instruction = (
        """
        You are a Security Refactoring Agent. Your job is to improve the following code
        in terms of security and vulnerabilities only. Even if other issues exist, 
        you must only focus on security optimizations. Follow the response schema provided and 
        provide the final output in unified diff format. 
        """
    )

    user_prompt = (
       f"""
        Task given: {task}
        \n
        Code: {code}
        """
    )

    # Configuration for structured Pydantic output
    config = {
        "response_mime_type": "application/json",
        "response_schema": RefactorResult,
    }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"{system_instruction}\n\n{user_prompt}",
            config=config
        )
        
        # .parsed automatically returns the RefactorResult Pydantic object
        return response.parsed

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def main():
    test_redis()
    print("Security Agent is listening for tasks...", flush=True)

    while True:
        rtask = r.brpop('security_tasks', timeout=0)
        
        if rtask:
            try:
                task_data = rtask[1]
                task = RefactorTask.model_validate_json(task_data)
                print(f"Recieved task: {task.task_id} for file: {task.file_name}", flush=True)
                
                # REFACTORING GOES HERE
                time.sleep(2)
                try:
                    with open(task.file_name, 'r') as file:
                        file_content = file.read()

                except Exception as e:
                    print(f"Error: {e}")
                
                # result = RefactorResult(
                #     task_id=task.task_id,
                #     agent_type=task.agent_type,
                #     status=TaskStatus.COMPLETED,
                #     diff=f"--- {task.file_name}\n+++ {task.file_name}\n- # Mock security optimization",
                #     explanation="securitu agent processed the file successfully."
                # )
                result = refactor_code(file_content, task)
                print(result.diff, result.explanation)


                r.lpush("orchestrator_tasks", result.model_dump_json())
                print(f"Security sent to orchestrator: {task.task_id}", flush=True)

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

# print("Security Agent is running", flush=True)
# r = redis.Redis(host='redis', port=6379, db=0, socket_timeout=5)

# try:
#     r.ping()
#     print("Security Agent connected to Redis!", flush=True)
# except Exception as e:
#     print(f"Redis connection failed: {e}", flush=True)
#     sys.exit(1)


# while True:
#     rtask = r.brpop('security_tasks', timeout=0)
#     if rtask:
#         task = json.loads(rtask[1])
#         print(f"Received task: {task}", flush=True)
#         time.sleep(2)
        
#         resp = {"task_id": 14, "description": "Security agent response back to the orchestrator"}
#         r.lpush("orchestrator_tasks", json.dumps(resp))
#         print(f"Sent orchestrator task(Security): {task['task_id']}", flush=True) 
#         break