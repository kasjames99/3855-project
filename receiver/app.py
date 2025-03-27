import connexion
import os
import sys
import json
import httpx
import time
import yaml
import logging
import logging.config
from datetime import datetime
from threading import Lock
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from connexion import NoContent
from pykafka import KafkaClient

ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '../config')

FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'receiver')
LOG_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'receiver_log_conf.yml')
APP_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'receiver_app_conf.yml')

with open(LOG_CONF_FILE, "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

with open(APP_CONF_FILE, 'r') as f:
    app_config = yaml.safe_load(f.read())

logger = logging.getLogger("basicLogger")

# Add retry logic for Kafka connection
def connect_to_kafka():
    kafka_connected = False
    retry_count = 0
    max_retries = 30

    while not kafka_connected and retry_count < max_retries:
        try:
            logger.info(f"Connecting to Kafka (Attempt {retry_count+1}/{max_retries})...")
            client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            topic = client.topics[str.encode(app_config['events']['topic'])]
            producer = topic.get_sync_producer()
            logger.info("Connected to Kafka!")
            kafka_connected = True
            return client, topic, producer
        except Exception as e:
            retry_count += 1
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            if retry_count < max_retries:
                logger.info(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error("Failed to connect to Kafka after maximum retries")
                raise Exception(f"Failed to connect to Kafka after {max_retries} attempts: {str(e)}")

# Establish connection to Kafka with retries
client, topic, producer = connect_to_kafka()

def log_event(event_type, event_body):
    """ Logs the event to Kafka """
    trace_id = time.time_ns()
    logger.info(f"Received event {event_type} with a trace ID of {trace_id}")

    if event_type == "temperature":
        event_data = {
            "trace_id": trace_id,
            "device_id": event_body["device_id"],
            "temperature": event_body["temperature"],
            "event_type": event_body.get("event_type", "temperature"),
        }
    elif event_type == "motion":
        event_data = {
            "trace_id": trace_id,
            "device_id": event_body["device_id"],
            "room": event_body.get("room", "default_room"),
            "motion_intensity": event_body.get("motion_intensity", 0),
        }

    msg = {
        "type": event_type,
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": event_data
    }

    msg_str = json.dumps(msg)
    logger.info(f"Sending message to Kafka: {msg_str}")
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Produced Kafka message for event {event_type} with trace ID: {trace_id}")

    return NoContent, 201

def postTemperatureEvent(body):
    return log_event("temperature", body)

def postMotionEvent(body):
    return log_event("motion", body)

def getTemperatureEvents(start_timestamp, end_timestamp):
    STORAGE_URL = app_config["events"]["temperature"]["url"]
    params = {"start_timestamp": start_timestamp, "end_timestamp": end_timestamp}
    try:
        response = httpx.get(STORAGE_URL, params=params)
        if response.status_code == 200:
            return response.json(), 200
        else:
            return {"error": "Failed to retrieve temperature events"}, response.status_code
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch temperature events: {e}")
        return {"error": f"Request failed: {e}"}, 500

def getMotionEvents(start_timestamp, end_timestamp):
    STORAGE_URL = app_config["events"]["motion"]["url"]
    params = {"start_timestamp": start_timestamp, "end_timestamp": end_timestamp}
    try:
        response = httpx.get(STORAGE_URL, params=params)
        if response.status_code == 200:
            return response.json(), 200
        else:
            return {"error": "Failed to retrieve motion events"}, response.status_code
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch motion events: {e}")
        return {"error": f"Request failed: {e}"}, 500

app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_api("receiver.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info("Starting Receiver Service")
    app.run(port=8081, host="0.0.0.0")