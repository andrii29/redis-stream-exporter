import os
import logging
import redis
from prometheus_client import start_http_server, Gauge
import time
from urllib.parse import urlparse
import argparse

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Redis Stream Metrics Exporter', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--redis_uris', type=str, default=os.getenv('REDIS_URI', 'redis://localhost:6379/0'),
                    help='Comma-separated list of Redis URIs')
parser.add_argument('--scan_count', type=int, default=int(os.getenv('SCAN_COUNT', 1000000)),
                    help='Number of keys to scan for a streams, adjust accordingly to your db size')
parser.add_argument('--sleep_interval', type=int, default=int(os.getenv('SLEEP_INTERVAL', 10)),
                    help='Interval in seconds between metric collections')
parser.add_argument('--http_port', type=int, default=int(os.getenv('HTTP_PORT', 9124)),
                    help='Port for the Prometheus HTTP server')
args = parser.parse_args()

# Configuration
REDIS_URIS = args.redis_uris.split(',')
SCAN_COUNT = args.scan_count
SLEEP_INTERVAL = args.sleep_interval
HTTP_PORT = args.http_port

# Function to create Redis clients and extract server labels
def create_redis_clients(redis_uris):
    clients = []
    server_labels = []
    for uri in redis_uris:
        parsed_uri = urlparse(uri)
        username = parsed_uri.username
        password = parsed_uri.password
        host = parsed_uri.hostname
        port = parsed_uri.port
        db = parsed_uri.path[1:] if parsed_uri.path else 0

        # Format server label (hide username and password)
        server_label = f"{host}:{port}/{db}"
        server_labels.append(server_label)

        client = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            username=username,
            password=password
        )
        clients.append(client)

    # Log information about connected Redis servers
    logging.info(f"Connected to Redis servers: {server_labels}")

    return clients, server_labels

# Prometheus metrics
stream_length_gauge = Gauge('redis_stream_length', 'Length of Redis Stream', ['stream', 'redis_server'])
consumer_groups_total_gauge = Gauge('redis_stream_consumers_total', 'Total number of consumer groups for Redis Stream', ['stream', 'redis_server'])

# New metrics
consumer_group_pending_messages_total_gauge = Gauge('redis_stream_consumer_group_pending_messages_total', 'Total number of pending messages in Redis Stream consumer group', ['stream', 'redis_server', 'group'])
consumer_group_consumers_total_gauge = Gauge('redis_stream_consumer_group_consumers_total', 'Total number of consumers in Redis Stream consumer group', ['stream', 'redis_server', 'group'])
consumer_idle_time_total_gauge = Gauge('redis_stream_consumer_idle_time_seconds_total', 'Idle time of each consumer in Redis Stream consumer group', ['stream', 'redis_server', 'group', 'consumer'])

def get_streams(redis_client):
    streams = []
    _, keys = redis_client.scan(match='*', count=SCAN_COUNT, _type='stream')
    for key in keys:
        streams.append(key.decode('utf-8'))
    return streams

def collect_metrics():
    for client, server_label in zip(redis_clients, server_labels):
        streams = get_streams(client)
        for stream in streams:
            length = client.xlen(stream)
            stream_length_gauge.labels(stream=stream, redis_server=server_label).set(length)

            # Fetch and set additional metrics
            try:
                # Get total number of consumer groups
                consumer_groups = client.xinfo_groups(stream)
                consumer_groups_total_gauge.labels(stream=stream, redis_server=server_label).set(len(consumer_groups))

                for group in consumer_groups:
                    group_name = group['name'].decode('utf-8')

                    # Get total number of pending messages in the group
                    pending_messages = client.xpending(stream, group_name)
                    if isinstance(pending_messages, dict):  # Handle the case where detailed pending messages are returned
                        count = pending_messages.get('pending', 0)
                    else:
                        count = pending_messages
                    consumer_group_pending_messages_total_gauge.labels(stream=stream, redis_server=server_label, group=group_name).set(count)

                    # Get total number of consumers in the group
                    consumers = client.xinfo_consumers(stream, group_name)
                    consumer_group_consumers_total_gauge.labels(stream=stream, redis_server=server_label, group=group_name).set(len(consumers))

                    # Get data per consumer
                    for consumer in consumers:
                        consumer_name = consumer['name'].decode('utf-8')

                        # Get idle time for each consumer
                        idle_time = consumer.get('idle', 0)
                        consumer_idle_time_total_gauge.labels(stream=stream, redis_server=server_label, group=group_name, consumer=consumer_name).set(idle_time / 1000)  # Convert ms to seconds

            except redis.RedisError as e:
                logging.info(f"Error collecting metrics for stream {stream}: {e}")

if __name__ == '__main__':
    # Log important information
    logging.info(f"Starting Redis Stream Prometheus Exporter with the following parameters:")
    logging.info(f"Scan count: {SCAN_COUNT}")
    logging.info(f"Sleep interval: {SLEEP_INTERVAL}")
    logging.info(f"HTTP port: {HTTP_PORT}")

    # Connect to Redis servers
    redis_clients, server_labels = create_redis_clients(REDIS_URIS)

    # Start the Prometheus HTTP server
    start_http_server(HTTP_PORT)

    # Collect metrics at regular intervals
    while True:
        collect_metrics()
        time.sleep(SLEEP_INTERVAL)  # Collect metrics every specified interval
