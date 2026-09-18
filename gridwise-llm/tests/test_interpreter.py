from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
def test_prompt_contains_canonical_semantics():
    assert "start inclusive and end exclusive" in SYSTEM_PROMPT
    assert "80% reduction" in SYSTEM_PROMPT
    assert "1 PM to 3 PM" in SYSTEM_PROMPT
