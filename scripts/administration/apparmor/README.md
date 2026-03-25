# AppArmor Administration 🛡️

This directory contains the AppArmor-facing maintenance layer for the local and CI development experience.

The focus here is not feature work, but control and safety: development workflows sometimes need a softer security posture, while cleanup paths must leave the system in a predictable state again. That makes this area less about convenience and more about trust, reversibility, and clear operational boundaries. 🔒

When changing anything in this area, prefer behavior that is:

- explicit rather than magical
- reversible rather than destructive
- capability-aware rather than assumption-driven
- quiet on unsupported systems, but loud when real integrity risks appear

In short: these files exist to help development move quickly without teaching the project to be careless around host security controls. ⚙️
