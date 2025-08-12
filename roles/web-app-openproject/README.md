# OpenProject

## Description

Transform your project management with [OpenProject](https://www.openproject.org/), a vibrant and collaborative tool that brings clarity and energy to your planning, tracking, and team communication. Experience streamlined workflows and an innovative platform that propels your projects forward.

## Overview

Designed for simplicity, this role automates everything needed to run OpenProject in a containerized environment. It configures essential services such as the application itself, a PostgreSQL database, reverse proxy, and optional LDAP integration for identity management.

## Purpose

The purpose of this role is to reduce the complexity of setting up OpenProject with modern production‐ready defaults. By combining Docker Compose and Ansible automation, it enables a hands‐off setup for both small teams and larger internal infrastructures.

## Features

- **Work Package Management**:  
  Create, assign, track, and prioritize tasks and issues with customizable workflows that keep your project organized and on schedule.

- **Gantt Charts & Timelines**:  
  Visualize project schedules and dependencies using intuitive Gantt charts and timeline views, enabling effective planning and resource allocation.

- **Agile Boards & Scrum/Kanban Integration**:  
  Manage agile projects using Scrum or Kanban boards, track progress through sprints, and maintain a clear overview of work in progress.

- **Time Tracking & Cost Management**:  
  Record time spent on tasks to monitor productivity and generate detailed cost reports to manage budgets effectively.

- **Collaboration & Document Management**:  
  Facilitate team collaboration with built-in discussion forums, document sharing, and version control, ensuring all project documentation remains up to date.

- **Robust Reporting & Dashboards**:  
  Gain insights through comprehensive reporting features and customizable dashboards that help monitor project performance and key metrics.

- **Custom Plugins & Extensibility**:  
  Extend functionality with a wide variety of plugins and integrations, or create your own to tailor OpenProject to your unique workflow.

- **Role-Based Access Control & Security**:  
  Manage user permissions precisely to ensure that sensitive information and critical functions remain secure.


## Developer Notes

See the [Development.md](./Development.md) file for how to inspect and modify live settings inside the container, including full LDAP and SMTP configuration via the Rails console.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus NonCommercial License (CNCL)](https://s.infinito.nexus/license)
