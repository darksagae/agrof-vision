# AGROF Vision

**Check a leaf in seconds.** Snap one leaf; AGROF Vision checks the photo, outlines the leaf and measures yellowing, browning and spots. It uses explainable OpenCV 5 computer vision, not a black box.

Built for the OpenCV AI Competition.

## What you get from one photo

- **Capture checks:** lighting, sharpness, glare, framing and resolution, each with a pass/check/retake status and a plain-language fix.
- **Leaf segmentation:** the leaf outlined on the photo, even on busy soil backgrounds.
- **Tissue map:** each leaf pixel classed as healthy green, yellowing, brown/dark or other.
- **Spot detection:** compact discoloured patches are boxed and counted. Broad yellowing is reported separately so it isn't miscounted as spots.
- **Findings:** a condition summary, a discolouration index and an honest disclaimer.
- **Downloads:** a JSON report and the annotated image.
- **Session history:** to compare leaves (in memory only).

Photos are processed in memory and never stored. Phones can capture straight from the camera, and large photos are resized on the device before upload.

## Pipeline

| Stage | What happens | OpenCV |
| --- | --- | --- |
| 1. Normalise | Decode JPEG, PNG or WebP with EXIF orientation; cap at 10 MB and 40 MP; resize to 1024 px | `imdecode`, `resize(INTER_AREA)` |
| 2. Capture quality | LAB lightness, specular glare (high V, low S), Laplacian variance on the leaf crop at a fixed 512 px scale, coverage, resolution | `cvtColor`, `Laplacian` |
| 3. Leaf segmentation | Excess-green index `2g − r − b` with an Otsu threshold and a hue gate. Yellow tissue connected to green is kept, components must be plant-sized and mostly green, then closing and hole filling | `threshold(OTSU)`, `connectedComponentsWithStats`, `morphologyEx`, `findContours` |
| 4. Tissue classes | HSV rules inside the leaf: healthy, yellowing, brown/dark, other | `COLOR_BGR2HSV` |
| 5. Spots | Open, then close to rejoin patches split by veins; keep components between 0.02% and 3% of leaf area | `connectedComponentsWithStats` |

All thresholds live in [`agrof_vision/pipeline.py`](agrof_vision/pipeline.py).

## Run it

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and Node.js 20+.

```sh
uv sync
(cd web && npm ci && npm run build)
uv run python -m agrof_vision        # http://127.0.0.1:8000
```

For UI development with hot reload, run the API as above and `cd web && npm run dev` (Vite proxies `/api` to port 8000).

Environment variables: `HOST`, `PORT`, `AGROF_MAX_CONCURRENT` (simultaneous analyses, default 4) and `AGROF_WEB_DIST`.

## API

`POST /api/analyze` with a multipart field `image` returns the full analysis as JSON. Errors return `{ "error": "…" }` with status 413 or 422.

`GET /api/health` reports versions. Interactive docs are at `/api/docs`.

## Test

```sh
uv run pytest           # 21 tests: segmentation IoU, spot counts, yellowing, quality gates, bad files, API, Lambda
uv run ruff check . && uv run ruff format --check .
(cd web && npm run build)   # includes the TypeScript check
```

Tests use procedurally generated leaves ([`agrof_vision/synthetic.py`](agrof_vision/synthetic.py)) with known ground truth: leaf IoU is above 0.95 on soil and paper backgrounds, and spot counts are exact. `scripts/make_samples.py` writes the demo samples in `web/public/samples/`.

## Deploy

- **Container:** `docker build -t agrof-vision .` then `docker run -p 8000:8000 agrof-vision`.
- **AWS Lambda:** `docker build -f deploy/lambda/Dockerfile -t agrof-vision-lambda .` builds the analysis endpoint. It accepts either a raw image body (`Content-Type: image/jpeg`) or JSON `{"image": "<base64>"}` via a Function URL or API Gateway. Turn on IAM auth or an authorizer; do not expose an open endpoint.

Neither image has been deployed or built in CI yet.

## Limits

This is a screening aid, not a diagnosis. Yellowing and spots have many causes (disease, pests, nutrients, water stress, sun scorch, ageing).

The colour rules can be fooled by purple or variegated leaves, tinted light and green backgrounds such as grass. Mostly-brown leaves may not be detected.

Thresholds were tuned on synthetic leaves. They need evaluation on labelled field photos (e.g. PlantVillage or local data) before agronomic use.

## License

MIT
