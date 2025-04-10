import connexion
import os
import json
import yaml
import logging
import logging.config
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from db_setup import DB_SESSION
from models import temperatureEvent, motionEvent
from datetime import datetime
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '../config')

# Construct the paths once and store them in constants
FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'storage')
LOG_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'storage_log_conf.yml')
APP_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'storage_app_conf.yaml')

with open(LOG_CONF_FILE, 'r') as f:
    log_conf = yaml.safe_load(f.read())
    logging.config.dictConfig(log_conf)

with open(APP_CONF_FILE, 'r') as f:
    app_conf = yaml.safe_load(f.read())

logger = logging.getLogger('basicLogger')

def process_messages():
    """ Process event messages """
    logger.info("Starting Kafka consumer...")

    kafka_host = os.environ.get('KAFKA_HOST', app_conf['events']['hostname'])
    kafka_port = os.environ.get('KAFKA_PORT', app_conf['events']['port'])
    kafka_topic = os.environ.get('KAFKA_TOPIC', app_conf['events']['topic'])

    hostname = f"{kafka_host}:{kafka_port}"
    client = KafkaClient(hosts=hostname)
    logger.info(f"Connected to Kafka at {hostname}")

    topic = client.topics[str.encode(kafka_topic)]

    try:
        #sets up a connection to the kafka broker using hostname and port
        hostname = f"{app_conf['events']['hostname']}:{app_conf['events']['port']}"
        client = KafkaClient(hosts=hostname)
        logger.info(f"Connected to Kafka at {hostname}")
        #sets a topic location, where events will be sent and stored
        topic = client.topics[str.encode(app_conf['events']['topic'])]
        logger.info(f"Found topic: {app_conf['events']['topic']}")

        consumer = topic.get_simple_consumer(
            consumer_group=b'event_group',
            reset_offset_on_start=False,
            auto_offset_reset=OffsetType.LATEST
        )
        logger.info("Consumer created and ready to receive messages")

        for msg in consumer:
            logger.info("Received message - processing...")
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.info(f"Message: {msg}")

            payload = msg["payload"]

            session = DB_SESSION()

            if msg["type"] == "temperature":
                temperature = temperatureEvent(
                    device_id=payload['device_id'],
                    temperature=payload['temperature'],
                    timestamp=datetime.strptime(msg['datetime'], "%Y-%m-%dT%H:%M:%S"),
                    event_type=payload['event_type'],
                    trace_id=payload['trace_id']
                )
                session.add(temperature)
                logger.info(f"Stored temperature event with trace id: {payload['trace_id']}")

            elif msg["type"] == "motion":
                motion = motionEvent(
                    device_id=payload['device_id'],
                    room=payload['room'],
                    motion_intensity=payload['motion_intensity'],
                    timestamp=datetime.strptime(msg['datetime'], "%Y-%m-%dT%H:%M:%S"),
                    trace_id=payload['trace_id']
                )
                session.add(motion)
                logger.info(f"Stored motion event with trace id: {payload['trace_id']}")

            session.commit()
            session.close()
            consumer.commit_offsets()
            logger.info("Message processing completed")

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def get_temperature_events(start_timestamp, end_timestamp):
    """Gets temperature events between the given start and end timestamps."""
    session = DB_SESSION()

    if start_timestamp.endswith('Z'):
        start_timestamp = start_timestamp[:-1]
    if end_timestamp.endswith('Z'):
        end_timestamp = end_timestamp[:-1]

    start = datetime.fromisoformat(start_timestamp)
    end = datetime.fromisoformat(end_timestamp)

    temperature_events = session.query(temperatureEvent).filter(
        temperatureEvent.timestamp >= start,
        temperatureEvent.timestamp < end
    ).all()

    results = [event.to_dict() for event in temperature_events]
    session.close()

    logger.info(f"Found {len(results)} temperature events")
    return results, 200

def get_motion_events(start_timestamp, end_timestamp):
    """Gets motion events between the given start and end timestamps."""
    session = DB_SESSION()

    if start_timestamp.endswith('Z'):
        start_timestamp = start_timestamp[:-1]
    if end_timestamp.endswith('Z'):
        end_timestamp = end_timestamp[:-1]

    start = datetime.fromisoformat(start_timestamp)
    end = datetime.fromisoformat(end_timestamp)

    motion_events = session.query(motionEvent).filter(
        motionEvent.timestamp >= start,
        motionEvent.timestamp < end
    ).all()

    results = [event.to_dict() for event in motion_events]
    session.close()

    logger.info(f"Found {len(results)} motion events")
    return results, 200

# Add these functions to your storage app.py file

def get_event_counts():
    """
    Gets the count of each event type in the database.
    
    Returns:
        A dictionary with counts for each event type and a 200 status code,
        or an error message and a 400 status code.
    """
    session = DB_SESSION()
    
    try:
        temperature_count = session.query(temperatureEvent).count()
        motion_count = session.query(motionEvent).count()
        
        result = {
            "temperature": temperature_count,
            "motion": motion_count
        }
        
        logger.info(f"Retrieved event counts: {result}")
        return result, 200
    
    except Exception as e:
        logger.error(f"Error retrieving event counts: {str(e)}")
        return {"message": f"Error retrieving event counts: {str(e)}"}, 400
    
    finally:
        session.close()

def get_temperature_ids():
    """
    Gets a list of event IDs and trace IDs for temperature events.
    
    Returns:
        A list of dictionaries containing event_id and trace_id, and a 200 status code,
        or an error message and a 400 status code.
    """
    session = DB_SESSION()
    
    try:
        # Select only the fields we need
        events = session.query(
            temperatureEvent.device_id,
            temperatureEvent.trace_id
        ).all()
        
        # Convert to list of dictionaries
        result = [
            {
                "event_id": event.device_id,
                "trace_id": event.trace_id
            }
            for event in events
        ]
        
        logger.info(f"Retrieved {len(result)} temperature event IDs")
        return result, 200
    
    except Exception as e:
        logger.error(f"Error retrieving temperature event IDs: {str(e)}")
        return {"message": f"Error retrieving temperature event IDs: {str(e)}"}, 400
    
    finally:
        session.close()

def get_motion_ids():
    """
    Gets a list of event IDs and trace IDs for motion events.
    
    Returns:
        A list of dictionaries containing event_id and trace_id, and a 200 status code,
        or an error message and a 400 status code.
    """
    session = DB_SESSION()
    
    try:
        # Select only the fields we need
        events = session.query(
            motionEvent.device_id,
            motionEvent.trace_id
        ).all()
        
        # Convert to list of dictionaries
        result = [
            {
                "event_id": event.device_id,
                "trace_id": event.trace_id
            }
            for event in events
        ]
        
        logger.info(f"Retrieved {len(result)} motion event IDs")
        return result, 200
    
    except Exception as e:
        logger.error(f"Error retrieving motion event IDs: {str(e)}")
        return {"message": f"Error retrieving motion event IDs: {str(e)}"}, 400
    
    finally:
        session.close()

#This will listen for messages constantly in the background
def setup_kafka_thread():
    logger.info("Creating Kafka consumer thread")
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    logger.info("Kafka consumer thread started")

app = connexion.FlaskApp(__name__, specification_dir='.')
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.add_api("receiver.yml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info("Storage Service starting...")
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")