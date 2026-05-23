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

system_instruction = """
        You are a Refactoring Orchestrator.

        INPUT:
        - Original source file.
        - Unified diffs from three agents: [1] ARCHITECTURE, [2] PERFORMANCE, [3] STYLE.

        GOAL:
        Produce a single refactored code file by merging agent diff changes in order of precedence (1 > 2 > 3).

        CONFLICT & MERGE RULES:
        1. OVERLAPPING CHANGES: Merge hunks where logically additive (e.g., if ARCHITECTURE moves a block and STYLE renames a variable within that same block, include both).
        2. EXCLUSIVE CHANGES: If changes are mutually exclusive or incompatible, the earlier agent takes absolute precedence. Discard the conflicting portion of the later diff.
        3. NO INVENTION: Do not "improve" code or bridge gaps between agents. Only apply what is explicitly provided.
        4. ATOMICITY: If a later diff hunk cannot be applied cleanly to the version resulting from earlier agents, drop that hunk.
    
        CONSTRAINTS:
        - Preserve original external behavior.
        - Output ONLY the final code file
        - Do not refactor beyond the provided inputs.
        """

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
            agent_diffs_text += f"\n--- {result.agent_type} diff ---\n{result.diff} explanation ---\n{result.explanation}\n"

    priority_order = {"ARCHITECTURE": 0, "PERFORMANCE": 1, "STYLE": 2}
    results_sorted = sorted(results, key=lambda r: priority_order[r.agent_type.value.upper()])

    user_prompt = f"""
        Task: Consolidate the following agent diffs into a single final code file for this source file. Be sure to merge all refactoring diffs in a logical way. 
                First start with the structural modifications done by the architecture diffs, then include the performance changes, then include the style modifications suggested.

        Original file path: {file_name}

        Original code:
        {file_content}

        Agent diffs:
        {results_sorted}
        """

    try:
        response = client.models.generate_content(
            model="gemini-3-flash",
            contents=f"{system_instruction}\n\n{user_prompt}",
            config=config
        )
        
        return response.parsed

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None


def consolidate_output_2(results):
    """
    Assume each agent is a blackbox that produces a correct refactoring. 

    consolidate_output simply merges everything in one call, we want this one to be more efficient.

    Approach:
    Use unidiff python library to create unique objects for each agent's diff - we can then use these objects for final consolidation

    Apply diffs in a specific order, if there is any overlap we disregard all those hunk's edits. Keep track of these hunk edits and the agent it came from

    At the end of applying the hunks that had no overlap, we go through the skipped hunks, call the agent again but on the new code
        We then repeat same process again until there are no overlapping hunks at all. 
    """

    priority_order = {"ARCHITECTURE": 0, "PERFORMANCE": 1, "STYLE": 2}
    results_sorted = sorted(results, key=lambda r: priority_order[r.agent_type.value.upper()])
    pass


if __name__ == "__main__":
    test_redis()
    
    # Mock file data for testing
    TEST_FILENAME = "/app/shared/test_file_2.py"
    current_batch_id = send_tasks(TEST_FILENAME)

    all_results = listen_for_results(expected_count=3)
    final_result = consolidate_output(all_results, TEST_FILENAME)
    SHARED_DIR = "/app/shared"


    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".diff",
        delete=False,
        dir=SHARED_DIR,
    ) as tmp_file:
        tmp_file.write(final_result.final_content)
        temp_path = tmp_file.name

    print(f"Final diff written to: {temp_path}")









