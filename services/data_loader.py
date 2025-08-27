"""
Data loader service for US states and counties data.
This will populate the database with all US states and counties.
"""

from models import db, State, County
import json
import requests
from flask import current_app

class DataLoader:
    def __init__(self):
        pass
    
    def ensure_us_data_loaded(self):
        """Load US states and counties if not already present"""
        if State.query.count() == 0:
            self.load_states_and_counties()
    
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
        
        # Sample counties for North Carolina (since that's your primary use case)
        # In a real implementation, you'd want to load all ~3,000+ US counties
        nc_counties = [
            "Alamance", "Alexander", "Alleghany", "Anson", "Ashe", "Avery", "Beaufort", 
            "Bertie", "Bladen", "Brunswick", "Buncombe", "Burke", "Cabarrus", "Caldwell", 
            "Camden", "Carteret", "Caswell", "Catawba", "Chatham", "Cherokee", "Chowan", 
            "Clay", "Cleveland", "Columbus", "Craven", "Cumberland", "Currituck", "Dare", 
            "Davidson", "Davie", "Duplin", "Durham", "Edgecombe", "Forsyth", "Franklin", 
            "Gaston", "Gates", "Graham", "Granville", "Greene", "Guilford", "Halifax", 
            "Harnett", "Haywood", "Henderson", "Hertford", "Hoke", "Hyde", "Iredell", 
            "Jackson", "Johnston", "Jones", "Lee", "Lenoir", "Lincoln", "McDowell", 
            "Macon", "Madison", "Martin", "Mecklenburg", "Mitchell", "Montgomery", 
            "Moore", "Nash", "New Hanover", "Northampton", "Onslow", "Orange", "Pamlico", 
            "Pasquotank", "Pender", "Perquimans", "Person", "Pitt", "Polk", "Randolph", 
            "Richmond", "Robeson", "Rockingham", "Rowan", "Rutherford", "Sampson", 
            "Scotland", "Stanly", "Stokes", "Surry", "Swain", "Transylvania", "Tyrrell", 
            "Union", "Vance", "Wake", "Warren", "Washington", "Watauga", "Wayne", 
            "Wilkes", "Wilson", "Yadkin", "Yancey"
        ]
        
        nc_state = state_objects["NC"]
        for county_name in nc_counties:
            county = County(name=county_name, state_id=nc_state.id)
            db.session.add(county)
        
        # Add some sample counties for other states too
        sample_counties = {
            "CA": ["Los Angeles", "San Francisco", "San Diego", "Orange", "Riverside", "Sacramento"],
            "TX": ["Harris", "Dallas", "Tarrant", "Bexar", "Travis", "Collin"],
            "FL": ["Miami-Dade", "Broward", "Palm Beach", "Hillsborough", "Orange", "Pinellas"],
            "NY": ["New York", "Kings", "Queens", "Suffolk", "Nassau", "Bronx"]
        }
        
        for state_abbr, counties in sample_counties.items():
            state = state_objects[state_abbr]
            for county_name in counties:
                county = County(name=county_name, state_id=state.id)
                db.session.add(county)
        
        db.session.commit()
        total_counties = County.query.count()
        print(f"Loaded {total_counties} counties")
        print("Data loading complete!")
    
    def load_full_county_data(self):
        """
        Load complete US county data from Census API or other source.
        This would be used in production to get all ~3,000+ counties.
        """
        # This is a placeholder for loading complete county data
        # You could integrate with Census API, use a CSV file, etc.
        pass
