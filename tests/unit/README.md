# Unit Tests

This directory contains unit tests for various custom components in the project, such as the custom lookup plugin `docker_cards` used in the `web-app-dashboard` role.

## Overview

The unit tests are written using Python’s built-in `unittest` framework. They are designed to verify that your custom logic works as expected—such as extracting metadata from role files—without needing to run the entire playbook.

## Running the Tests

You can run the tests using one of the following methods:

1. **Using Unittest Discovery:**

   From the project's root directory, run:

   ```bash
   python -m unittest discover -s tests/unit
   ```

   This command will discover and execute all test files within the `tests/unit` directory.

2. **Running a Specific Test File:**

   If you want to run only the Docker cards test, execute:

   ```bash
   python tests/unit/test_docker_cards.py
   ```

## How It Works

- **Setup:**  
  The test script creates a temporary directory to simulate your roles folder. It then creates a sample role (`web-app-dashboard`) with a `README.md` file (containing a header for the title) and a `meta/main.yml` file (with the required metadata).

- **Execution:**  
  Dummy variable values for `domains` and `applications` are provided (these are the variables the lookup plugin expects). The lookup plugin is then run, which processes the sample role and returns the card information.

- **Verification:**  
  The test uses assertions to ensure that the output contains the expected title, description, icon information, constructed URL, and the correct iframe flag.

- **Cleanup:**  
  After the test completes, the temporary directory is removed, ensuring that no test artifacts remain.

## Requirements

- Python 3.6 or newer is recommended.
- All necessary dependencies for your project should be installed.

These tests help ensure that your custom code is reliable and behaves as expected, and they can be easily integrated into a Continuous Integration (CI) pipeline.

Happy testing!