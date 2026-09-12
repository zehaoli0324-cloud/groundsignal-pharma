# Override PYTHON_IMAGE with a verified digest when freezing a release image.
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY scripts/ /app/scripts/
COPY tests/medical_dialogue_bench/ /app/tests/medical_dialogue_bench/
COPY benchmark/medical-dialogue-v1/ /app/benchmark/medical-dialogue-v1/
RUN mkdir -p /output && chown 10001:10001 /output
USER 10001:10001
ENTRYPOINT ["python", "-m", "scripts.medical_dialogue_bench"]
CMD ["validate"]
