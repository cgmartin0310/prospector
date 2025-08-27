#!/usr/bin/env python3
"""
Script to populate the database with all US counties.
This script will fetch all 3,244 counties from the Census API.
"""

import sys
import os
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, State, County
from services.data_loader import DataLoader

def populate_all_counties():
    """Populate database with all US counties"""
    
    with app.app_context():
        print("=" * 60)
        print("PROSPECTOR - US COUNTIES DATABASE POPULATION")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check current state
        states_count = State.query.count()
        counties_count = County.query.count()
        
        print(f"Current database state:")
        print(f"  States: {states_count}")
        print(f"  Counties: {counties_count}")
        print()
        
        if states_count == 0:
            print("No states found. The database will be initialized with all states and counties.")
            
            # Initialize the data loader and load everything
            loader = DataLoader()
            loader.load_states_and_counties()
            
        else:
            print("States found. Loading missing counties...")
            
            # Just load counties for existing states
            loader = DataLoader()
            state_objects = {state.abbreviation: state for state in State.query.all()}
            counties_added = loader._load_all_counties_from_data(state_objects)
            db.session.commit()
            
            if counties_added > 0:
                print(f"Successfully added {counties_added} counties!")
            else:
                print("All counties are already loaded.")
        
        # Final count
        final_states = State.query.count()
        final_counties = County.query.count()
        
        print()
        print("=" * 60)
        print("POPULATION COMPLETE")
        print("=" * 60)
        print(f"Final database state:")
        print(f"  States: {final_states}")
        print(f"  Counties: {final_counties}")
        print()
        
        # Show some sample data
        print("Sample counties by state:")
        for state in State.query.order_by(State.name).limit(5).all():
            county_count = County.query.filter_by(state_id=state.id).count()
            print(f"  {state.name} ({state.abbreviation}): {county_count} counties")
            
            # Show first few counties
            sample_counties = County.query.filter_by(state_id=state.id).limit(3).all()
            for county in sample_counties:
                print(f"    - {county.name}")
            if county_count > 3:
                print(f"    ... and {county_count - 3} more")
            print()
        
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("Your Prospector application is now ready to search all US counties!")
        print("You can now start the app with: python3 app.py")

if __name__ == '__main__':
    try:
        populate_all_counties()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure you're in the correct directory and have all dependencies installed.")
        sys.exit(1)
