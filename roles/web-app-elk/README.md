# ELK Stack

## Warning
For security reasons, this role is not recommended. If you prefer to keep your logs safe without relying on external servers, consider using an alternative tool.

## Overview
This Ansible role deploys and configures an [ELK Stack](https://en.wikipedia.org/wiki/Elastic_stack) (comprising [Elasticsearch](https://en.wikipedia.org/wiki/Elasticsearch), [Logstash](https://en.wikipedia.org/wiki/Elastic_stack), and [Kibana](https://en.wikipedia.org/wiki/Kibana)) using [Docker Compose](https://en.wikipedia.org/wiki/Docker_Compose). The ELK Stack is widely used for centralized log collection, analysis, and visualization of log and machine-generated data.

## Description
This role performs the following tasks:
- **Setup & Configuration:** Installs and configures the three main components—Elasticsearch, Logstash, and Kibana.
- **Template-Driven Adjustments:** Adapts configuration files through templates and variables.
- **Docker Integration:** Deploys the stack using Docker Compose, integrating it into your containerized environment.
- **Service Management:** Handles service restarts and updates through Ansible handlers.

## Purpose
The ELK Stack is primarily used for:
- **Centralized Log Management:** Consolidating logs from various systems into one location.
- **Real-Time Troubleshooting:** Quickly diagnosing issues through live log analysis.
- **Performance Monitoring:** Tracking system performance and identifying anomalies.
- **Security Analysis:** Detecting and investigating security incidents based on log data.

## Features
- **Centralized Log Management:** Collects and aggregates logs from disparate systems.
- **Real-Time Analysis:** Leverages Elasticsearch for fast data search and analytics.
- **Flexible Data Pipelines:** Processes and transforms log data with Logstash.
- **Interactive Visualization:** Creates dashboards and visual reports with Kibana.
- **Scalable & Extensible:** Easily integrates additional tools and custom configurations via templates.

## Credits 📝
Developed and maintained by **Kevin Veen-Birkenbach**.  
For more information, visit [www.veen.world](https://www.veen.world).  
Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code).  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)