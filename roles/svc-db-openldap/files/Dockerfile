FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    slapd slapd-contrib ldap-utils ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

# Ensure runtime dirs exist
RUN mkdir -p /run/slapd /var/lib/ldap /etc/ldap/slapd.d \
 && chown -R openldap:openldap /run/slapd /var/lib/ldap /etc/ldap/slapd.d

# Bootstrap entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Healthcheck script (kept tiny & deterministic)
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

EXPOSE 389

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=12 \
  CMD ["/healthcheck.sh"]

ENTRYPOINT ["/usr/bin/tini","--","/entrypoint.sh"]
