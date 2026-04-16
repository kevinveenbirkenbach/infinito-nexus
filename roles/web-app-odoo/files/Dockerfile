ARG ODOO_IMAGE
ARG ODOO_VERSION

FROM ${ODOO_IMAGE}:${ODOO_VERSION}

# Install additional Python dependencies for OIDC support
USER root

# Install system dependencies for python3-saml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages \
    python3-saml>=1.15.0 \
    oauthlib>=3.2.0 \
    requests-oauthlib>=1.3.0 \
    PyJWT>=2.8.0

# Create log directory
RUN mkdir -p /var/log/odoo && \
    chown -R odoo:odoo /var/log/odoo

USER odoo
