# Intel Driver

## Description

This Ansible role installs Intel media drivers on Pacman-based Linux distributions (e.g., Arch Linux), ensuring the `intel-media-driver` package is present and up-to-date.

## Overview

The `drv-intel` role uses the `community.general.pacman` module to:

1. Update the package cache  
2. Install or upgrade the `intel-media-driver` package  
3. Verify the driver installation for media pipelines  

## Features

* Idempotent installation of Intel media drivers  
* Automatic Pacman cache update  
* Support for all Pacman-based distributions  

## Further Resources

* [Intel Media Driver upstream documentation](https://01.org/intel-media-sdk)
