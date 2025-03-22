import connexion
import json
import os
import yaml
import logging
import logging.config
from pykafka import KafkaClient

ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '../config')

FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'analyzer')
LOG_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'analyzer_log_conf.yml')
APP_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'analyzer_app_conf.yml')

with open(APP_CONF_FILE, 'r') as f:
    app_config = yaml.safe_load(f.read())

with open(LOG_CONF_FILE, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

def get_temperature(index):
    try:
        index = int(index)
    except ValueError:
        logger.error(f"Invalid index format: {index}")
        return {"message": "Index must be an integer"}, 400

    logger.info(f"Retrieving temperature event at index {index}")
    
    try:
        host_str = f"{app_config['kafka']['hostname']}:{app_config['kafka']['port']}"
        logger.info(f"Attempting to connect to Kafka at {host_str}")
        client = KafkaClient(hosts=host_str)
        topic_name = app_config['kafka']['topic']
        logger.info(f"Looking for topic: {topic_name}")
        topic = client.topics[str.encode(topic_name)]
        logger.info("Successfully connected to Kafka and found topic")
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        logger.info("Created Kafka consumer")
    except Exception as e:
        logger.error(f"Detailed Kafka connection error: {str(e)}")
        return {"message": f"Error connecting to message queue: {str(e)}"}, 500
    
    current_index = 0
    try:
        for msg in consumer:
            message = msg.value.decode("utf-8")
            data = json.loads(message)
            
            if data["type"] == "temperature":
                if current_index == index:
                    logger.info(f"Found temperature event at index {index}")
                    return data["payload"], 200
                current_index += 1
    except Exception as e:
        logger.error(f"Error processing Kafka messages: {e}")
        return {"message": "Error processing message queue"}, 500
    
    logger.warning(f"No temperature event found at index {index}")
    return {"message": f"No temperature event found at index {index}"}, 404

def get_motion(index):
    try:
        index = int(index)
    except ValueError:
        logger.error(f"Invalid index format: {index}")
        return {"message": "Index must be an integer"}, 400

    logger.info(f"Retrieving motion event at index {index}")
    
    try:
        host_str = f"{app_config['kafka']['hostname']}:{app_config['kafka']['port']}"
        logger.info(f"Attempting to connect to Kafka at {host_str}")
        client = KafkaClient(hosts=host_str)
        topic_name = app_config['kafka']['topic']
        logger.info(f"Looking for topic: {topic_name}")
        topic = client.topics[str.encode(topic_name)]
        logger.info("Successfully connected to Kafka and found topic")
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        logger.info("Created Kafka consumer")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.error(f"Detailed Kafka connection error: Type: {error_type}, Message: {error_msg}")
        logger.exception("Full error traceback:")
        return {"message": f"Error connecting to message queue: {error_type} - {error_msg}"}, 500
    
    current_index = 0
    try:
        for msg in consumer:
            message = msg.value.decode("utf-8")
            data = json.loads(message)
            
            if data["type"] == "motion":
                if current_index == index:
                    logger.info(f"Found motion event at index {index}")
                    return data["payload"], 200
                current_index += 1
    except Exception as e:
        logger.error(f"Error processing Kafka messages: {e}")
        return {"message": "Error processing message queue"}, 500
    
    logger.warning(f"No motion event found at index {index}")
    return {"message": f"No motion event found at index {index}"}, 404

def get_event_stats():
    logger.info("Retrieving event statistics")
    
    try:
        client = KafkaClient(hosts=f"{app_config['kafka']['hostname']}:{app_config['kafka']['port']}")
        topic = client.topics[str.encode(app_config['kafka']['topic'])]
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    except Exception as e:
        logger.error(f"Error connecting to Kafka: {e}")
        return {"message": "Error connecting to message queue"}, 500
    
    temperature_count = 0
    motion_count = 0
    
    try:
        for msg in consumer:
            message = msg.value.decode("utf-8")
            data = json.loads(message)
            
            if data["type"] == "temperature":
                temperature_count += 1
            elif data["type"] == "motion":
                motion_count += 1
    except Exception as e:
        logger.error(f"Error processing Kafka messages: {e}")
        return {"message": "Error processing message queue"}, 500
    
    stats = {
        "num_temperature_events": temperature_count,
        "num_motion_events": motion_count
    }
    
    logger.info(f"Event statistics: {stats}")
    return stats, 200

app = connexion.FlaskApp(__name__, specification_dir='.')

app.add_api('analyzer.yaml')

if __name__ == '__main__':
    logger.info("Starting Analyzer Service")
    app.run(port=app_config['service']['port'], host="0.0.0.0")