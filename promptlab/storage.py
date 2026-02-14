"""SQLite storage for test results."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import PromptConfig


class Storage:
    """SQLite storage for promptlab results."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize storage with database path."""
        if db_path is None:
            # Default to ~/.promptlab/results.db
            db_path = Path.home() / ".promptlab" / "results.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    timestamp INTEGER NOT NULL,
                    prompt_file TEXT NOT NULL,
                    models TEXT NOT NULL,
                    config_hash TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    run_id TEXT NOT NULL,
                    test_case_idx INTEGER NOT NULL,
                    model TEXT NOT NULL,
                    response TEXT,
                    expected TEXT NOT NULL,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    cost REAL,
                    latency_ms INTEGER,
                    error TEXT,
                    inputs TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs (id)
                )
            """)
            
            # Migration: Add inputs column if it doesn't exist
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if "inputs" not in columns:
                conn.execute("ALTER TABLE results ADD COLUMN inputs TEXT")
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs (timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_results_run_id ON results (run_id)")
    
    def create_run(
        self,
        prompt_file: str,
        models: List[str],
        config_hash: str
    ) -> str:
        """Create a new test run and return its ID."""
        run_id = self._generate_run_id()
        timestamp = int(datetime.now().timestamp())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO runs (id, timestamp, prompt_file, models, config_hash) VALUES (?, ?, ?, ?, ?)",
                (run_id, timestamp, prompt_file, ",".join(models), config_hash)
            )
        
        return run_id
    
    def save_result(
        self,
        run_id: str,
        test_case_idx: int,
        model: str,
        response: Optional[str],
        expected: str,
        inputs: Optional[Dict[str, Any]] = None,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        cost: Optional[float] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Save a test result."""
        import json
        
        inputs_json = json.dumps(inputs) if inputs else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO results 
                   (run_id, test_case_idx, model, response, expected, tokens_in, tokens_out, cost, latency_ms, error, inputs)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, test_case_idx, model, response, expected, tokens_in, tokens_out, cost, latency_ms, error, inputs_json)
            )
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run metadata by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                "id": row["id"],
                "timestamp": datetime.fromtimestamp(row["timestamp"]),
                "prompt_file": row["prompt_file"],
                "models": row["models"].split(","),
                "config_hash": row["config_hash"]
            }
    
    def get_results(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all results for a run."""
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM results WHERE run_id = ? 
                   ORDER BY test_case_idx, model""",
                (run_id,)
            )
            
            results = []
            for row in cursor:
                # Parse inputs JSON
                inputs = None
                if row["inputs"]:
                    try:
                        inputs = json.loads(row["inputs"])
                    except json.JSONDecodeError:
                        inputs = None
                
                results.append({
                    "test_case_idx": row["test_case_idx"],
                    "model": row["model"],
                    "response": row["response"],
                    "expected": row["expected"],
                    "tokens_in": row["tokens_in"],
                    "tokens_out": row["tokens_out"],
                    "cost": row["cost"],
                    "latency_ms": row["latency_ms"],
                    "error": row["error"],
                    "inputs": inputs
                })
            
            return results
    
    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            
            runs = []
            for row in cursor:
                runs.append({
                    "id": row["id"],
                    "timestamp": datetime.fromtimestamp(row["timestamp"]),
                    "prompt_file": row["prompt_file"],
                    "models": row["models"].split(","),
                    "config_hash": row["config_hash"]
                })
            
            return runs
    
    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        from datetime import datetime
        import random
        import string
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        return f"{timestamp}-{suffix}"