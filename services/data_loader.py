"""
Data loader service for US states and counties data.
This will populate the database with all US states and counties.
"""

from models import db, State, County
import json
from flask import current_app

class DataLoader:
    def __init__(self):
        pass
    
    def ensure_us_data_loaded(self):
        """Load US states and counties if not already present"""
        if State.query.count() == 0:
            self.load_states_and_counties()
        else:
            # Check if we need to add missing counties for existing states
            self.add_missing_counties()
    
    def load_states_and_counties(self):
        """Load all US states and counties from embedded data"""
        print("Loading US states and counties data...")
        
        # US States data
        states_data = [
            {"name": "Alabama", "abbreviation": "AL"},
            {"name": "Alaska", "abbreviation": "AK"},
            {"name": "Arizona", "abbreviation": "AZ"},
            {"name": "Arkansas", "abbreviation": "AR"},
            {"name": "California", "abbreviation": "CA"},
            {"name": "Colorado", "abbreviation": "CO"},
            {"name": "Connecticut", "abbreviation": "CT"},
            {"name": "Delaware", "abbreviation": "DE"},
            {"name": "Florida", "abbreviation": "FL"},
            {"name": "Georgia", "abbreviation": "GA"},
            {"name": "Hawaii", "abbreviation": "HI"},
            {"name": "Idaho", "abbreviation": "ID"},
            {"name": "Illinois", "abbreviation": "IL"},
            {"name": "Indiana", "abbreviation": "IN"},
            {"name": "Iowa", "abbreviation": "IA"},
            {"name": "Kansas", "abbreviation": "KS"},
            {"name": "Kentucky", "abbreviation": "KY"},
            {"name": "Louisiana", "abbreviation": "LA"},
            {"name": "Maine", "abbreviation": "ME"},
            {"name": "Maryland", "abbreviation": "MD"},
            {"name": "Massachusetts", "abbreviation": "MA"},
            {"name": "Michigan", "abbreviation": "MI"},
            {"name": "Minnesota", "abbreviation": "MN"},
            {"name": "Mississippi", "abbreviation": "MS"},
            {"name": "Missouri", "abbreviation": "MO"},
            {"name": "Montana", "abbreviation": "MT"},
            {"name": "Nebraska", "abbreviation": "NE"},
            {"name": "Nevada", "abbreviation": "NV"},
            {"name": "New Hampshire", "abbreviation": "NH"},
            {"name": "New Jersey", "abbreviation": "NJ"},
            {"name": "New Mexico", "abbreviation": "NM"},
            {"name": "New York", "abbreviation": "NY"},
            {"name": "North Carolina", "abbreviation": "NC"},
            {"name": "North Dakota", "abbreviation": "ND"},
            {"name": "Ohio", "abbreviation": "OH"},
            {"name": "Oklahoma", "abbreviation": "OK"},
            {"name": "Oregon", "abbreviation": "OR"},
            {"name": "Pennsylvania", "abbreviation": "PA"},
            {"name": "Rhode Island", "abbreviation": "RI"},
            {"name": "South Carolina", "abbreviation": "SC"},
            {"name": "South Dakota", "abbreviation": "SD"},
            {"name": "Tennessee", "abbreviation": "TN"},
            {"name": "Texas", "abbreviation": "TX"},
            {"name": "Utah", "abbreviation": "UT"},
            {"name": "Vermont", "abbreviation": "VT"},
            {"name": "Virginia", "abbreviation": "VA"},
            {"name": "Washington", "abbreviation": "WA"},
            {"name": "West Virginia", "abbreviation": "WV"},
            {"name": "Wisconsin", "abbreviation": "WI"},
            {"name": "Wyoming", "abbreviation": "WY"}
        ]
        
        # Create states
        state_objects = {}
        for state_data in states_data:
            state = State(name=state_data["name"], abbreviation=state_data["abbreviation"])
            db.session.add(state)
            state_objects[state_data["abbreviation"]] = state
        
        db.session.commit()
        print(f"Loaded {len(states_data)} states")
        
        # Load complete county data for all states
        self._load_all_counties(state_objects)
        
        db.session.commit()
        total_counties = County.query.count()
        print(f"Loaded {total_counties} counties")
        print("Data loading complete!")
    
    def add_missing_counties(self):
        """Add counties for states that don't have any counties yet"""
        sample_counties = {
            "CA": ["Los Angeles", "San Francisco", "San Diego", "Orange", "Riverside", "Sacramento"],
            "TX": ["Harris", "Dallas", "Tarrant", "Bexar", "Travis", "Collin"],
            "FL": ["Miami-Dade", "Broward", "Palm Beach", "Hillsborough", "Orange", "Pinellas"],
            "NY": ["New York", "Kings", "Queens", "Suffolk", "Nassau", "Bronx"],
            "DE": ["New Castle", "Kent", "Sussex"]  # Delaware has only 3 counties
        }
        
        for state_abbr, counties in sample_counties.items():
            state = State.query.filter_by(abbreviation=state_abbr).first()
            if state:
                # Check if this state already has counties
                existing_count = County.query.filter_by(state_id=state.id).count()
                if existing_count == 0:
                    print(f"Adding counties for {state.name}...")
                    for county_name in counties:
                        county = County(name=county_name, state_id=state.id)
                        db.session.add(county)
        
        db.session.commit()
        print("Missing counties added!")
    
    def load_full_county_data(self):
        """
        Load complete US county data from Census API or other source.
        This would be used in production to get all ~3,000+ counties.
        """
        # This is a placeholder for loading complete county data
        # You could integrate with Census API, use a CSV file, etc.
        pass
