FROM python:3.8-alpine

COPY requirements.txt /app/requirements.txt
WORKDIR /app

RUN BUILD_DEPS='pkgconfig freetype-dev musl-dev gcc g++' \
    && apk update \
    && apk add $BUILD_DEPS \
    && pip install -r requirements.txt \
    && apk del $BUILD_DEPS

COPY . /app

CMD ["python", "webserver.py"]
