# AegisWatch AI Models — Documentation

This document records every AI model integrated into AegisWatch, including
license, hardware requirements, and rationale for selection.

---

## MODEL 1 — Primary Object Detector

| Field | Value |
|-------|-------|
| **Name** | YOLOv8n (nano) |
| **Hugging Face / Source** | Ultralytics (github.com/ultralytics/ultralytics), weights auto-downloaded from `github.com/ultralytics/assets` |
| **Local File** | `yolov8n.pt` (in project root) |
| **Model Type** | Single-stage anchor-free CNN object detector |
| **What it detects** | 80 COCO classes — person, car, motorcycle, backpack, handbag, suitcase, umbrella, laptop, cell phone, knife, scissors, etc. |
| **Expected Input** | BGR image (numpy array), any resolution — auto-resized to 640×640 |
| **Expected Output** | Bounding boxes [x1,y1,x2,y2], class label, confidence score, tracking ID (via ByteTrack) |
| **License** | AGPL-3.0 |
| **Academic Use** | ✅ Permitted — AGPL-3.0 allows use and modification for academic/research purposes; source code of modifications must be shared if distributed |
| **Hardware** | CPU: ~3–5 FPS at 640px. GPU (CUDA): 30+ FPS |
| **Approx. Size** | 6.5 MB |
| **Why Selected** | Fastest available model (6.5MB), already present in repo, industry-standard for CCTV, built-in ByteTrack multi-object tracker, well-documented |
| **Tracking** | ByteTrack (built into ultralytics 8.x) — provides persistent Track IDs across frames |

---

## MODEL 2 — Secondary / Backup Detector (Hugging Face)

| Field | Value |
|-------|-------|
| **Name** | DETR — DEtection TRansformer (resnet-50 backbone) |
| **Hugging Face ID** | `facebook/detr-resnet-50` |
| **Model Type** | Transformer-based end-to-end object detector |
| **What it detects** | 91 COCO classes — person, bicycle, car, backpack, handbag, laptop, cell phone, knife, etc. |
| **Expected Input** | PIL Image or BGR numpy array (auto-converted) |
| **Expected Output** | Bounding boxes, class labels, confidence scores |
| **License** | **Apache 2.0** ✅ — fully permissive for academic and commercial use |
| **Academic Use** | ✅ No restrictions |
| **Hardware** | CPU feasible (1–2 FPS); GPU recommended for video analysis |
| **Approx. Size** | ~166 MB (downloaded on first use, cached in `.cache/huggingface/`) |
| **Why Selected** | Apache 2.0 license (cleanest for academic demo), directly from Hugging Face `transformers`, demonstrates real HF integration, acceptable accuracy on CCTV classes |
| **HF URL** | https://huggingface.co/facebook/detr-resnet-50 |

---

## MODEL 3 — (Architecture Placeholder) Video Action Recognition

| Field | Value |
|-------|-------|
| **Name** | VideoMAE-Base |
| **Hugging Face ID** | `MCG-NJU/videomae-base` |
| **Model Type** | Masked Autoencoder for Video Understanding |
| **Purpose** | Video-level action/violence recognition |
| **License** | CC-BY-NC 4.0 — non-commercial only |
| **Academic Use** | ✅ Permitted for non-commercial academic projects |
| **Status** | **Architecture hook created** — model interface defined in `models/base_model.py`. Full integration requires GPU with ≥8GB VRAM for real-time video classification. Currently disabled for CPU-only demo. Activate by setting `ENABLE_VIDEO_CLASSIFIER=true` in `.env` |
| **Why Documented** | Required by system design; disabled by default to keep demo feasible on a standard laptop |

---

## Behavior Analysis (Rule-Based, Not ML)

The following behaviors are detected using **deterministic rules** applied to
the output of the object detector and tracker. These are **not ML models**.

| Behavior | Method | Requires |
|----------|--------|----------|
| Loitering | Track history spread < threshold for N frames | Person track + history |
| Suspicious movement | Direction change frequency > threshold | Person track + history |
| Fight/Violence | 2+ persons very close + high movement | 2+ person tracks |
| Abandoned object | Object visible for >25s with no nearby person | Object track + absence of person |
| Weapon detected | Knife/scissors class detection | Object detector output |

---

## Risk Engine

Scores are computed by the `_risk_score()` function in `ai_service.py`:

| Event | Base Score | Severity |
|-------|-----------|---------|
| LOITERING | 45 | MEDIUM |
| SUSPICIOUS_MOVEMENT | 55 | MEDIUM |
| ABANDONED_OBJECT | 65 | HIGH |
| FIGHT | 85 | CRITICAL |
| WEAPON_DETECTED | 92 | CRITICAL |

Final score = base ± confidence factor ± person count adjustment, clamped to [0,100].

---

## Privacy Policy

- No facial recognition is used or implemented.
- All persons are tracked by anonymous numeric IDs (e.g., `Person #14`).
- No personally identifiable information is stored.
- All AI outputs are probabilistic — human review is required before action.
