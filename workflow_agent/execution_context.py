import uuid
import time
from datetime import datetime

class ExecutionContext:
    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.stages = {}
        self.metadata = {}
        
    def start_stage(self, stage_name: str):
        self.stages[stage_name] = {
            "start_time": time.time(),
            "status": "IN_PROGRESS"
        }
        
    def end_stage(self, stage_name: str, status: str = "SUCCESS", details: dict = None):
        if stage_name in self.stages:
            duration = (time.time() - self.stages[stage_name]["start_time"]) * 1000  # ms
            self.stages[stage_name].update({
                "end_time": time.time(),
                "duration_ms": int(duration),
                "status": status,
                "details": details or {}
            })
            
    def get_duration_ms(self) -> int:
        return int((time.time() - self.start_time) * 1000)
        
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": datetime.fromtimestamp(self.start_time).isoformat(),
            "total_duration_ms": self.get_duration_ms(),
            "stages": self.stages,
            "metadata": self.metadata
        }
