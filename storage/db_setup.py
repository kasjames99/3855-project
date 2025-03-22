import yaml
import os
import time
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base

logger = logging.getLogger('basicLogger')

ENV = os.environ.get('ENV', 'dev')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '../config')
FULL_CONFIG_PATH = os.path.join(CONFIG_PATH, ENV, 'storage')
app_conf_file = os.path.join(FULL_CONFIG_PATH, 'storage_app_conf.yaml')

with open(app_conf_file, "r") as f:
    app_config = yaml.safe_load(f.read())
    
db_user = app_config["datastore"]["user"]
db_password = app_config["datastore"]["password"]
db_host = app_config["datastore"]["hostname"]
db_port = app_config["datastore"]["port"]
db_name = app_config["datastore"]["db"]

DB_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

max_retries = 20
retry_count = 0
engine = None

while retry_count < max_retries:
    try:
        logger.info(f"Attempting to connect to DB: {DB_URL}")
        engine = create_engine(DB_URL)
        # Test the connection
        with engine.connect() as connection:
            logger.info("Database connection successful")
            break
    except Exception as e:
        retry_count += 1
        logger.error(f"DB connection attempt {retry_count}/{max_retries} failed: {str(e)}")
        if retry_count < max_retries:
            logger.info(f"Retrying in 5 seconds")
            time.sleep(5)
        else:
            logger.error("Max retries reached, could not connect to database")
            raise

logger.info(f"Connecting to database at {DB_URL}")
engine = create_engine(DB_URL)
Base.metadata.bind = engine
inspector = inspect(engine)

existing_tables = inspector.get_table_names()
logger.info(f"Found existing tables: {existing_tables}")

if not inspector.has_table("temperature") or not inspector.has_table("motion"):
    logger.info("Creating missing tables")
    Base.metadata.create_all(engine)
else:
    logger.info("All tables already exist, not creating any")

DB_SESSION = sessionmaker(bind=engine)