# AGROF Vision

A working OpenCV 5 crop-image capture and green-region segmentation pipeline for the OpenCV AI Competition.

## Run

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open http://127.0.0.1:8000. Upload a JPEG or PNG (4 MB maximum).

## Pipeline

Decode image → resize to maximum 1024-pixel edge → HSV green segmentation → morphological opening/closing → contour overlays. Separately measures lighting and Laplacian variance as a focus heuristic. Returns actual measured data and an annotated image. Images are not stored.

This is capture-quality analysis, not a disease classifier. Yellow/brown leaves, non-green crops, backgrounds and lighting can confuse the green heuristic. Thresholds need evaluation on a labeled dataset. Focus varies with resolution and texture. Decode limits are applied after image decoding; production must isolate processing and enforce resource limits.

## AWS

Includes a Lambda Function URL adapter and a Python 3.13 Lambda container Dockerfile. This has not been deployed to AWS. Configure IAM authentication and request limits; connect a secure backend proxy for browser access. Do not expose an unrestricted public endpoint. Follow the official container workflow: https://docs.aws.amazon.com/lambda/latest/dg/python-image.html

## Tests

```sh
.venv/bin/python test_vision.py
```

Checks synthetic leaf segmentation, invalid images, dark-image rejection and the Lambda adapter. These tests are not real-world accuracy evidence.

## Remaining submission work

AWS deployment and full browser-to-AWS test; labeled field-photo evaluation; robust crop/leaf segmentation; judge instructions, demo video, architecture diagram and technical report. MIT license.
