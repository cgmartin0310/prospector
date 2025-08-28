from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    abbreviation = db.Column(db.String(2), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    counties = db.relationship('County', backref='state', lazy=True)
    jobs = db.relationship('ProspectingJob', backref='state', lazy=True)
    
    def __repr__(self):
        return f'<State {self.name}>'

class County(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    fips_code = db.Column(db.String(5), unique=True)  # Federal Information Processing Standards code
    population = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    search_results = db.relationship('SearchResult', backref='county', lazy=True)
    
    def __repr__(self):
        return f'<County {self.name}, {self.state.abbreviation}>'

class ProspectingJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.Text, nullable=False)  # What we're looking for
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed, paused
    current_county = db.Column(db.String(100))  # Current county being processed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Settings
    delay_between_searches = db.Column(db.Integer, default=5)  # Seconds between county searches
    max_results_per_county = db.Column(db.Integer, default=10)
    
    # Relationships
    search_results = db.relationship('SearchResult', backref='job', lazy=True)
    
    @property
    def progress_percentage(self):
        if self.status not in ['running', 'completed']:
            return 0
        
        total_counties = County.query.filter_by(state_id=self.state_id).count()
        # Count unique counties that have been processed (not total results)
        processed_counties = db.session.query(SearchResult.county_id).filter_by(job_id=self.id).distinct().count()
        
        if total_counties == 0:
            return 0
        
        return round((processed_counties / total_counties) * 100, 1)
    
    def __repr__(self):
        return f'<ProspectingJob {self.id}: {self.search_query[:50]}...>'

class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('prospecting_job.id'), nullable=False)
    county_id = db.Column(db.Integer, db.ForeignKey('county.id'), nullable=False)
    
    # Result data
    organization_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    # Key personnel information (NEW)
    key_personnel_name = db.Column(db.String(200))  # Name of director/manager/coordinator
    key_personnel_title = db.Column(db.String(100))  # Their title
    key_personnel_phone = db.Column(db.String(50))   # Direct phone number
    key_personnel_email = db.Column(db.String(200))  # Direct email address
    
    # General contact information (UPDATED)
    contact_info = db.Column(db.Text)  # JSON string with general phone, email, website, etc.
    address = db.Column(db.Text)
    additional_notes = db.Column(db.Text)
    
    # Metadata
    confidence_score = db.Column(db.Float, default=0.0)  # AI confidence in the result
    source_urls = db.Column(db.Text)  # JSON array of source URLs
    ai_response_raw = db.Column(db.Text)  # Raw AI response for debugging
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status
    verified = db.Column(db.Boolean, default=False)
    duplicate_of = db.Column(db.Integer, db.ForeignKey('search_result.id'))
    
    def __repr__(self):
        return f'<SearchResult {self.organization_name} in {self.county.name}>'
