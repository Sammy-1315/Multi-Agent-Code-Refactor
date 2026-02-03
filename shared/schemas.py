from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class AgentType(str, Enum):
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    STYLE = "style"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RefactorTask(BaseModel):
    task_id: str = Field(..., description="Unique UUID for the refactoring request")
    file_name: str = Field(..., description="Name of the file being refactored")
    agent_type: AgentType
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RefactorResult(BaseModel):
    task_id: str
    agent_type: AgentType
    status: TaskStatus
    diff: Optional[str] = Field(None, description="The Unified Diff output from the agent")
    explanation: Optional[str] = Field(None, description="LLM's reasoning for the changes")
    error: Optional[str] = Field(None, description="Error message if the task failed")

class ConsolidateAgentOutput(BaseModel):
    original_file_path: str
    original_content: str
    final_diff: str

    
