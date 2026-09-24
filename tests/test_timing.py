import numpy as np
import pytest
from backend.timing import fit_slot
from backend.audio import replace_audio,SR

def test_fit_never_truncates_voiced_tail():
    with pytest.raises(ValueError,match='未截斷'):fit_slot(np.ones(24001)*.2,24000,1)
    out=fit_slot(np.ones(12000)*.2,24000,1)
    assert len(out)==24000 and np.all(out[12000:]==0)

@pytest.mark.parametrize('start,end',[(.19,2.19),(.123,2.456)])
def test_fixed_slot_retains_exact_timeline_and_samples(start,end):
    rng=np.random.default_rng(12);x=rng.normal(0,.01,(4*SR,2))
    voice=fit_slot(np.sin(np.arange(24000)*.02)*.02,24000,end-start)
    out,report=replace_audio(x,x*.8,voice,24000,start,end,True,fixed_slot=True)
    i,j=round(start*SR),round(end*SR)
    assert len(out)==len(x) and report['shift_seconds']==0
    np.testing.assert_array_equal(out[:i],x[:i]);np.testing.assert_array_equal(out[j:],x[j:])
