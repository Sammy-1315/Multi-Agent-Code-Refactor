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

system_instruction = """
        You are a Style Refactoring Agent.

        Goal:
        Apply minimal, behavior-preserving style improvements only.

        Allowed changes (ONLY):
        - Formatting and whitespace per common language conventions (e.g., PEP8 for Python, standard Java/JS style guides)
        - Import ordering or cleanup (no new imports)
        - Local variable or parameter renaming where usage is unchanged
        - Adding or improving docstrings/comments
        - Removing clearly unused imports or comments

        Hard constraints:
        - Do NOT change logic, control flow, data flow, or data structures.
        - Do NOT add, remove, reorder, or duplicate functions, classes, routes, or public APIs.
        - Do NOT move code blocks or rewrite entire functions.
        - If a change could plausibly affect runtime behavior, DO NOT make it.

        Diff rules:
        - Output a unified diff ONLY.
        - Do NOT include hunks with identical before/after lines.
        - Keep hunks small and local; avoid mechanical rewrites.
        - If no safe improvements exist, return an EMPTY diff.

        Unified Diff Format (follow exactly):

        --- a/example.py
        +++ b/example.py
        @@ -12,7 +12,7 @@
        -    total = price * qty
        +    total_price = price * qty

        """

def test_redis():
    """Verify connection to Redis."""
    try:
        r.ping()
        print("Style Agent connected to Redis!", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)

def refactor_code(code: str, task) -> RefactorResult:
    """
    Sends code to Gemini and returns a structured RefactorResult object.
    """

    # System instruction below
    

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
    print("Style Agent is listening for tasks...", flush=True)

    while True:
        rtask = r.brpop('style_tasks', timeout=0)
        
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
                print(result.diff)
                print(result.explanation)

                r.lpush("orchestrator_tasks", result.model_dump_json())

                print(f"Style sent to orchestrator: {task.task_id}", flush=True)

            except Exception as e:
                print(f"Error processing task: {e}", flush=True)
                # In a real app, you'd send a RefactorResult with status=FAILED here

if __name__ == "__main__":
    main()





