# Public sample test is integration-oriented: configure a real LLM before running.
# The script below compares all public cases; this pytest module is intentionally skipped by default.
import pytest
@pytest.mark.skip(reason="Requires configured generative LLM; run scripts/test_public_samples.py")
def test_public_samples():
    pass
