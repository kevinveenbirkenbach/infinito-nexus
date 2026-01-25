# Ansible Collection Requirements

This directory contains Ansible collection requirement files used by the installation logic.

## Overview

- `requirements.galaxy.yml`  
  Primary source using **Ansible Galaxy**.

- `requirements.git.yml`  
  **Git-based fallback** used when Galaxy is unavailable or unstable.

The selection and retry logic is implemented in  
`scripts/install/ansible.sh`.
