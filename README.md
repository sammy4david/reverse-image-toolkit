# Reverse Image Toolkit v1.1.0

A Python-based, multi-engine reverse image search toolkit for Termux on Android and standard Linux.

It supports JSON reporting, HTML report generation, thumbnail downloading and a centrally managed local PHP server.

## Features

- Five integrated search engines:
  - Yandex
  - Baidu
  - AnimeTrace
  - IQDB
  - TinEye
- Individual engine selection or searches across all five engines.
- JSON search reports.
- Standalone HTML report generation.
- Local thumbnail downloading.
- Centrally managed PHP server.
- Isolated Python virtual environment.
- Installation and uninstallation scripts.

## Requirements

### Termux (Android)

Install the required packages:

```bash
pkg update && pkg upgrade
pkg install python php
termux-setup-storage
```

### Install from the source package

Extract the toolkit ZIP archive, enter its directory, and run:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer automatically:

- Detects Termux or standard Linux.
- Creates an isolated Python virtual environment.
- Installs the required Python dependencies.
- Installs the four toolkit commands.
- Preserves backups of existing launchers before replacing them.

## Available Commands

**Command**                              **Purpose**  
reverse-image                        Search images using supported engines  
reverse-image-html               Convert JSON reports into HTML  
reverse-image-local               Download thumbnails and create local HTML reports  
reverse-image-server             Manage the local PHP server

## Search Usage
Search with the default engine (Yandex):

reverse-image image.jpg

**Search with all five engines:**

reverse-image image.jpg --all

**Select specific engines:**

reverse-image image.jpg --engine yandex,baidu

**Available engine names:**

yandex, baidu, animetrace, iqdb, tineye

List available engines:

```bash
reverse-image --list-engines
```

## Search Options

Limit the number of results:

```bash
reverse-image image.jpg -n 20
```

Set the request timeout:

```bash
reverse-image image.jpg --timeout 120
```

Choose an output JSON file:

```bash
reverse-image image.jpg -o results.json
```

Run without saving a JSON report:

```bash
reverse-image image.jpg --no-save
```

Display command help:

```bash
reverse-image --help
```

## HTML Report Generation

Convert a JSON report into an HTML report:

```bash
reverse-image-html results.json
```

Specify an output HTML file:

```bash
reverse-image-html results.json -o report.html
```

Display help:

```bash
reverse-image-html --help
```

## Local HTML Reports and Thumbnails
Generate a local HTML report with downloaded thumbnails:

```bash
reverse-image-local results.json
```

Set the number of download workers:

```bash
reverse-image-local results.json -w 8
```

Generate the report without starting the local server:

```bash
reverse-image-local results.json --no-serve
```

Display help:

```bash
reverse-image-local --help
```

## Local PHP Server Management

Check the server status:

```bash
reverse-image-server status
```

Start the server:

```bash
reverse-image-server start
```

Stop the server:

```bash
reverse-image-server stop
```

Restart the server:

```bash
reverse-image-server restart
```

The local server uses:

```text
http://127.0.0.1:8765/
```

The server serves files from the Android shared Download directory.
## Output Locations
By default, JSON reports are saved in:

~/reports/reverse-image/

Local HTML reports and downloaded thumbnails are published to:

~/storage/shared/Download/

The PHP server log is stored at:

~/reports/reverse-image/php-server.log

## Uninstallation
From the extracted toolkit source directory, run:

./uninstall.sh

The uninstaller removes the toolkit installation while preserving search reports, downloaded files and launcher backups.
## Important Notes
An internet connection is required for reverse image searches and thumbnail downloads.
PHP CLI is required for the local PHP server.
Search results depend on the availability and response of the supported search engines.
Use images only where you have the right or lawful basis to process them.
The toolkit does not bypass authentication or guarantee that an image will be identified.

## License
See the accompanying project licence, if provided.

