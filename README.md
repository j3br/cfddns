# cfddns

Cloudflare Dynamic DNS updater

## Installation
1. Clone this repo
2. Install the required dependencies: 
```bash
pip install -r requirements.txt
```

## Configuration

By default, the program looks for a `config.json` file inside the cfddns module directory. However, you can specify a custom path to your configuration file using the `--config` command-line argument.

To provide a custom path to your configuration file, use the following command:

```bash
cfddns --config /path/to/config.json
```

Replace /path/to/config.json with the actual path to your configuration file.

Note that the configuration file must be a valid JSON file.
For more information on the required format and structure of the configuration file, refer to the `config-sample.json` file provided in the cfddns module directory.


## Usage

### Running with Python
```
python -m cfddns [--config /path/to/config.json]
```

### Running with Docker

#### Docker run
```
docker run -d \
    --name cfddns \
    --security-opt no-new-privileges:true \
    -e PUID=1000 \
    -e PGID=1000 \
    -e CRON_SCHEDULE="0 * * * *" \
    -v /path/to/config.json:/app/config.json \
    --restart unless-stopped \
    j3br/cfddns
```

#### Docker Compose
```
version: '3.8'
services:
  cfddns:
    image: j3br/cfddns
    container_name: cfddns
    security_opt:
      - no-new-privileges:true
    environment:
      - PUID=1000
      - PGID=1000
      - CRON_SCHEDULE="0 * * * *" # Custom cron schedule. Defaults to every 5 min if omitted.
    volumes:
      - /path/to/config.json:/app/config.json
    restart: unless-stopped
```
