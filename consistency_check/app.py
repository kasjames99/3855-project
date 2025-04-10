import connexion
import os
import json
import time
from datetime import datetime
import yaml
import logging
import logging.config
import httpx
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

# Environment setup
ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config')
FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'consistency_check')
LOG_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'consistency_check_log_conf.yml')
APP_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'consistency_check_app_conf.yml')

# Load configuration
with open(LOG_CONF_FILE, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

with open(APP_CONF_FILE, 'r') as f:
    app_config = yaml.safe_load(f.read())

logger = logging.getLogger('consistencyCheckService')

# Define the path to the JSON data store
DATA_STORE_PATH = app_config.get('datastore', {}).get('filepath', '/app/data/consistency_checks.json')

def get_checks():
    """
    Returns the latest consistency check results from the JSON data store.
    """
    if not os.path.exists(DATA_STORE_PATH):
        logger.warning("No consistency check results found - data store does not exist")
        return {"message": "No consistency checks have been run yet"}, 404
    
    try:
        with open(DATA_STORE_PATH, 'r') as f:
            check_results = json.load(f)
        
        logger.info(f"Retrieved consistency check results from {DATA_STORE_PATH}")
        return check_results, 200
    
    except Exception as e:
        logger.error(f"Error retrieving consistency check results: {str(e)}")
        return {"message": f"Error retrieving consistency check results: {str(e)}"}, 400

def run_update():
    """
    Performs a new consistency check and updates the JSON data store.
    
    The function:
    1. Gets event counts from the processing service
    2. Gets event counts and IDs from the analyzer service
    3. Gets event counts and IDs from the storage service
    4. Compares the lists to find inconsistencies
    5. Stores the results in the JSON data store
    """
    start_time = time.time()
    logger.info("Starting consistency check update")
    
    try:
        # Step 1: Get event counts from processing service
        processing_url = app_config['endpoints']['processing']
        processing_response = httpx.get(f"{processing_url}/stats")
        processing_response.raise_for_status()
        processing_stats = processing_response.json()
        
        # Step 2: Get event counts from analyzer service
        analyzer_url = app_config['endpoints']['analyzer']
        analyzer_stats_response = httpx.get(f"{analyzer_url}/stats")
        analyzer_stats_response.raise_for_status()
        analyzer_stats = analyzer_stats_response.json()
        
        # Get event IDs from analyzer
        temperature_ids_queue_response = httpx.get(f"{analyzer_url}/temperature/ids")
        temperature_ids_queue_response.raise_for_status()
        temperature_ids_queue = temperature_ids_queue_response.json()
        
        motion_ids_queue_response = httpx.get(f"{analyzer_url}/motion/ids")
        motion_ids_queue_response.raise_for_status()
        motion_ids_queue = motion_ids_queue_response.json()
        
        # Step 3: Get event counts from storage service
        storage_url = app_config['endpoints']['storage']
        storage_counts_response = httpx.get(f"{storage_url}/counts")
        storage_counts_response.raise_for_status()
        storage_counts = storage_counts_response.json()
        
        # Get event IDs from storage
        temperature_ids_db_response = httpx.get(f"{storage_url}/temperature/ids")
        temperature_ids_db_response.raise_for_status()
        temperature_ids_db = temperature_ids_db_response.json()
        
        motion_ids_db_response = httpx.get(f"{storage_url}/motion/ids")
        motion_ids_db_response.raise_for_status()
        motion_ids_db = motion_ids_db_response.json()
        
        # Step 4: Compare lists to find inconsistencies
        
        # Convert queue lists to sets of trace_ids for efficient comparison
        temperature_queue_trace_ids = {event['trace_id'] for event in temperature_ids_queue}
        motion_queue_trace_ids = {event['trace_id'] for event in motion_ids_queue}
        
        # Convert DB lists to sets of trace_ids for efficient comparison
        temperature_db_trace_ids = {event['trace_id'] for event in temperature_ids_db}
        motion_db_trace_ids = {event['trace_id'] for event in motion_ids_db}
        
        # Find temperature events missing in DB but in queue
        temp_missing_in_db = [
            {
                "event_id": event['event_id'],
                "trace_id": event['trace_id'],
                "type": "temperature"
            }
            for event in temperature_ids_queue
            if event['trace_id'] not in temperature_db_trace_ids
        ]
        
        # Find motion events missing in DB but in queue
        motion_missing_in_db = [
            {
                "event_id": event['event_id'],
                "trace_id": event['trace_id'],
                "type": "motion"
            }
            for event in motion_ids_queue
            if event['trace_id'] not in motion_db_trace_ids
        ]
        
        # Find temperature events missing in queue but in DB
        temp_missing_in_queue = [
            {
                "event_id": event['event_id'],
                "trace_id": event['trace_id'],
                "type": "temperature"
            }
            for event in temperature_ids_db
            if event['trace_id'] not in temperature_queue_trace_ids
        ]
        
        # Find motion events missing in queue but in DB
        motion_missing_in_queue = [
            {
                "event_id": event['event_id'],
                "trace_id": event['trace_id'],
                "type": "motion"
            }
            for event in motion_ids_db
            if event['trace_id'] not in motion_queue_trace_ids
        ]
        
        # Combine missing lists
        missing_in_db = temp_missing_in_db + motion_missing_in_db
        missing_in_queue = temp_missing_in_queue + motion_missing_in_queue
        
        # Step 5: Store the results in the JSON data store
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        check_results = {
            "last_updated": current_time,
            "counts": {
                "db": {
                    "temperature": storage_counts.get("temperature", 0),
                    "motion": storage_counts.get("motion", 0)
                },
                "queue": {
                    "temperature": analyzer_stats.get("num_temperature_events", 0),
                    "motion": analyzer_stats.get("num_motion_events", 0)
                },
                "processing": {
                    "temperature": processing_stats.get("num_temperature_events", 0),
                    "motion": processing_stats.get("num_motion_events", 0)
                }
            },
            "missing_in_db": missing_in_db,
            "missing_in_queue": missing_in_queue
        }
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(DATA_STORE_PATH), exist_ok=True)
        
        # Write to file
        with open(DATA_STORE_PATH, 'w') as f:
            json.dump(check_results, f, indent=4)
        
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        # Log completion with summary
        logger.info(f"Consistency checks completed | processing_time_ms={processing_time_ms} | "
                   f"missing_in_db = {len(missing_in_db)} | missing_in_queue = {len(missing_in_queue)}")
        
        return {"processing_time_ms": processing_time_ms}, 200
    
    except Exception as e:
        logger.error(f"Error running consistency check: {str(e)}")
        return {"message": f"Error running consistency check: {str(e)}"}, 400

# Create Connexion application
app = connexion.FlaskApp(__name__, specification_dir='.')

# Add CORS middleware if enabled
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add API definition
app.add_api('consistency_check.yaml', base_path="/consistency_check", strict_validation=True, validate_responses=True)

if __name__ == '__main__':
    port = app_config.get('service', {}).get('port', 8200)
    logger.info(f"Starting Consistency Check Service on port {port}")
    app.run(port=port, host="0.0.0.0")