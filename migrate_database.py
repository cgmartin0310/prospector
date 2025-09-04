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
    """Add new key personnel columns and Golden Dataset functionality to the database"""
    
    with app.app_context():
        try:
            print("🔧 Starting database migration...")
            
            # Check if columns already exist in search_result table
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('search_result')]
            
            print(f"Current columns in search_result table: {columns}")
            
            # Define the new columns to add to search_result
            new_columns = [
                'key_personnel_name',
                'key_personnel_title', 
                'key_personnel_phone',
                'key_personnel_email',
        
            ]
            
            # Check which columns need to be added
            columns_to_add = [col for col in new_columns if col not in columns]
            
            if columns_to_add:
                print(f"📝 Adding columns to search_result: {columns_to_add}")
                
                # Add each column with PostgreSQL-specific syntax
                for column in columns_to_add:
                    if column == 'key_personnel_name':
                        sql = text("ALTER TABLE search_result ADD COLUMN IF NOT EXISTS key_personnel_name VARCHAR(200)")
                    elif column == 'key_personnel_title':
                        sql = text("ALTER TABLE search_result ADD COLUMN IF NOT EXISTS key_personnel_title VARCHAR(100)")
                    elif column == 'key_personnel_phone':
                        sql = text("ALTER TABLE search_result ADD COLUMN IF NOT EXISTS key_personnel_phone VARCHAR(50)")
                    elif column == 'key_personnel_email':
                        sql = text("ALTER TABLE search_result ADD COLUMN IF NOT EXISTS key_personnel_email VARCHAR(200)")

                    
                    print(f"  Adding {column}...")
                    db.session.execute(sql)
                    print(f"  ✅ Added {column}")
            else:
                print("✅ All search_result columns already exist.")
            

            

            
            # Commit the changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            

            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise e

if __name__ == "__main__":
    migrate_database()
