# AegisWatch — License Audit

All external dependencies, models, and code are documented below.

---

## AI Models

| Component | License | Source | Notes |
|-----------|---------|--------|-------|
| YOLOv8n | AGPL-3.0 | github.com/ultralytics/ultralytics | Academic use OK; modifications must be open-sourced if distributed |
| facebook/detr-resnet-50 | **Apache 2.0** | huggingface.co/facebook/detr-resnet-50 | Fully permissive — no restrictions |
| MCG-NJU/videomae-base | CC-BY-NC 4.0 | huggingface.co/MCG-NJU/videomae-base | Non-commercial academic use OK; disabled by default |

---

## Python Libraries

| Library | License | Usage |
|---------|---------|-------|
| FastAPI | MIT | Backend web framework |
| Uvicorn | BSD | ASGI server |
| SQLAlchemy | MIT | ORM / database access |
| aiosqlite | MIT | Async SQLite driver |
| python-jose | MIT | JWT authentication |
| passlib | BSD | Password hashing |
| ultralytics | AGPL-3.0 | YOLOv8 model runner |
| opencv-python | Apache 2.0 | Image/video processing |
| numpy | BSD | Numerical arrays |
| Pillow | HPND | Image format handling |
| torch | BSD | PyTorch (required by ultralytics + transformers) |
| torchvision | BSD | Vision utilities |
| transformers | Apache 2.0 | Hugging Face Transformers (DETR) |
| httpx | BSD | Async HTTP client |
| requests | Apache 2.0 | HTTP client |
| python-dotenv | BSD | Environment variable loading |
| pydantic | MIT | Data validation |

---

## Original Repository

| Item | Details |
|------|---------|
| **Original Repo** | https://github.com/Rishichamp/AegisEdge-SmartSurveillance |
| **Original License** | MIT (see LICENSE file in project root — preserved unmodified) |
| **Attribution** | Original code by Rishichamp. Modified and extended for this project. |

The original MIT license is preserved in the `LICENSE` file at the project root.
All modifications and additions are documented in `README.md`.

---

## Frontend Libraries (CDN)

| Library | License | Usage |
|---------|---------|-------|
| Leaflet.js | BSD | Map display (OpenStreetMap) |
| Chart.js | MIT | Analytics charts |
| OpenStreetMap tiles | ODbL | Map tiles |

---

## Compliance Summary

| Requirement | Status |
|-------------|--------|
| No facial recognition | ✅ |
| No real police API | ✅ |
| No paid cloud required | ✅ |
| Licenses checked | ✅ |
| AGPL-3.0 compliance (source available) | ✅ (this is the source) |
| Apache 2.0 compliance | ✅ (no action required) |
| Original license preserved | ✅ |
