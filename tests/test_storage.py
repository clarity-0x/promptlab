"""Tests for storage functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from promptlab.storage import Storage


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        storage = Storage(db_path)
        yield storage


def test_create_run(temp_storage):
    """Test creating a new run."""
    run_id = temp_storage.create_run(
        prompt_file="test.yaml",
        models=["gpt-4o", "claude-sonnet"],
        config_hash="abc12345"
    )
    
    assert isinstance(run_id, str)
    assert len(run_id) > 10  # Should be timestamp + random suffix
    assert "-" in run_id  # Should contain separator


def test_get_run(temp_storage):
    """Test retrieving run metadata."""
    # Create a run
    run_id = temp_storage.create_run(
        prompt_file="test.yaml",
        models=["gpt-4o"],
        config_hash="abc12345"
    )
    
    # Retrieve it
    run = temp_storage.get_run(run_id)
    
    assert run is not None
    assert run["id"] == run_id
    assert run["prompt_file"] == "test.yaml"
    assert run["models"] == ["gpt-4o"]
    assert run["config_hash"] == "abc12345"
    assert isinstance(run["timestamp"], datetime)


def test_get_nonexistent_run(temp_storage):
    """Test retrieving a non-existent run."""
    run = temp_storage.get_run("nonexistent-run-id")
    assert run is None


def test_save_and_get_results(temp_storage):
    """Test saving and retrieving test results."""
    # Create a run
    run_id = temp_storage.create_run(
        prompt_file="test.yaml",
        models=["gpt-4o"],
        config_hash="abc12345"
    )
    
    # Save some results
    temp_storage.save_result(
        run_id=run_id,
        test_case_idx=0,
        model="gpt-4o",
        response="Hello world!",
        expected="Hello world!",
        tokens_in=10,
        tokens_out=5,
        cost=0.0001,
        latency_ms=250
    )
    
    temp_storage.save_result(
        run_id=run_id,
        test_case_idx=1,
        model="gpt-4o",
        response=None,
        expected="Goodbye",
        error="Timeout error"
    )
    
    # Retrieve results
    results = temp_storage.get_results(run_id)
    
    assert len(results) == 2
    
    # Check first result
    result1 = results[0]
    assert result1["test_case_idx"] == 0
    assert result1["model"] == "gpt-4o"
    assert result1["response"] == "Hello world!"
    assert result1["expected"] == "Hello world!"
    assert result1["tokens_in"] == 10
    assert result1["tokens_out"] == 5
    assert result1["cost"] == 0.0001
    assert result1["latency_ms"] == 250
    assert result1["error"] is None
    
    # Check second result (with error)
    result2 = results[1]
    assert result2["test_case_idx"] == 1
    assert result2["model"] == "gpt-4o"
    assert result2["response"] is None
    assert result2["expected"] == "Goodbye"
    assert result2["error"] == "Timeout error"


def test_list_runs(temp_storage):
    """Test listing recent runs."""
    # Initially empty
    runs = temp_storage.list_runs()
    assert len(runs) == 0
    
    # Create some runs
    run_id1 = temp_storage.create_run(
        prompt_file="test1.yaml",
        models=["gpt-4o"],
        config_hash="hash1"
    )
    
    run_id2 = temp_storage.create_run(
        prompt_file="test2.yaml",
        models=["claude-sonnet"],
        config_hash="hash2"
    )
    
    # List runs
    runs = temp_storage.list_runs()
    
    assert len(runs) == 2
    
    # Should be sorted by timestamp DESC (newest first)
    assert runs[0]["id"] == run_id2  # Most recent
    assert runs[1]["id"] == run_id1  # Older
    
    # Check run details
    assert runs[0]["prompt_file"] == "test2.yaml"
    assert runs[0]["models"] == ["claude-sonnet"]
    assert runs[1]["prompt_file"] == "test1.yaml"
    assert runs[1]["models"] == ["gpt-4o"]


def test_list_runs_with_limit(temp_storage):
    """Test listing runs with a limit."""
    # Create several runs
    for i in range(5):
        temp_storage.create_run(
            prompt_file=f"test{i}.yaml",
            models=["gpt-4o"],
            config_hash=f"hash{i}"
        )
    
    # List with limit
    runs = temp_storage.list_runs(limit=3)
    
    assert len(runs) == 3
    # Should get the 3 most recent ones
    assert runs[0]["prompt_file"] == "test4.yaml"
    assert runs[1]["prompt_file"] == "test3.yaml"
    assert runs[2]["prompt_file"] == "test2.yaml"


def test_multiple_models_same_run(temp_storage):
    """Test saving results for multiple models in the same run."""
    # Create a run with multiple models
    run_id = temp_storage.create_run(
        prompt_file="test.yaml",
        models=["gpt-4o", "claude-sonnet"],
        config_hash="abc12345"
    )
    
    # Save results for both models on the same test case
    temp_storage.save_result(
        run_id=run_id,
        test_case_idx=0,
        model="gpt-4o",
        response="GPT response",
        expected="Expected output",
        cost=0.001
    )
    
    temp_storage.save_result(
        run_id=run_id,
        test_case_idx=0,
        model="claude-sonnet",
        response="Claude response",
        expected="Expected output",
        cost=0.002
    )
    
    # Retrieve and verify
    results = temp_storage.get_results(run_id)
    
    assert len(results) == 2
    
    # Should be sorted by test_case_idx, then model
    gpt_result = next(r for r in results if r["model"] == "gpt-4o")
    claude_result = next(r for r in results if r["model"] == "claude-sonnet")
    
    assert gpt_result["response"] == "GPT response"
    assert gpt_result["cost"] == 0.001
    
    assert claude_result["response"] == "Claude response"
    assert claude_result["cost"] == 0.002


def test_database_persistence(temp_storage):
    """Test that data persists after storage object is recreated."""
    db_path = temp_storage.db_path
    
    # Create a run and save result
    run_id = temp_storage.create_run(
        prompt_file="persistent.yaml",
        models=["gpt-4o"],
        config_hash="persist123"
    )
    
    temp_storage.save_result(
        run_id=run_id,
        test_case_idx=0,
        model="gpt-4o",
        response="Persistent response",
        expected="Expected"
    )
    
    # Create new storage instance with same database
    new_storage = Storage(db_path)
    
    # Data should still be there
    run = new_storage.get_run(run_id)
    assert run is not None
    assert run["prompt_file"] == "persistent.yaml"
    
    results = new_storage.get_results(run_id)
    assert len(results) == 1
    assert results[0]["response"] == "Persistent response"