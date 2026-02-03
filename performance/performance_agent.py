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
    "temperature": 0

}

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def test_redis():
    """Verify connection to Redis."""
    try:
        r.ping()
        print("Performance Agent connected to Redis", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)


def refactor_code(code: str, task) -> RefactorResult:
    """
    Sends code to Gemini and returns a structured RefactorResult object.
    """
    
    # The System Instruction defines the 'personality' of this specific agent
    system_instruction = """
       You are a Performance Refactoring Agent.

Goal:
Improve runtime performance and/or memory efficiency under realistic workloads.

Performance includes:
- Reduced algorithmic complexity
- Eliminating redundant computation
- Better data structures
- Reduced memory allocation or retention
- Faster hot-path execution
- Avoiding unnecessary I/O or blocking

Constraints:
- Do NOT change external behavior.
- Do NOT add features or dependencies.
- Do NOT refactor for readability, style, or security.
- Prefer small, localized changes.
- Avoid speculative or micro-optimizations.

If no meaningful performance or memory improvements exist:
- Return an empty unified diff.

Unified Diff Format (follow exactly):

--- a/example.py
+++ b/example.py
@@ -10,8 +10,7 @@
 def compute(items):
-    total = 0
-    for x in items:
-        total += x
-    return total
+    return sum(items)


        """


    user_prompt = (
       f"""
        Task given: {task}
        \n
        Code: {code}
        """
    )


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
    print("Performance Agent is listening for tasks...", flush=True)

    while True:
        rtask = r.brpop('performance_tasks', timeout=0)
        
        if rtask:
            try:
                task_data = rtask[1]
                task = RefactorTask.model_validate_json(task_data)
                print(f"Recieved task: {task.task_id} for file: {task.file_name}", flush=True)
                
                # REFACTORING GOES HERE
                
                try:
                    with open(task.file_name, 'r') as file:
                        file_content = file.read()

                except Exception as e:
                    print(f"Error: {e}", flush=True)

                result = refactor_code(file_content, task)

                print(result.diff, flush=True)
                r.lpush("orchestrator_tasks", result.model_dump_json())
                print(f"Performance sent to orchestrator: {task.task_id}", flush=True)

            except Exception as e:
                print(f"Error processing task: {e}", flush=True)
                # In a real app, you'd send a RefactorResult with status=FAILED here

if __name__ == "__main__":
    main()













