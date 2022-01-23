FROM python:3.7-slim as builder

RUN BUILD_DEPS='gcc libc-dev libmariadb-dev-compat git' \
    && apt-get update \
    && apt-get install -y --no-install-recommends $BUILD_DEPS

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-warn-script-location --prefix /opt/local -r requirements.txt
COPY . /app
RUN bash update_about.bash



FROM python:3.7-slim as base

RUN RUN_DEPS='libmariadb3' \
    && apt-get update \
    && apt-get install -y --no-install-recommends $RUN_DEPS

WORKDIR /app
COPY --from=builder /app /app
COPY --from=builder /opt/local /opt/local

ENV PATH=/opt/local/bin:$PATH PYTHONPATH=/opt/local/lib/python3.7/site-packages



FROM base as probe
CMD ["python", "probe.py", "-f"]



FROM base as collector
CMD ["bash", "start_collector.bash"]



FROM base as web
CMD ["gunicorn", "pingweb.wsgi:application", "--bind", "0.0.0.0:8000", "-w", "4"]


FROM base as web-dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:5000"]
