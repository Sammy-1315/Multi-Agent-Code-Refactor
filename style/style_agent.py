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
        print("Style Agent connected to Redis!", flush=True)
    except Exception as e:
        print(f"Redis connection failed: {e}", flush=True)
        sys.exit(1)

def refactor_code(code: str, task) -> RefactorResult:
    """
    Sends code to Gemini and returns a structured RefactorResult object.
    """
    
    # The System Instruction defines the 'personality' of this specific agent
    system_instruction = """
        You are a Style Refactoring Agent.

        Your sole responsibility is to improve code style and adherence to language
        conventions without altering behavior.

        Constraints:
        - There are two other agents: security and performance. If an issue would likely be better 
            addressed by one of these agents, leave it to them and do not modify. 
        - Consider ONLY style, formatting, and language-idiomatic conventions.
        - Explicitly IGNORE performance, security, correctness, and architectural issues.
        - Do NOT change logic, control flow, or data structures.
        - Do NOT introduce new functionality or remove existing behavior.

        Style Scope (non-exhaustive):
        - Naming conventions (variables, functions, classes)
        - Formatting, spacing, and indentation
        - Language-idiomatic constructs
        - Comment clarity and docstring conventions
        - File and import organization (style-only)
        - Lint-level issues that do NOT affect behavior

        Output Requirements:
        - Apply the minimal set of changes needed to achieve idiomatic, consistent style.
        - Prefer standard language conventions over personal or subjective preferences.
        - If no meaningful style improvements exist, explicitly state so.

        Response Format:
        - The diff field MUST be in unified diff format.
        - The diff field should not include any comments, just the unified diff

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
                    print(f"Error: {e}")
                
              
                result = refactor_code(file_content, task)


                r.lpush("orchestrator_tasks", result.model_dump_json())
                print(f"Style sent to orchestrator: {task.task_id}", flush=True)

            except Exception as e:
                print(f"Error processing task: {e}", flush=True)
                # In a real app, you'd send a RefactorResult with status=FAILED here

if __name__ == "__main__":
    main()





