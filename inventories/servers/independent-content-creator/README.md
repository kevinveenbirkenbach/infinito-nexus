# Independent Content Creator

## Purpose

An independent creator stack for publishing, video, audio, analytics, and community without platform lock-in.

## Target Audience

Independent creators, small studios, and community-driven media teams who want full control over content and audience.

## Included Components

This bundle activates the following Infinito.Nexus roles:

- web-app-wordpress
- web-app-peertube
- web-app-funkwhale
- web-app-matomo
- web-app-matrix
- svc-prx-openresty

## Notes

- This is a skeleton bundle: it activates roles but does not set application-specific configuration values.
- All services are expected to be exposed behind a reverse proxy role where applicable.
- Authentication can be unified via IAM roles depending on the included components.
