# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:alpine

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Disable development dependencies
ENV UV_NO_DEV=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=1000
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/bin/bash" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Sync dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the source code into the container.
COPY --chown=appuser:appuser . /app

# Sync again
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Switch back to the non-privileged user.
USER appuser

# Expose the port that the application listens on.
EXPOSE 7035

# Run the application
CMD ["uv", "run", "flask", "run"]