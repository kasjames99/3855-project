#!/bin/bash

echo "Stopping containers..."
docker compose down

echo "Removing Kafka meta.properties..."
rm -f ./data/kafka-data/meta.properties

echo "Starting containers..."
docker compose up -d

echo "Kafka cleanup complete!"