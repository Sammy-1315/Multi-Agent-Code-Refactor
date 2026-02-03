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
from shared.schemas import RefactorTask, RefactorResult, AgentType, ConsolidateAgentOutput
from typing import List
from pathlib import Path
from unidiff import PatchSet
import json
import os
import tempfile
# Connect to Redis
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)


from google import genai
import os
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
config = {
    "response_mime_type": "application/json",
    "response_schema": ConsolidateAgentOutput,
    "temperature": 0

}
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
        RefactorTask(task_id=batch_id, file_name=file_name, agent_type=AgentType.ARCHITECTURE),
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


def consolidate_output(results, file_name):
    try:
        with open(file_name, 'r') as file:
            file_content = file.read()
    except Exception as e:
        return None
        print(f"Error: {e}")
    
    agent_diffs_text = ""
    for result in results:
        if result.diff:  # only include if a diff exists
            agent_diffs_text += f"\n--- {result.agent_type} diff ---\n{result.diff}\n"

    priority_order = {"ARCHITECTURE": 0, "PERFORMANCE": 1, "STYLE": 2}
    results_sorted = sorted(results, key=lambda r: priority_order[r.agent_type.value.upper()])

    system_instruction = """
        You are a Refactoring Orchestrator.

Input:
- Original source file
- Unified diffs from ARCHITECTURE, PERFORMANCE, and STYLE agents

Goal:
Produce a single final unified diff for the original file.

Ordering & Precedence:
1. Apply ARCHITECTURE diff
2. Apply PERFORMANCE diff
3. Apply STYLE diff

Conflict Rules:
- Earlier agents take precedence over later agents.
- If multiple diffs modify the same lines:
  - Keep the earlier agent’s change.
  - Discard or partially apply later diffs as needed.
- Never rewrite code to merge intent.
- If a diff hunk cannot be applied cleanly, drop it.

Constraints:
- Only apply changes that appear in the agent diffs.
- Do NOT invent new changes.
- Do NOT refactor or improve code beyond resolving conflicts.
- Preserve original external behavior

Unified Diff Format (follow exactly):

--- a/example.py
+++ b/example.py
@@ -3,7 +3,7 @@
 def add(a, b):
-    return a+b
+    return a + b


        """


    user_prompt = f"""
        Task: Consolidate the following agent diffs into a single final unified diff for this source file. Go in order of ARCHITECTURE -> PERFORMANCE -> STYLE

        Original file path: {file_name}
        Original content:
        {file_content}

        Agent diffs:
        {results_sorted}
        """

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
    


if __name__ == "__main__":
    test_redis()
    
    # Mock file data for testing
    TEST_FILENAME = "/app/shared/test_file.py"
    current_batch_id = send_tasks(TEST_FILENAME)

    all_results = listen_for_results(expected_count=3)
    final_result = consolidate_output(all_results, TEST_FILENAME)
    print(final_result.final_diff)
    SHARED_DIR = "/app/shared"


    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".diff",
        delete=False,
        dir=SHARED_DIR,
    ) as tmp_file:
        tmp_file.write(final_result.final_diff)
        temp_path = tmp_file.name

    print(f"Final diff written to: {temp_path}")
    







