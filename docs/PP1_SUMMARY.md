# PP1 Summary — what was built and learned

Record of the PP1 stage so nothing is forgotten. The PP1 code lives at
`/Volumes/KINGSTON/voice_stress_pipeline` (kept as reference, untouched).

## What PP1 delivered

- Full 5-layer pipeline behind a FastAPI server (v4.0) plus a React UI
  (cognify-ui, 5-step session flow with live waveform).
- Datasets: RAVDESS + CREMA-D + TESS (~11k acted English clips), unified
  metadata with speaker-independent splits, calm-class augmentation
  (192 -> 1920 samples).

## The model ablation (Layer 2)

| Model | Approach | Result |
|---|---|---|
| 1 | wav2vec2-base embeddings + custom MLP | 72.5% (acted test set) |
| 2 | emotion2vec_base embeddings + custom MLP | 84.7% (acted test set), failed on real voices |
| 3 | emotion2vec regression variants | similar failure on real voices |
| 4 | emotion2vec_base_finetuned direct 9-class output + hand-written valence/arousal weight table | generalised best, shipped in PP1 API |
| - | XLSR-53 fine-tune attempt | underperformed emotion encoders, abandoned |

## Key findings (these motivate the PP2 design)

1. Emotion-pretrained encoders beat ASR-pretrained encoders for stress
   (84.7% vs 72.5%). Keep emotion2vec, drop XLSR.
2. High acted-set accuracy did not transfer to real voices: the
   acted-speech domain gap, not the encoder, was the bottleneck.
   PP2 therefore trains on naturalistic data (MELD, CMU-MOSEI, later
   MSP-Podcast/MuSE).
3. Model 4 worked but contained zero trained parameters of ours: the
   emotion-to-stress mapping was a lookup table. Panel feedback:
   directly using a pretrained model is not enough, an enhancement must
   be built. PP2 answer: trained gated fusion + learned V/A regression head.

## Other PP1 pieces and their PP2 fate

| PP1 piece | PP2 decision |
|---|---|
| Layer 1 ambient check (DSP rules) | rebuilt clean, same idea |
| Layer 3 pre/post comparison | rebuilt clean, add reliability band |
| Layer 4 cross-modal (rich validate_crossmodal existed but was never wired into the API) | wired in from day one this time |
| Layer 5 autoencoder (7 features, global mean+3sigma threshold, simulated training data) | extended to 12 features, per-user thresholds, severity codes |
| Two api_server files (api_server.py and api_server_final_fixed.py) | one api_server.py only |
| React UI | ported once the new API is stable |
