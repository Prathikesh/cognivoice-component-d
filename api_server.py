"""Component D API server: all five layers behind one FastAPI app.

The Quest 2 / mobile client only ever talks to these endpoints.
Heavy models load once at startup; endpoints degrade gracefully with
503 when a model checkpoint is not present yet.

Run:  uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import io
import uuid
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from config import SAMPLE_RATE, MODELS_DIR
from src.layer1_ambient import check_ambient
from src.layer3_comparison import compare_scores
from src.layer4_crossmodal import (StoredHRVProvider, MockHRVProvider,
                                   validate_crossmodal)
from src.layer5_anomaly import SessionAnomalyDetector

FUSION_CKPT = MODELS_DIR / "fusion_v2.pt"
ANOMALY_CKPT = MODELS_DIR / "anomaly_v2.pt"

# loaded at startup when the checkpoints exist
scorer = None
anomaly_detector = None

# HRV pushed by Component B lives here; mock is the demo fallback
hrv_store = StoredHRVProvider()
hrv_mock = MockHRVProvider()

# per-session stress results so /compare and /full-session can look back
session_scores: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # load whatever checkpoints exist; missing ones disable their endpoint
    global scorer, anomaly_detector
    if FUSION_CKPT.exists():
        from src.inference_fusion import StressScorer
        scorer = StressScorer(str(FUSION_CKPT))
        print(f"loaded fusion model: {FUSION_CKPT}")
    else:
        print(f"fusion checkpoint missing ({FUSION_CKPT}), /infer disabled")
    if ANOMALY_CKPT.exists():
        anomaly_detector = SessionAnomalyDetector(str(ANOMALY_CKPT))
        print(f"loaded anomaly model: {ANOMALY_CKPT}")
    else:
        print(f"anomaly checkpoint missing ({ANOMALY_CKPT}), /anomaly-check disabled")
    yield


app = FastAPI(title="CogniVoice Component D", version="2.0", lifespan=lifespan)


async def read_audio(file: UploadFile) -> np.ndarray:
    """Decode an uploaded audio file to 16 kHz mono float32."""
    raw = await file.read()
    try:
        audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
    except Exception:
        raise HTTPException(400, "could not decode audio file")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
    return audio


# ---------- health ----------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "layers": {
            "layer1_ambient": True,
            "layer2_fusion": scorer is not None,
            "layer3_comparison": True,
            "layer4_crossmodal": True,
            "layer5_anomaly": anomaly_detector is not None,
        },
    }


# ---------- layer 1 ----------

@app.post("/ambient-check")
async def ambient_check(file: UploadFile = File(...)):
    audio = await read_audio(file)
    return check_ambient(audio)


# ---------- layer 2 ----------

@app.post("/infer")
async def infer(file: UploadFile = File(...),
                session_id: str | None = None, phase: str = "pre"):
    if scorer is None:
        raise HTTPException(503, "fusion model not trained yet")
    audio = await read_audio(file)

    ambient = check_ambient(audio)
    if not ambient["ok"]:
        raise HTTPException(422, detail={"error": "audio rejected by layer 1",
                                         "reasons": ambient["reasons"]})

    result = scorer.score_array(audio)
    result["ambient"] = ambient["metrics"]

    # remember the score so later endpoints can use it
    sid = session_id or str(uuid.uuid4())
    session_scores.setdefault(sid, {})[phase] = result
    result["session_id"] = sid
    return result


# ---------- layer 3 ----------

class CompareRequest(BaseModel):
    session_id: str


@app.post("/compare")
def compare(req: CompareRequest):
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results for this session")
    return compare_scores(stored["pre"], stored["post"])


# ---------- layer 4 ----------

class HRVUpdate(BaseModel):
    session_id: str
    phase: str          # "pre" | "post"
    rmssd: float        # milliseconds, from Component B


@app.post("/session-update")
def session_update(update: HRVUpdate):
    if update.phase not in ("pre", "post"):
        raise HTTPException(400, "phase must be 'pre' or 'post'")
    hrv_store.push(update.session_id, update.phase, update.rmssd)
    return {"stored": True}


class CrossValidateRequest(BaseModel):
    session_id: str
    use_mock_hrv: bool = False   # demos without Component B


@app.post("/cross-validate")
def cross_validate(req: CrossValidateRequest):
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results for this session")

    provider = hrv_mock if req.use_mock_hrv else hrv_store
    hrv_pre = provider.get_rmssd(req.session_id, "pre")
    hrv_post = provider.get_rmssd(req.session_id, "post")
    if hrv_pre is None or hrv_post is None:
        raise HTTPException(404, "no HRV data for this session; Component B must "
                                 "call /session-update, or set use_mock_hrv")

    return validate_crossmodal(stored["pre"]["stress_score"],
                               stored["post"]["stress_score"],
                               hrv_pre, hrv_post)


# ---------- layer 5 ----------

class AnomalyRequest(BaseModel):
    user_id: str
    features: list[float]   # ANOMALY_FEATURES order, see config.py


@app.post("/anomaly-check")
def anomaly_check(req: AnomalyRequest):
    if anomaly_detector is None:
        raise HTTPException(503, "anomaly model not trained yet")
    return anomaly_detector.check(req.user_id, np.asarray(req.features))


# ---------- full session for the app / Component C ----------

class FullSessionRequest(BaseModel):
    session_id: str
    user_id: str = "default"
    use_mock_hrv: bool = False


@app.post("/full-session")
def full_session(req: FullSessionRequest):
    """One call the app makes after the post-session recording:
    comparison + cross-modal validation + anomaly check, combined."""
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results for this session")

    comparison = compare_scores(stored["pre"], stored["post"])

    crossmodal = None
    provider = hrv_mock if req.use_mock_hrv else hrv_store
    hrv_pre = provider.get_rmssd(req.session_id, "pre")
    hrv_post = provider.get_rmssd(req.session_id, "post")
    if hrv_pre is not None and hrv_post is not None:
        crossmodal = validate_crossmodal(stored["pre"]["stress_score"],
                                         stored["post"]["stress_score"],
                                         hrv_pre, hrv_post)

    anomaly = None
    if anomaly_detector is not None:
        features = [
            stored["pre"]["stress_score"], stored["post"]["stress_score"],
            comparison["delta"],
            stored["pre"]["confidence"], stored["post"]["confidence"],
            15.0,                                            # session_duration: from app later
            crossmodal["agreement"] if crossmodal else 0.75,
            abs(stored["pre"].get("arousal", 0) - stored["post"].get("arousal", 0)),
            stored["pre"].get("ambient", {}).get("rms", 0.02),
            float(len(session_scores)),                      # session_number proxy
            12.0,                                            # time_of_day: from app later
            1.0,                                             # days_since_last: from app later
        ]
        anomaly = anomaly_detector.check(req.user_id, np.asarray(features))

    # the compact payload Component C (Unity) consumes
    return {
        "stress_level": stored["post"]["stress_score"],
        "confidence": stored["post"]["confidence"],
        "comparison": comparison,
        "crossmodal": crossmodal,
        "anomaly": anomaly,
    }
