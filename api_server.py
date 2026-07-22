"""Component D API server - the single entry point for every client.

The mobile app / VR headset / teammates' components only ever talk to
these endpoints. All five layers are wired here. Missing model
checkpoints disable their endpoint with a clean 503 (never a crash),
so the system runs even before training is complete.

Run (you will do this manually):
  .venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8001

Port 8001, not 8000: 8000 is a common clash point with other local dev
servers, and on macOS a process bound specifically to 127.0.0.1 silently
wins loopback traffic over a 0.0.0.0 bind - so a clash there fails
invisibly (a different app answers) instead of a loud "port in use"
error. This exact thing happened during development of this component.
"""

import io
import uuid
from contextlib import asynccontextmanager

import librosa
import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import MODELS_DIR, SAMPLE_RATE
from src.layer1_quality import check_quality
from src.layer3_compare import compare_scores
from src.layer4_crossmodal import (MockHRVProvider, StoredHRVProvider,
                                   validate_crossmodal)
from src.layer5_anomaly import SessionAnomalyDetector

# Trained checkpoints (produced by the training scripts).
FUSION_CKPT = MODELS_DIR / "fusion_v2.pt"
ANOMALY_CKPT = MODELS_DIR / "anomaly_v2.pt"

# Populated at startup if the checkpoints exist.
scorer = None
anomaly_detector = None

# HRV pushed by Component B lives here; the mock serves solo demos.
hrv_store = StoredHRVProvider()
hrv_mock = MockHRVProvider()

# Per-session Layer 2 results, so /compare and /full-session can look back.
# In-memory for now; a database replaces this in production.
session_scores: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load whatever trained models exist, once, at server start."""
    global scorer, anomaly_detector
    if FUSION_CKPT.exists():
        from src.layer2_inference import StressScorer
        scorer = StressScorer(str(FUSION_CKPT))
        print(f"loaded fusion model: {FUSION_CKPT}")
    else:
        print(f"fusion checkpoint missing ({FUSION_CKPT}) - /infer disabled")
    if ANOMALY_CKPT.exists():
        anomaly_detector = SessionAnomalyDetector(str(ANOMALY_CKPT))
        print(f"loaded anomaly model: {ANOMALY_CKPT}")
    else:
        print(f"anomaly checkpoint missing ({ANOMALY_CKPT}) - "
              f"/anomaly-check disabled")
    yield


app = FastAPI(title="CogniVoice Component D", version="2.0",
              lifespan=lifespan)

# The frontend (Vite dev server) and this API run on different ports,
# which browsers treat as different origins - without this, every fetch
# from the UI fails silently with a CORS error, even though curl/Postman
# work fine (they don't enforce CORS). Wide open here because this is a
# research demo on localhost; a real deployment should replace "*" with
# the mobile app's / hosted demo site's exact origin(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def read_audio(file: UploadFile) -> np.ndarray:
    """Decode any uploaded audio to 16 kHz mono float32."""
    raw = await file.read()
    try:
        audio, sr = sf.read(io.BytesIO(raw), dtype="float32")
    except Exception:
        raise HTTPException(400, "could not decode audio file")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)          # stereo -> mono
    if sr != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
    return audio


# ------------------------------------------------------------ health
@app.get("/health")
def health():
    return {
        "status": "ok",
        "layers": {
            "layer1_quality": True,
            "layer2_fusion": scorer is not None,
            "layer3_compare": True,
            "layer4_crossmodal": True,
            "layer5_anomaly": anomaly_detector is not None,
        },
    }


# ----------------------------------------------------------- layer 1
@app.post("/ambient-check")
async def ambient_check(file: UploadFile = File(...)):
    """Standalone quality check - the app calls this while recording to
    warn the user early about a bad environment."""
    audio = await read_audio(file)
    return check_quality(audio)


# ----------------------------------------------------------- layer 2
@app.post("/infer")
async def infer(file: UploadFile = File(...),
                session_id: str | None = None, phase: str = "pre"):
    """Audio -> stress score. Layer 1 gates the input first."""
    if scorer is None:
        raise HTTPException(503, "fusion model not trained yet")
    audio = await read_audio(file)

    quality = check_quality(audio)
    if not quality["ok"]:
        # 422 tells the app: recording unusable, ask the user to retry.
        raise HTTPException(422, detail={"error": "audio rejected by layer 1",
                                         "reasons": quality["reasons"]})

    result = scorer.score_array(audio)
    result["quality"] = quality["metrics"]

    # Remember this score so /compare and /full-session can use it.
    sid = session_id or str(uuid.uuid4())
    session_scores.setdefault(sid, {})[phase] = result
    result["session_id"] = sid
    return result


# ----------------------------------------------------------- layer 3
class CompareRequest(BaseModel):
    session_id: str


@app.post("/compare")
def compare(req: CompareRequest):
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results "
                                 "for this session")
    return compare_scores(stored["pre"], stored["post"])


# ----------------------------------------------------------- layer 4
class HRVUpdate(BaseModel):
    """The contract with Component B: they POST this after each phase."""
    session_id: str
    phase: str      # "pre" | "post"
    rmssd: float    # milliseconds


@app.post("/session-update")
def session_update(update: HRVUpdate):
    if update.phase not in ("pre", "post"):
        raise HTTPException(400, "phase must be 'pre' or 'post'")
    hrv_store.push(update.session_id, update.phase, update.rmssd)
    return {"stored": True}


class CrossValidateRequest(BaseModel):
    session_id: str
    use_mock_hrv: bool = False   # demos without Component B connected


@app.post("/cross-validate")
def cross_validate(req: CrossValidateRequest):
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results "
                                 "for this session")

    provider = hrv_mock if req.use_mock_hrv else hrv_store
    hrv_pre = provider.get_rmssd(req.session_id, "pre")
    hrv_post = provider.get_rmssd(req.session_id, "post")
    if hrv_pre is None or hrv_post is None:
        raise HTTPException(404, "no HRV for this session; Component B must "
                                 "call /session-update, or set use_mock_hrv")

    return validate_crossmodal(stored["pre"]["stress_score"],
                               stored["post"]["stress_score"],
                               hrv_pre, hrv_post)


# ----------------------------------------------------------- layer 5
class AnomalyRequest(BaseModel):
    user_id: str
    features: list[float]   # ANOMALY_FEATURES order - see config.py


@app.post("/anomaly-check")
def anomaly_check(req: AnomalyRequest):
    if anomaly_detector is None:
        raise HTTPException(503, "anomaly model not trained yet")
    return anomaly_detector.check(req.user_id, np.asarray(req.features))


# ------------------------------------- full session (for Component C)
class FullSessionRequest(BaseModel):
    session_id: str
    user_id: str = "default"
    use_mock_hrv: bool = False


@app.post("/full-session")
def full_session(req: FullSessionRequest):
    """The one call the app makes after the post-session recording:
    comparison + cross-modal + anomaly, combined into the payload
    Component C (Unity) consumes."""
    stored = session_scores.get(req.session_id, {})
    if "pre" not in stored or "post" not in stored:
        raise HTTPException(404, "need both pre and post /infer results "
                                 "for this session")

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
        # Session summary in ANOMALY_FEATURES order. Three values marked
        # "from app later" use defaults until the app supplies them.
        features = [
            stored["pre"]["stress_score"], stored["post"]["stress_score"],
            comparison["delta"],
            stored["pre"]["confidence"], stored["post"]["confidence"],
            15.0,                                          # session_duration
            crossmodal["agreement"] if crossmodal else 0.75,
            abs(stored["pre"].get("arousal", 0)
                - stored["post"].get("arousal", 0)),       # acoustic_variance
            stored["pre"].get("quality", {}).get("rms", 0.02),
            float(len(session_scores)),                    # session_number
            12.0,                                          # time_of_day
            1.0,                                           # days_since_last
        ]
        anomaly = anomaly_detector.check(req.user_id, np.asarray(features))

    return {
        "stress_level": stored["post"]["stress_score"],
        "confidence": stored["post"]["confidence"],
        "comparison": comparison,
        "crossmodal": crossmodal,
        "anomaly": anomaly,
    }
