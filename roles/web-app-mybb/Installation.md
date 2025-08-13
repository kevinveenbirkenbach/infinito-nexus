# Installation

## Multi Domain Installation
If you want to access your mybb over multiple domains, keep the following in mind:
- Set Cookie Domain to nothing
- Access mybb for installation via mybb.<PRIMARY_DOMAIN> 
- Set the Board Url to mybb.<PRIMARY_DOMAIN>

## Manual Installation of MyBB Plugins

This guide describes the process of manually installing MyBB plugins in your Docker-MyBB environment. This can be useful if you want to quickly test plugins or do not wish to execute the Ansible role.

### Steps for Manual Installation


1. **Prepare Plugin Files:**
   - Download the desired MyBB plugin zip files.

2. **Copy plugin to host:**
    - ```bash scp <plugin> administrator@<server>:/opt/docker/mybb/plugins```

3. **Unzip Plugin Files on the Host:**
   - Unzip the plugin zip files in the host's plugin directory:
     ```bash
     unzip /opt/docker/mybb/plugins/<plugin-file>.zip -d /opt/docker/mybb/plugins/
     ```
   - Replace `<plugin-file>.zip` with the name of the plugin zip file.
   - Repeat this step for each plugin.

4. **Access the Docker Container:**
   - Open a terminal or SSH session on the server where the Docker container is running.

5. **Copy Unzipped Plugin Files to the Container:**
   - Copy the unzipped plugin files from the host directory to the Docker container:
     ```bash
     docker compose cp /opt/docker/mybb/plugins/<unzipped-plugin-folder> application:/var/www/html/inc/plugins/
     ```
   - Replace `<unzipped-plugin-folder>` with the name of the unzipped plugin folder.

6. **Restart the Container:**
   - Execute the following command to restart the MyBB container:
     ```bash
     docker-compose -p mybb up -d --force-recreate
     ```
   - This ensures all changes take effect.

7. **Activate Plugins in the MyBB Admin Panel:**
   - Open the MyBB admin panel in your web browser.
   - Navigate to the plugin settings and activate the newly installed plugins.

### Important Notes

- Ensure you use the correct paths and filenames.
- Do not forget to regularly back up your MyBB database and files before making changes.
- If encountering issues, refer to the MyBB documentation or specific instructions from the plugin author.