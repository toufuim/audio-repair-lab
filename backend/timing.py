"""Timeline fitting: silence padding only, never pitch/time stretch."""
import numpy as np

def fit_slot(voice, sr, seconds):
    """Pad silence only. Never cut speech or stretch a waveform to fill a slot."""
    n = round(seconds * sr)
    if len(voice) > n:
        extra = voice[n:]
        if np.max(np.abs(extra), initial=0) > 1e-5:
            raise ValueError('新台詞超過選取時間，未截斷語音。請縮短台詞、擴大範圍，或改用自然長度。')
        voice = voice[:n]
    return np.pad(voice, (0, n-len(voice)))
