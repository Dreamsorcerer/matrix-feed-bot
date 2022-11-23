FROM python:3.9.15-slim as python
WORKDIR /app

FROM python as poetry
COPY . .
RUN pip install poetry && poetry install --no-interaction --no-ansi -vvv

FROM python as runtime
COPY --from=poetry /app /app
CMD [ "python", "./matrix_rss_bridge/main.py" ]