# Runtime image for Bridgy Fed (Flask) with a build step that clones upstream
ARG PY_BASE="python:3.12-bookworm"
FROM ${PY_BASE} AS build

ARG BRIDGY_REPO_URL
ARG BRIDGY_REPO_REF

# System deps: git, build tools, curl for healthchecks, and gunicorn
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone --depth=1 --branch "${BRIDGY_REPO_REF}" "${BRIDGY_REPO_URL}" ./

# Python deps
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create oauth_dropins static symlink (upstream expects this)
RUN python - <<'PY'\n\
import oauth_dropins, pathlib, os\n\
target = pathlib.Path(oauth_dropins.__file__).parent / 'static'\n\
link = pathlib.Path('/app/oauth_dropins_static')\n\
try:\n\
    if link.exists() or link.is_symlink():\n\
        link.unlink()\n\
    os.symlink(str(target), str(link))\n\
except FileExistsError:\n\
    pass\n\
print('Symlinked oauth_dropins_static ->', target)\n\
PY

# Final stage
FROM ${PY_BASE}

ARG CONTAINER_PORT
ENV PORT=${CONTAINER_PORT:-8080}

WORKDIR /app
COPY --from=build /app /app

# Non-root good practice
RUN useradd -r -m -d /nonroot appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT}
# Upstream flask app entry: 'flask_app:app'
CMD ["sh", "-lc", "exec gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT} flask_app:app"]
