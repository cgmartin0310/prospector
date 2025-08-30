#!/usr/bin/env python3
"""
Migration script to add organization fields to County model
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import County

def migrate_county_organization_fields():
    """Add organization fields to County table"""
    with app.app_context():
        try:
            # Add new columns to County table
            db.engine.execute("""
                ALTER TABLE county 
                ADD COLUMN organization_name VARCHAR(200),
                ADD COLUMN description TEXT,
                ADD COLUMN key_personnel_name VARCHAR(200),
                ADD COLUMN key_personnel_title VARCHAR(100),
                ADD COLUMN key_personnel_phone VARCHAR(50),
                ADD COLUMN key_personnel_email VARCHAR(200),
                ADD COLUMN contact_info TEXT,
                ADD COLUMN address TEXT,
                ADD COLUMN additional_notes TEXT,
                ADD COLUMN confidence_score FLOAT DEFAULT 0.0,
                ADD COLUMN source_urls TEXT,
                ADD COLUMN ai_response_raw TEXT,
                ADD COLUMN last_searched_at DATETIME,
                ADD COLUMN search_query TEXT,
                ADD COLUMN verified BOOLEAN DEFAULT FALSE
            """)
            
            print("✅ Successfully added organization fields to County table")
            
            # Migrate existing SearchResult data to County table
            print("🔄 Migrating existing SearchResult data to County table...")
            
            # Get all counties that have search results
            counties_with_results = db.engine.execute("""
                SELECT DISTINCT c.id, c.name, s.organization_name, s.description,
                       s.key_personnel_name, s.key_personnel_title, s.key_personnel_phone,
                       s.key_personnel_email, s.contact_info, s.address, s.additional_notes,
                       s.confidence_score, s.source_urls, s.ai_response_raw, s.created_at
                FROM county c
                JOIN search_result s ON c.id = s.county_id
                WHERE s.organization_name IS NOT NULL
                ORDER BY s.confidence_score DESC
            """).fetchall()
            
            # Group by county and take the best result for each
            county_updates = {}
            for row in counties_with_results:
                county_id = row[0]
                if county_id not in county_updates:
                    county_updates[county_id] = {
                        'organization_name': row[2],
                        'description': row[3],
                        'key_personnel_name': row[4],
                        'key_personnel_title': row[5],
                        'key_personnel_phone': row[6],
                        'key_personnel_email': row[7],
                        'contact_info': row[8],
                        'address': row[9],
                        'additional_notes': row[10],
                        'confidence_score': row[11],
                        'source_urls': row[12],
                        'ai_response_raw': row[13],
                        'last_searched_at': row[14]
                    }
            
            # Update counties with the best results
            for county_id, data in county_updates.items():
                db.engine.execute("""
                    UPDATE county SET
                        organization_name = %s,
                        description = %s,
                        key_personnel_name = %s,
                        key_personnel_title = %s,
                        key_personnel_phone = %s,
                        key_personnel_email = %s,
                        contact_info = %s,
                        address = %s,
                        additional_notes = %s,
                        confidence_score = %s,
                        source_urls = %s,
                        ai_response_raw = %s,
                        last_searched_at = %s
                    WHERE id = %s
                """, (
                    data['organization_name'],
                    data['description'],
                    data['key_personnel_name'],
                    data['key_personnel_title'],
                    data['key_personnel_phone'],
                    data['key_personnel_email'],
                    data['contact_info'],
                    data['address'],
                    data['additional_notes'],
                    data['confidence_score'],
                    data['source_urls'],
                    data['ai_response_raw'],
                    data['last_searched_at'],
                    county_id
                ))
            
            print(f"✅ Migrated {len(county_updates)} counties with organization data")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            raise

if __name__ == '__main__':
    migrate_county_organization_fields()
