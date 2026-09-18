import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app.main import app
from app.api.routes import service
from app.llm.models import RawInterpretationBatch, RawInterpretation

class FakeLLM:
    def __init__(self, batch=None, exc=None): self.batch=batch; self.exc=exc
    async def interpret(self, notes, hours):
        if self.exc: raise self.exc
        return self.batch

@pytest.fixture
def client():
    from httpx import ASGITransport, AsyncClient
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

@pytest.fixture
def fake_service(monkeypatch):
    old=service.llm
    def install(batch=None, exc=None):
        service.llm=FakeLLM(batch,exc)
    yield install
    service.llm=old
