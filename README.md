# cfddns

Cloudflare Dynamic DNS updater

## Installation
1. Clone this repo
2. Install the required dependencies: 
```bash
pip install -r requirements.txt
```

## Configuration

By default, the program looks for a `config.json` file inside the cfddns module directory. 

To provide a custom path to your configuration file, use the following command:

```bash
cfddns --config /path/to/config.json
```

Note that the configuration file must be a valid JSON file.
For more information on the required format and structure of the configuration file, refer to the `config-sample.json` file provided in the cfddns module directory.


## Usage

### Running with Python
To run the program with Python, use the following command:
```
python -m cfddns [--config /path/to/config.json] [-i INTERVAL]
```
Optional Arguments

`-i INTERVAL, --interval INTERVAL`

Interval between loop iterations in seconds (default is 60 seconds; minimum is 30 seconds, maximum is 3600 seconds)


### Running with Docker

#### Docker run
```
docker run -d \
    --name cfddns \
    --security-opt no-new-privileges:true \
    -e PUID=1000 \
    -e PGID=1000 \
    -e INTERVAL=60 \
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
      - INTERVAL=60 # Custom interval in seconds (valid range: 30-3600). If omitted, the DNS update runs only once.
    volumes:
      - /path/to/config.json:/app/config.json
    restart: unless-stopped
```
