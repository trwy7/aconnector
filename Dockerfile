# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

FROM python:3.14.3-slim as base
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

# Disable development dependencies
ENV UV_NO_DEV=1

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# TODO: maybe cache uv better

# Copy the source code into the container.
COPY --chown=appuser:appuser . /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Switch to the non-privileged user to run the application.
USER appuser

# Force temp cache from now on
ENV UV_CACHE_DIR=/tmp/.uv_cache

# Expose the port that the application listens on.
EXPOSE 7035

# Run the application.
CMD /app/.venv/bin/gunicorn app:app --bind=0.0.0.0:7035
