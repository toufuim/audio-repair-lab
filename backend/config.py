"""Local model locations shared by the service and explicit setup command."""
import os
from pathlib import Path
from .store import DATA

MODEL_REVISIONS = {
    'Qwen/Qwen3-TTS-12Hz-0.6B-Base': '5d83992436eae1d760afd27aff78a71d676296fc',
    'Qwen/Qwen3-TTS-12Hz-1.7B-Base': 'fd4b254389122332181a7c3db7f27e918eec64e3',
}
MODEL_ID = os.environ.get('AUDIO_LAB_QWEN_MODEL', 'Qwen/Qwen3-TTS-12Hz-0.6B-Base')
if MODEL_ID not in MODEL_REVISIONS:
    raise ValueError('AUDIO_LAB_QWEN_MODEL 必須是官方 0.6B-Base 或 1.7B-Base。')
MODELS = Path(os.environ.get('AUDIO_LAB_MODELS', str(DATA/'models')))
QWEN = Path(os.environ.get('AUDIO_LAB_QWEN_PATH', str(MODELS/MODEL_ID.split('/')[-1])))
WHISPER = Path(os.environ.get('AUDIO_LAB_WHISPER', str(MODELS/'whisper-small')))
DEMUCS = MODELS/'demucs/955717e8-8726e21a.th'
QWEN_FILES = ('config.json', 'generation_config.json', 'merges.txt', 'model.safetensors',
              'preprocessor_config.json', 'tokenizer_config.json', 'vocab.json',
              'speech_tokenizer/config.json', 'speech_tokenizer/configuration.json',
              'speech_tokenizer/model.safetensors', 'speech_tokenizer/preprocessor_config.json')
WHISPER_FILES = ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt')


def readiness():
    present = lambda p: p.is_file() and p.stat().st_size > 0
    return {'Qwen 語音生成': all(present(QWEN/p) for p in QWEN_FILES),
            '人聲分離': present(DEMUCS),
            '語音辨識': all(present(WHISPER/p) for p in WHISPER_FILES)}
