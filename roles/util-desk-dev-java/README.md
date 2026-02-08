# Java Development Utilities

## Description

This Ansible role sets up a complete environment for Java developers on Arch Linux. It ensures that the Java Development Kit (JDK) is installed and ready to use, building on a base developer environment to support software engineers, students, and professionals working with Java.

Learn more about [Java on Wikipedia](https://en.wikipedia.org/wiki/Java_(programming_language)), [OpenJDK](https://openjdk.org/), and [Java Development on the Arch Wiki](https://wiki.archlinux.org/title/Java).

## Overview

Part of the Infinito.Nexus persona system, this role adds Java-specific tools and configurations on top of a general developer setup. It focuses on providing the foundation needed to develop, build, and run Java applications.

## Purpose

The role is ideal for users who regularly work with Java, whether for backend systems, Android development, or academic projects. It ensures that the necessary runtime and development tools are always present and correctly configured.

## Features

- **Installs Java Development Kit (JDK):** Ensures the system has Java ready to run and compile applications.
- **Persona Integration:** Extends the `util-desk-dev-core` role with Java-specific capabilities.
- **Ready for IDEs & Build Tools:** Prepares the base for tools like Maven, Gradle, or IntelliJ IDEA.

## Customization

You can extend this role to include more Java tooling such as:
- Maven (`maven`)
- Gradle (`gradle`)
- IDEs (like IntelliJ or Eclipse)
Just add packages or tasks based on your workflow.

## Credits 📝

Developed and maintained by **Kevin Veen-Birkenbach**.  
Learn more at [www.veen.world](https://www.veen.world)

Part of the [Infinito.Nexus Project](https://s.infinito.nexus/code)  
License: [Infinito.Nexus Community License (Non-Commercial)](https://s.infinito.nexus/license)