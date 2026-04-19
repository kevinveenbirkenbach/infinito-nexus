ARG DECIDIM_IMAGE
ARG DECIDIM_VERSION
FROM ${DECIDIM_IMAGE}:${DECIDIM_VERSION}

# Add omniauth_openid_connect to Gemfile and install
RUN echo "gem 'omniauth_openid_connect'" >> /code/Gemfile && \
    cd /code && bundle install --quiet

# Copy and run the patch script
COPY patch_decidim.py /tmp/patch_decidim.py
RUN python3 /tmp/patch_decidim.py
