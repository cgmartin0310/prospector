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
                'is_golden'
            ]
            
            # Check which columns need to be added
            columns_to_add = [col for col in new_columns if col not in columns]
            
            if columns_to_add:
                print(f"📝 Adding columns to search_result: {columns_to_add}")
                
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
                    elif column == 'is_golden':
                        sql = text("ALTER TABLE search_result ADD COLUMN is_golden BOOLEAN DEFAULT FALSE")
                    
                    print(f"  Adding {column}...")
                    db.session.execute(sql)
                    print(f"  ✅ Added {column}")
            else:
                print("✅ All search_result columns already exist.")
            
            # Check if golden_result table exists
            tables = inspector.get_table_names()
            if 'golden_result' not in tables:
                print("📝 Creating golden_result table...")
                
                # Create golden_result table
                db.session.execute(text("""
                    CREATE TABLE golden_result (
                        id SERIAL PRIMARY KEY,
                        organization_name VARCHAR(200) NOT NULL,
                        description TEXT,
                        services TEXT,
                        county_id INTEGER NOT NULL REFERENCES county(id),
                        state_id INTEGER NOT NULL REFERENCES state(id),
                        key_personnel_name VARCHAR(200),
                        key_personnel_title VARCHAR(100),
                        key_personnel_phone VARCHAR(50),
                        key_personnel_email VARCHAR(200),
                        contact_info TEXT,
                        address TEXT,
                        website VARCHAR(500),
                        verification_source VARCHAR(200),
                        verification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        verified_by VARCHAR(100),
                        search_query TEXT,
                        search_category VARCHAR(100),
                        relevance_score FLOAT DEFAULT 1.0,
                        completeness_score FLOAT DEFAULT 1.0,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes for better performance
                print("📝 Creating indexes...")
                db.session.execute(text("""
                    CREATE INDEX idx_golden_result_county_id 
                    ON golden_result(county_id)
                """))
                
                db.session.execute(text("""
                    CREATE INDEX idx_golden_result_state_id 
                    ON golden_result(state_id)
                """))
                
                db.session.execute(text("""
                    CREATE INDEX idx_golden_result_search_category 
                    ON golden_result(search_category)
                """))
                
                db.session.execute(text("""
                    CREATE INDEX idx_search_result_is_golden 
                    ON search_result(is_golden)
                """))
                
                print("✅ Created golden_result table and indexes")
            else:
                print("✅ golden_result table already exists.")
            
            # Commit the changes
            db.session.commit()
            print("✅ Database migration completed successfully!")
            
            # Show statistics
            try:
                golden_count = db.session.execute(text("SELECT COUNT(*) FROM golden_result")).scalar()
                print(f"📊 Golden results in database: {golden_count}")
            except:
                print("📊 Golden results table not accessible yet")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise e

if __name__ == "__main__":
    migrate_database()
