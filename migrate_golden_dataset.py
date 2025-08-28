#!/usr/bin/env python3
"""
Database migration script to add Golden Dataset functionality
"""

import os
import sys
from sqlalchemy import text

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import SearchResult, GoldenResult

def migrate_golden_dataset():
    """Add Golden Dataset tables and columns"""
    with app.app_context():
        try:
            # Add is_golden column to search_result table
            print("Adding is_golden column to search_result table...")
            db.session.execute(text("""
                ALTER TABLE search_result 
                ADD COLUMN is_golden BOOLEAN DEFAULT FALSE
            """))
            
            # Create golden_result table
            print("Creating golden_result table...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS golden_result (
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
            print("Creating indexes...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_golden_result_county_id 
                ON golden_result(county_id)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_golden_result_state_id 
                ON golden_result(state_id)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_golden_result_search_category 
                ON golden_result(search_category)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_search_result_is_golden 
                ON search_result(is_golden)
            """))
            
            db.session.commit()
            print("✅ Golden Dataset migration completed successfully!")
            
            # Show statistics
            golden_count = db.session.execute(text("SELECT COUNT(*) FROM golden_result")).scalar()
            print(f"📊 Golden results in database: {golden_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("🔄 Starting Golden Dataset migration...")
    migrate_golden_dataset()
    print("🎉 Migration completed!")
