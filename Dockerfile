FROM public.ecr.aws/lambda/python:3.14

COPY backend/requirements.lambda.txt ${LAMBDA_TASK_ROOT}/requirements.lambda.txt
RUN python -m pip install --no-cache-dir \
    --requirement ${LAMBDA_TASK_ROOT}/requirements.lambda.txt \
    --target ${LAMBDA_TASK_ROOT}

COPY backend ${LAMBDA_TASK_ROOT}/backend

CMD ["backend.ingestion.lambda_handler.handler"]
