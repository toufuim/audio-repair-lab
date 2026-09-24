import numpy as np
import pytest
from backend.audio import SR,replace_audio,validate_ranges,background_for_length

@pytest.mark.parametrize('new_length',[.45,1.65])
@pytest.mark.parametrize('background',[True,False])
def test_replacement_preserves_prefix_and_shifted_suffix(new_length,background):
 rng=np.random.default_rng(5);source=rng.normal(0,.015,(SR*3,2));vocals=source*.7
 y=np.sin(np.arange(round(24000*new_length))*2*np.pi*180/24000)*.08
 out,report=replace_audio(source,vocals,y,24000,.7,1.7,background)
 expected_new=round(SR*new_length)
 assert len(out)==len(source)-SR+expected_new
 np.testing.assert_array_equal(out[:round(.7*SR)],source[:round(.7*SR)])
 np.testing.assert_array_equal(out[round(.7*SR)+expected_new:],source[round(1.7*SR):])
 assert np.isfinite(out).all() and np.max(abs(out))<1
 assert report['background_extended']==(new_length>1 and background)

def test_background_extension_is_finite_for_short_residual():
 out,extended=background_for_length(np.zeros((3,2)),200,SR)
 assert extended and out.shape==(200,2)

def test_invalid_reference_length_and_bounds():
 s={'mode':'generate','ref_start':0,'ref_end':13}
 with pytest.raises(ValueError):validate_ranges(s,20)
 s['ref_end']=5;s['ref_start']=-1
 with pytest.raises(ValueError):validate_ranges(s,20)

def test_peak_control_does_not_change_rest():
 x=np.ones((SR*3,2))*.1;v=x*.5
 y=np.ones(24000)*2
 out,report=replace_audio(x,v,y,24000,1,2,True)
 assert report['gain_limited'] is False or np.max(abs(out))<=.981
 np.testing.assert_array_equal(out[:SR],x[:SR])
