ARG XWIKI_IMAGE
ARG XWIKI_VERSION
FROM ${XWIKI_IMAGE}:${XWIKI_VERSION}
ARG XWIKI_SUPERADMIN_PASSWORD
RUN printf '%s\n' \
  'xwiki.superadmin=1' \
  "xwiki.superadminpassword=${XWIKI_SUPERADMIN_PASSWORD}" \
  >> /usr/local/tomcat/webapps/ROOT/WEB-INF/xwiki.cfg
