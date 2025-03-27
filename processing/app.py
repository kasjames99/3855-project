import connexion
import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import logging
import logging.config
import json
import os
import yaml
import httpx

ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = "/app/config"

FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'processing')
LOG_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'processing_log_conf.yml')
APP_CONF_FILE = os.path.join(FULL_CONFIG_PATH, 'processing_app_conf.yml')

with open(APP_CONF_FILE, 'r') as f:
    app_conf = yaml.safe_load(f)

with open(LOG_CONF_FILE, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('processingService')
logger.info(f"Loading configuration for environment: {ENV}")

STATS_FILE_PATH = "stats.json"

default_stats = {
    'num_temperature_events': 0,
    'num_motion_events': 0,
    'max_temperature_value': float('-inf'),
    'min_temperature_value': float('inf'),
    'avg_temperature_value': 0,
    'sum_temperature_value': 0,
    'count_temperature_value': 0,
    'max_motion_intensity': float('-inf'),
    'min_motion_intensity': float('inf'),
    'avg_motion_intensity': 0,
    'sum_motion_intensity': 0,
    'count_motion_intensity': 0,
    'last_event_datetime': "2025-01-01T00:00:00Z"
}

def populate_stats():
    logger.info("Populating stats...")

    if os.path.exists(STATS_FILE_PATH):
        try:
            with open(STATS_FILE_PATH, 'r') as file:
                stats = json.load(file)
                logger.info("Loaded existing stats from file.")
        except Exception as e:
            logger.error(f"Error reading the stats file: {e}")
            stats = default_stats
    else:
        logger.info("Stats file not found. Using default values.")
        stats = default_stats

    current_datetime = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    logger.info(f"Current datetime: {current_datetime}")

    last_event_datetime = stats.get('last_event_datetime', "2025-01-01T00:00:00Z")
    logger.info(f"Last event datetime: {last_event_datetime}")

    if last_event_datetime is None:
        last_event_datetime = "2025-01-01T00:00:00Z"
        logger.info(f"Last event datetime was None, using default: {last_event_datetime}")

    try:
        last_event_datetime = datetime.strptime(last_event_datetime, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Most recent event processed at: {last_event_datetime}")
    except ValueError:
        logger.error(f"Invalid datetime format for last_event_datetime: {last_event_datetime}")
        last_event_datetime = "2025-01-01T00:00:00Z"

    temperature_url = app_conf['urls']['temperature_events']
    params = {
        'start_timestamp': last_event_datetime,
        'end_timestamp': current_datetime
    }

    logger.info(f"Querying temperature events with URL: {temperature_url} and params: {params}")

    try:
        temp_response = httpx.get(temperature_url, params=params)
        logger.info(f"Final URL sent: {temp_response.request.url}")
        temp_response.raise_for_status()

        if temp_response.status_code == 200:
            temp_events = temp_response.json()
            logger.info(f"Received {len(temp_events)} temperature events.")
            for event in temp_events:
                temp_value = event['temperature']
                stats['num_temperature_events'] += 1
                stats['sum_temperature_value'] += temp_value
                stats['count_temperature_value'] += 1
                stats['max_temperature_value'] = max(stats['max_temperature_value'], temp_value)
                stats['min_temperature_value'] = min(stats['min_temperature_value'], temp_value)
            if stats['count_temperature_value'] > 0:
                stats['avg_temperature_value'] = stats['sum_temperature_value'] / stats['count_temperature_value']
        else:
            logger.error(f"Failed to fetch temperature events. Status code: {temp_response.status_code}")
    except Exception as e:
        logger.error(f"Error querying temperature events: {e}")

    motion_url = app_conf['urls']['motion_events']
    try:
        motion_response = httpx.get(motion_url, params=params)
        motion_response.raise_for_status()
        if motion_response.status_code == 200:
            motion_events = motion_response.json()
            logger.info(f"Received {len(motion_events)} motion events.")
            for event in motion_events:
                motion_intensity = event['motion_intensity']
                stats['num_motion_events'] += 1
                stats['sum_motion_intensity'] += motion_intensity
                stats['count_motion_intensity'] += 1
                stats['max_motion_intensity'] = max(stats['max_motion_intensity'], motion_intensity)
                stats['min_motion_intensity'] = min(stats['min_motion_intensity'], motion_intensity)
            if stats['count_motion_intensity'] > 0:
                stats['avg_motion_intensity'] = stats['sum_motion_intensity'] / stats['count_motion_intensity']
        else:
            logger.error(f"Failed to fetch motion events. Status code: {motion_response.status_code}")
    except Exception as e:
        logger.error(f"Error querying motion events: {e}")

    stats['last_event_datetime'] = current_datetime

    try:
        with open(STATS_FILE_PATH, 'w') as file:
            json.dump(stats, file, indent=4)
        logger.info(f"Updated stats: {stats}")
    except Exception as e:
        logger.error(f"Error saving stats to file: {e}")

def init_scheduler():
    interval = app_conf.get('scheduler', {}).get('interval_seconds', 10)
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=interval)
    sched.start()

def get_stats():
    if os.path.exists(STATS_FILE_PATH):
        with open(STATS_FILE_PATH, 'r') as file:
            stats = json.load(file)
        return stats, 200
    else:
        return {'message': 'Stats file not found'}, 400

app = connexion.FlaskApp(__name__, specification_dir='.')
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_api('stats_api.yml')

if __name__ == '__main__':
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")