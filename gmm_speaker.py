import os
import pickle
from typing import Dict, List, Optional, Tuple

import numpy as np
import librosa
from sklearn.mixture import GaussianMixture


class GMMScorer:
    def __init__(self, model_dir: str = "data/gmm_models", sr: int = 16000, n_mfcc: int = 24, n_fft: int = 400, hop_length: int = 160):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)
        self.sr = sr
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length

    def _extract_mfcc(self, wav_path: str) -> np.ndarray:
        y, sr = librosa.load(wav_path, sr=self.sr, mono=True)
        if y.size == 0:
            return np.zeros((1, self.n_mfcc * 3), dtype=np.float32)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.n_mfcc, n_fft=self.n_fft, hop_length=self.hop_length)
        delta = librosa.feature.delta(mfcc)
        delta2 = librosa.feature.delta(mfcc, order=2)
        feat = np.vstack([mfcc, delta, delta2]).T
        return feat.astype(np.float32)

    def _model_path(self, user_id: str) -> str:
        safe_id = str(user_id).replace("/", "_").replace("\\", "_")
        return os.path.join(self.model_dir, f"{safe_id}.pkl")

    def fit_user(self, user_id: str, audio_files: List[str], n_components: int = 8, max_iter: int = 200, random_state: int = 42, covariance_type: str = "diag") -> bool:
        Xs = []
        for p in audio_files:
            try:
                X = self._extract_mfcc(p)
                if X.size > 0:
                    Xs.append(X)
            except Exception:
                continue
        if not Xs:
            return False
        X = np.vstack(Xs)
        gmm = GaussianMixture(n_components=n_components, covariance_type=covariance_type, max_iter=max_iter, random_state=random_state)
        gmm.fit(X)
        with open(self._model_path(user_id), "wb") as f:
            pickle.dump(gmm, f)
        return True

    def has_user_model(self, user_id: str) -> bool:
        return os.path.exists(self._model_path(user_id))

    def score_user(self, user_id: str, test_wav: str) -> Optional[float]:
        path = self._model_path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                gmm: GaussianMixture = pickle.load(f)
            X = self._extract_mfcc(test_wav)
            if X.size == 0:
                return None
            ll = gmm.score(X)
            return float(ll)
        except Exception:
            return None

    def score_all_users(self, users_db: Dict[str, dict], test_wav: str) -> Tuple[Dict[str, float], Dict[str, float], Optional[str]]:
        raw_scores: Dict[str, float] = {}
        for uid in users_db.keys():
            s = self.score_user(uid, test_wav)
            if s is not None:
                raw_scores[uid] = s
        if not raw_scores:
            return {}, {}, None
        vals = np.array(list(raw_scores.values()), dtype=np.float32)
        mu = float(vals.mean())
        sd = float(vals.std() + 1e-8)
        zscores = {u: (v - mu) / sd for u, v in raw_scores.items()}
        best = max(raw_scores, key=raw_scores.get)
        return raw_scores, zscores, best