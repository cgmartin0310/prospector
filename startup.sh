#!/bin/bash

# Navigate to the project directory
cd /opt/render/project/src

# Run the migration
echo "Running database migration..."
python migrate_county_organization_fields.py

# Start the Flask app
echo "Starting Flask application..."
python app.py
