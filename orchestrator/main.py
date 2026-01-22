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

    priority_order = {"SECURITY": 0, "PERFORMANCE": 1, "STYLE": 2}
    results_sorted = sorted(results, key=lambda r: priority_order[r.agent_type.value.upper()])

    system_instruction = """
        You are a Refactoring Orchestrator AI. Your task is to consolidate multiple agent diffs into a single final unified diff.

        Constraints:
        - Apply diffs in the following order: SECURITY → PERFORMANCE → STYLE.
        - Do not change any code outside the provided diffs unless strictly necessary to resolve conflicts.
        - Ensure the final code preserves the original functionality.
        - Output should be a single unified diff representing all applied changes.
        - Do not add explanations, commentary, or extra formatting—only provide the diff.
        """


    user_prompt = f"""
        Task: Consolidate the following agent diffs into a single final diff for this source file. Go in order of SECURITY -> PERFORMANCE -> STYLE

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
    print(final_result.final_content)    
    







