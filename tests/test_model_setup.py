from backend import config

def test_missing_nested_tokenizer_blocks_readiness(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'QWEN',tmp_path/'qwen')
    monkeypatch.setattr(config,'WHISPER',tmp_path/'whisper')
    monkeypatch.setattr(config,'DEMUCS',tmp_path/'demucs.th')
    for name in config.QWEN_FILES:
        path=config.QWEN/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
    assert config.readiness()['Qwen 語音生成']
    (config.QWEN/'speech_tokenizer/model.safetensors').unlink()
    assert not config.readiness()['Qwen 語音生成']
