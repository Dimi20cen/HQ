FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY tools /app/tools
RUN set -eux; \
    find /app/tools -mindepth 2 -maxdepth 2 -name requirements.txt -print0 | xargs -0 -r -n1 pip install -r

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "controller.controller_main:app", "--host", "0.0.0.0", "--port", "8000"]
