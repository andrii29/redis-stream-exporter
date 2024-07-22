## Redis Stream Profiler Exporter
A Python script that exports Redis Stream metrics for Prometheus monitoring. Exporter connects to one or multiple redis instances (or databases), autodiscover streams and collects metrics.

### Installation
```bash
pip install -r requirements.txt
python redis-stream-exporter.py
```

### Docker
```js
docker run -p 9124:9124 -it --rm --name redis-stream-exporter andriik/redis-stream-exporter
docker run -it --rm --net host --name redis-stream-exporter andriik/redis-stream-exporter // host network
```

### Usage
```
usage: redis-stream-exporter.py [-h] [--redis_uris REDIS_URIS] [--scan_count SCAN_COUNT] [--sleep_interval SLEEP_INTERVAL] [--http_port HTTP_PORT]

Redis Stream Metrics Exporter

options:
  -h, --help            show this help message and exit
  --redis_uris REDIS_URIS
                        Comma-separated list of Redis URIs (default: redis://localhost:6379/0)
  --scan_count SCAN_COUNT
                        Number of keys to scan for a streams, adjust accordingly to your db size (default: 1000000)
  --sleep_interval SLEEP_INTERVAL
                        Interval in seconds between metric collections (default: 10)
  --http_port HTTP_PORT
                        Port for the Prometheus HTTP server (default: 9124)

```

#### Environment Variables

You can use `REDIS_URIS, SCAN_COUNT, SLEEP_INTERVAL, HTTP_PORT` environment variables to configure the exporter. If an environment variable is set, it takes precedence over the corresponding command-line argument.

### Inspiration
Inspired by [chrnola/redis-streams-exporter](https://github.com/chrnola/redis-streams-exporter/)

### Grafana Dashboard
You can find example dashboard at id [21566](https://grafana.com/grafana/dashboards/21566)
