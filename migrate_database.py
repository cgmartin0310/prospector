#!/usr/bin/env python3
"""
Database migration script to add key personnel columns to the search_result table.
This script should be run on the Render deployment to update the database schema.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models import db
from config import Config
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Create Flask app context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def migrate_database():
    """Add new key personnel columns to the search_result table"""
    
    with app.app_context():
        try:
            print("🔧 Starting database migration...")
            
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('search_result')]
            
            print(f"Current columns in search_result table: {columns}")
            
            # Define the new columns to add
            new_columns = [
                'key_personnel_name',
                'key_personnel_title', 
                'key_personnel_phone',
                'key_personnel_email'
            ]
            
            # Check which columns need to be added
            columns_to_add = [col for col in new_columns if col not in columns]
            
            if not columns_to_add:
                print("✅ All new columns already exist. No migration needed.")
                return
            
            print(f"📝 Adding columns: {columns_to_add}")
            
            # Add each column
            for column in columns_to_add:
                if column == 'key_personnel_name':
                    sql = text("ALTER TABLE search_result ADD COLUMN key_personnel_name VARCHAR(200)")
                elif column == 'key_personnel_title':
                    sql = text("ALTER TABLE search_result ADD COLUMN key_personnel_title VARCHAR(100)")
                elif column == 'key_personnel_phone':
                    sql = text("ALTER TABLE search_result ADD COLUMN key_personnel_phone VARCHAR(50)")
                elif column == 'key_personnel_email':
                    sql = text("ALTER TABLE search_result ADD COLUMN key_personnel_email VARCHAR(200)")
                
                print(f"  Adding {column}...")
                db.session.execute(sql)
                print(f"  ✅ Added {column}")
            
            # Commit the changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            
            # Verify the columns were added
            inspector = db.inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('search_result')]
            print(f"Updated columns in search_result table: {updated_columns}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise e

if __name__ == "__main__":
    migrate_database()
