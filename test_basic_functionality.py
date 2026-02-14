#!/usr/bin/env python3
"""
Basic functionality test for promptlab.
Run this after installing dependencies to verify everything works.

Usage:
    pip install -e .
    python test_basic_functionality.py
"""

import tempfile
import sys
from pathlib import Path

# Add current directory to path so we can import promptlab
sys.path.insert(0, '.')

def test_basic_functionality():
    """Test basic functionality without making API calls."""
    
    try:
        from promptlab.config import load_prompt_config, render_prompt
        print("✓ Config module imported successfully")
        
        from promptlab.storage import Storage
        print("✓ Storage module imported successfully")
        
        from promptlab.display import display_results
        print("✓ Display module imported successfully")
        
        # Test config loading with example file
        example_file = Path("examples/classify-sentiment.yaml")
        if example_file.exists():
            config = load_prompt_config(example_file)
            print(f"✓ Loaded config: {config.name}")
            print(f"  - {len(config.test_cases)} test cases")
            print(f"  - Default model: {config.model}")
        
        # Test prompt rendering
        template = "Hello {{name}}, you are {{age}} years old."
        variables = {"name": "Alice", "age": "25"}
        result = render_prompt(template, variables)
        expected = "Hello Alice, you are 25 years old."
        assert result == expected, f"Expected {expected}, got {result}"
        print("✓ Prompt rendering works correctly")
        
        # Test storage with temporary database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            storage = Storage(db_path)
            
            # Create a test run
            run_id = storage.create_run(
                prompt_file="test.yaml",
                models=["gpt-4o"],
                config_hash="test123"
            )
            print(f"✓ Created test run: {run_id}")
            
            # Save a test result
            storage.save_result(
                run_id=run_id,
                test_case_idx=0,
                model="gpt-4o", 
                response="positive",
                expected="positive",
                tokens_in=10,
                tokens_out=2,
                cost=0.0001,
                latency_ms=150
            )
            print("✓ Saved test result")
            
            # Retrieve the result
            results = storage.get_results(run_id)
            assert len(results) == 1
            assert results[0]["response"] == "positive"
            print("✓ Retrieved test result")
        
        print("\n🎉 All basic functionality tests passed!")
        print("\nTo test with real API calls:")
        print("1. Set your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)")
        print("2. Run: promptlab run examples/classify-sentiment.yaml")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install dependencies first:")
        print("  pip install -e .")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)