ARG DECIDIM_IMAGE
ARG DECIDIM_VERSION
FROM ${DECIDIM_IMAGE}:${DECIDIM_VERSION}

ARG DECIDIM_PATCH_SCRIPT_HOST_REL
ARG DECIDIM_PATCH_SCRIPT_DOCKER

# Add omniauth_openid_connect to Gemfile and install
RUN echo "gem 'omniauth_openid_connect'" >> /code/Gemfile && \
    cd /code && bundle install --quiet

# Copy and run the patch script
COPY ${DECIDIM_PATCH_SCRIPT_HOST_REL} ${DECIDIM_PATCH_SCRIPT_DOCKER}
RUN python3 ${DECIDIM_PATCH_SCRIPT_DOCKER}
