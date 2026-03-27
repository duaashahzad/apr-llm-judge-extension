Task Definition
- Give a buggy program and a candidate patch, determine whether the patch correctly fixes the bug

Inputs
- Bug description (if available)
- Buggy code (method or file)
- Patch (diff or modified method)
- Optional test outcome

Evaluation Criteria
- Compilation correctness
- Test correctness
- Semantic correctness

Outputs
- YES/NO/UNKNOWN per criteron
- Confidence score
- Short explanation


### Output Schema

The LLM judge is required to return a valid JSON object with the following fields:

- `compiles`: categorical value indicating compilation correctness
- `passes_tests`: categorical value indicating test correctness
- `semantic_correctness`: integer score from 1 (incorrect) to 5 (fully correct)
- `confidence`: integer score from 1 (low) to 5 (high)
- `explanation`: short natural language justification

