# AWS Lambda container image for the analysis endpoint only.
# Build from the repository root:
#   docker build -f deploy/lambda/Dockerfile -t agrof-vision-lambda .
FROM public.ecr.aws/lambda/python:3.13
COPY deploy/lambda/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
COPY agrof_vision/__init__.py agrof_vision/pipeline.py agrof_vision/lambda_handler.py ${LAMBDA_TASK_ROOT}/agrof_vision/
CMD ["agrof_vision.lambda_handler.handler"]
