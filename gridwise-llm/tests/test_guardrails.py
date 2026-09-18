import pytest
from app.llm.models import RawInterpretation
from app.guardrails.normalizer import validate_and_normalize

def raw(i,t,a):
    return RawInterpretation(note_index=i,applies=t!="no_op",directive_type=t,structured_adjustment=a,
                             explanation="x")
def test_solar_rejects_unsorted_hours():
    with pytest.raises(ValueError):
        validate_and_normalize([raw(0,"solar_reduction",{"hours":[14,13],"factor":.2})],1,100)
def test_noop():
    x=validate_and_normalize([raw(0,"no_op",None)],1,100)
    assert x[0].applies is False
def test_invalid_factor():
    with pytest.raises(ValueError):
        validate_and_normalize([raw(0,"solar_reduction",{"hours":[1],"factor":1.2})],1,100)
