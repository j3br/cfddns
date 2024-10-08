# cfddns

Cloudflare Dynamic DNS updater

![Docker Image CI](https://github.com/j3br/cfddns/actions/workflows/docker-image.yml/badge.svg)

## Installation
1. Clone this repo
2. Install the required dependencies: 
```bash
pip install -r requirements.txt
```

## Configuration

By default, the program looks for a `config.yaml` file inside the `config` directory. 

To provide a custom path to your configuration file, use the following command:

```bash
cfddns --config /path/to/config.yaml
```

Note that the configuration file must be a valid YAML file.
For more information on the required format and structure of the configuration file, refer to the `config.yaml.sample` file provided in the `config` directory.


## Usage

### Running with Python
To run the program with Python, use the following command:
```
python -m cfddns [-i INTERVAL] path/to/config.yaml
```
**Optional Arguments**

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
    -v ./config:/app/config \
    --restart unless-stopped \
    j3br/cfddns
```

#### Docker Compose
Pre-compiled images are available on [DockerHub](https://hub.docker.com/repository/docker/j3br/cfddns).
```yaml
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
      - ./config:/app/config
    restart: unless-stopped
```
