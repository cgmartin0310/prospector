#!/usr/bin/env python3
"""
PostgreSQL-specific migration to fix Golden Dataset database issues
"""

import os
import sys
from sqlalchemy import text, inspect

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def fix_golden_dataset_migration():
    """Fix the Golden Dataset migration for PostgreSQL"""
    with app.app_context():
        try:
            print("🔧 Starting PostgreSQL Golden Dataset migration fix...")
            
            # Check current table structure
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('search_result')]
            print(f"Current columns in search_result table: {columns}")
            
            # Check if is_golden column exists
            if 'is_golden' not in columns:
                print("📝 Adding is_golden column to search_result table...")
                
                # Use PostgreSQL-specific syntax
                db.session.execute(text("""
                    ALTER TABLE search_result 
                    ADD COLUMN is_golden BOOLEAN DEFAULT FALSE
                """))
                
                db.session.commit()
                print("✅ Added is_golden column successfully")
            else:
                print("✅ is_golden column already exists")
            
            # Check if golden_result table exists
            tables = inspector.get_table_names()
            if 'golden_result' not in tables:
                print("📝 Creating golden_result table...")
                
                # Create golden_result table with PostgreSQL syntax
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
                
                print("✅ Created golden_result table")
            else:
                print("✅ golden_result table already exists")
            
            # Create indexes if they don't exist
            print("📝 Creating indexes...")
            
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_golden_result_county_id 
                    ON golden_result(county_id)
                """))
                print("✅ Created county_id index")
            except Exception as e:
                print(f"⚠️ County index creation failed: {e}")
            
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_golden_result_state_id 
                    ON golden_result(state_id)
                """))
                print("✅ Created state_id index")
            except Exception as e:
                print(f"⚠️ State index creation failed: {e}")
            
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_golden_result_search_category 
                    ON golden_result(search_category)
                """))
                print("✅ Created search_category index")
            except Exception as e:
                print(f"⚠️ Category index creation failed: {e}")
            
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_search_result_is_golden 
                    ON search_result(is_golden)
                """))
                print("✅ Created is_golden index")
            except Exception as e:
                print(f"⚠️ is_golden index creation failed: {e}")
            
            db.session.commit()
            print("✅ PostgreSQL Golden Dataset migration completed successfully!")
            
            # Verify the changes
            inspector = inspect(db.engine)
            updated_columns = [col['name'] for col in inspector.get_columns('search_result')]
            print(f"Updated columns in search_result table: {updated_columns}")
            
            updated_tables = inspector.get_table_names()
            print(f"Available tables: {updated_tables}")
            
            # Test query
            try:
                golden_count = db.session.execute(text("SELECT COUNT(*) FROM golden_result")).scalar()
                print(f"📊 Golden results in database: {golden_count}")
            except Exception as e:
                print(f"⚠️ Could not query golden_result table: {e}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    print("🔄 Starting PostgreSQL Golden Dataset migration fix...")
    fix_golden_dataset_migration()
    print("🎉 Migration fix completed!")
