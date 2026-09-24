"""Adapter contract tests; run with the full model dependencies, no weights needed."""
import importlib.util
import numpy as np
import pytest
if importlib.util.find_spec('qwen_tts') is None:
    pytest.skip('full Qwen dependencies not installed', allow_module_level=True)
from backend.engine import LocalEngine
from backend.audio import SR

class FakeQwen:
    def __init__(self,seconds=.6):self.seconds=seconds;self.calls=[]
    def generate_voice_clone(self,**kwargs):
        self.calls.append(kwargs)
        return [np.sin(np.arange(round(self.seconds*24000))*.06)*.1],24000

def test_clone_receives_reference_but_returns_only_new_utterance(monkeypatch):
    monkeypatch.setenv('AUDIO_LAB_DEVICE','cpu')
    engine=LocalEngine();engine.tts=FakeQwen()
    voice,sr=engine.generate(np.ones(4*SR)*.05,'四秒的參考。','我不是一個好父親。',123)
    call=engine.tts.calls[0]
    assert len(voice)/sr<1 and len(call['ref_audio'][0])==4*SR
    assert call['ref_text']=='四秒的参考。' and call['text']=='我不是一个好父亲。'
    assert call['language']=='Chinese' and not call['x_vector_only_mode']
    assert 'fix_duration' not in call and 'speed' not in call

def test_qwen_fit_pads_but_rejects_long_speech(monkeypatch):
    monkeypatch.setenv('AUDIO_LAB_DEVICE','cpu')
    engine=LocalEngine();engine.tts=FakeQwen()
    voice,sr=engine.generate(np.ones(4*SR)*.05,'原聲。','你好。',123,target_seconds=2)
    assert len(voice)==2*sr and np.all(voice[sr:]==0)
    engine.tts=FakeQwen(3)
    with pytest.raises(ValueError,match='未截斷'):
        engine.generate(np.ones(4*SR)*.05,'原聲。','你好。',456,target_seconds=2)
