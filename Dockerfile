FROM python:3.7-slim as builder

RUN BUILD_DEPS='gcc libc-dev libmariadb-dev-compat' \
    && apt-get update \
    && apt-get install -y --no-install-recommends $BUILD_DEPS

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-warn-script-location --prefix /app/local -r requirements.txt
COPY . /app



FROM python:3.7-slim as base

RUN RUN_DEPS='libmariadb3' \
    && apt-get update \
    && apt-get install -y --no-install-recommends $RUN_DEPS

WORKDIR /app
COPY --from=builder /app /app

ENV PATH=/app/local/bin:$PATH PYTHONPATH=/app/local/lib/python3.7/site-packages



FROM base as probe
CMD ["python", "probe.py", "-f"]



FROM base as collector
CMD ["bash", "start_collector.bash"]



FROM base as web
CMD ["python", "webserver.py"]
