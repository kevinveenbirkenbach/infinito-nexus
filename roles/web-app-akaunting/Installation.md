# Installation Guide

1. **Navigate to the Docker Compose Directory**  
   Change into the directory where the Docker Compose files reside.
   ```bash
   cd {{ PATH_DOCKER_COMPOSE_INSTANCES }}akaunting/
   ```

2. **Set Environment Variables**  
   Ensure timeouts are increased to handle long operations:
   ```bash
   export COMPOSE_HTTP_TIMEOUT=600
   export DOCKER_CLIENT_TIMEOUT=600
   ```

3. **Start Akaunting Service**  
   Run the setup command with the `AKAUNTING_SETUP` variable:
   ```bash
   AKAUNTING_SETUP=true docker-compose -p akaunting up -d
   ```

4. **Finalizing Setup**  
   After verifying that the web interface works, restart services:
   ```bash
   docker-compose down
   docker-compose -p akaunting up -d
   ```

For further details, visit the [Akaunting Documentation](https://akaunting.com/) and the [Akaunting GitHub Repository](https://github.com/akaunting/docker).