# Test-AI

Test-AI is a CLI tool that generates pytest tests for Python functions using an LLM.

Instead of generating tests directly, Test-AI generates **structured test specifications** and stores them in a JSON sidecar file. Those specs are then deterministically rendered into pytest tests.

This approach makes generated tests easier to review, debug, and regenerate.

---

# How It Works

Test-AI uses a two-step workflow.

### 1. Generate Test Specs


test-ai spec file.py


This command:

• discovers functions in the file  
• asks an LLM to generate test cases  
• stores the result in a sidecar JSON file  

Example output:


tests/file.testai.json


The tool also inserts a marker in the function:


# @testai spec=tests/file.testai.json
2. Generate Pytest Tests
test-ai gen file.py

This command:

• reads the sidecar spec file
• renders deterministic pytest tests
• writes them to the tests/ directory

Example output:

tests/test_file.py
Example
Source file:

def add(a, b):
    return a + b

Run:

test-ai spec math_utils.py

Produces:

tests/math_utils.testai.json

Then run:

test-ai gen math_utils.py

Produces:

tests/test_math_utils.py
Spec Format

Specs are stored in JSON:

{
  "version": 1,
  "target": "math_utils.py",
  "functions": {
    "add": {
      "cases": [
        {"in": {"a": 2, "b": 3}, "out": 5}
      ],
      "raises": []
    }
  }
}
Installation

Clone the repo:

git clone <repo>
cd test-ai

Create a virtual environment:

python -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Environment Setup

Set your OpenAI API key:

export OPENAI_API_KEY=your_key

Or create a .env file:

OPENAI_API_KEY=your_key
Usage

Generate specs:

test-ai spec file.py

Generate tests:

test-ai gen file.py

Optional flags:

--dry-run
--force
Project Structure
test_ai/
├── cli.py
├── core/
│   └── spec_store.py
├── languages/python/
│   ├── discover.py
│   ├── marker_inject.py
│   ├── render_pytest.py
│   └── spec_extract.py
└── llm/
    ├── client.py
    └── prompts.py
