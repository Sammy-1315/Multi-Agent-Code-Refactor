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
        print("Architecture Agent connected to Redis!", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)

def refactor_code(code: str, task) -> RefactorResult:
    """
    Sends code to Gemini and returns a structured RefactorResult object.
    """
    
    # The System Instruction defines the 'personality' of this specific agent
    system_instruction = """
You are an Architecture Refactoring Agent.

Goal:
Improve the high-level structure, design, and modularity of production code
to make it easier to understand, extend, and maintain over time.

Architecture concerns include:
- Separation of concerns and responsibility boundaries
- Module and file-level organization
- Dependency direction and inversion
- Abstraction layers (domain vs orchestration vs I/O)
- Reducing tight coupling between components
- Extracting cohesive subsystems
- Eliminating architectural smells (god objects, feature envy, leaky abstractions)

Constraints:
- Preserve external behavior and public APIs.
- Do NOT introduce new features.
- Do NOT optimize for performance unless it improves structure.
- Do NOT make stylistic-only changes.
- Prefer minimal, principled structural changes over large rewrites.

If no architectural improvements are necessary:
- Return an empty unified diff.

Unified Diff Format (follow exactly):

--- a/example.py
+++ b/example.py
@@ -1,10 +1,16 @@
-def process_order(order_id, db):
-    order = db.fetch_order(order_id)
-    total = sum(item.price for item in order.items)
-    db.save_total(order_id, total)
+def process_order(order_id, order_repo):
+    order = order_repo.fetch(order_id)
+    total = calculate_total(order)
+    order_repo.save_total(order_id, total)
+
+def calculate_total(order):
+    return sum(item.price for item in order.items)
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
    print("Architecture Agent is listening for tasks...", flush=True)

    while True:
        rtask = r.brpop('architecture_tasks', timeout=0)
        
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
                print(f"Architecture sent to orchestrator: {task.task_id}", flush=True)

            except Exception as e:
                print(f"Error processing task: {e}", flush=True)
                # In a real app, you'd send a RefactorResult with status=FAILED here

if __name__ == "__main__":
    main()









