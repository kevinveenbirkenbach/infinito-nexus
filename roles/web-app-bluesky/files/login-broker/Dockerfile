# Bluesky login-broker image. Pure Node, no npm dependencies — the
# broker uses only Node's stdlib (`node:http`, `node:https`,
# `node:crypto`) so the image stays minimal and rebuild-fast and the
# attack surface is small.
FROM node:22-alpine

RUN apk add --no-cache ca-certificates && update-ca-certificates

WORKDIR /app

COPY package.json server.js ./

USER node
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O - http://127.0.0.1:8080/healthz || exit 1

CMD ["node", "server.js"]
