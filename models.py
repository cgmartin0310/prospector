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
    
    # Organization data (nullable - county exists even without results)
    organization_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    key_personnel_name = db.Column(db.String(200))
    key_personnel_title = db.Column(db.String(100))
    key_personnel_phone = db.Column(db.String(50))
    key_personnel_email = db.Column(db.String(200))
    contact_info = db.Column(db.Text)  # JSON string
    address = db.Column(db.Text)
    additional_notes = db.Column(db.Text)
    confidence_score = db.Column(db.Float, default=0.0)
    source_urls = db.Column(db.Text)  # JSON array of source URLs
    ai_response_raw = db.Column(db.Text)  # Raw AI response for debugging
    last_searched_at = db.Column(db.DateTime)
    search_query = db.Column(db.Text)  # Last search query used
    
    # Status
    verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    search_results = db.relationship('SearchResult', backref='county', lazy=True)
    
    def __repr__(self):
        return f'<County {self.name}, {self.state.abbreviation}>'
    
    @property
    def has_organization(self):
        """Check if this county has an organization result"""
        return self.organization_name is not None and self.organization_name.strip() != ''

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
    
    # Golden dataset flag
    is_golden = db.Column(db.Boolean, default=False)  # Marked as verified perfect match
    
    def __repr__(self):
        return f'<SearchResult {self.organization_name} in {self.county.name}>'

class GoldenResult(db.Model):
    """Golden dataset of verified, high-quality matches for improving AI searches"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Organization details
    organization_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    services = db.Column(db.Text)  # JSON string of specific services offered
    
    # Location
    county_id = db.Column(db.Integer, db.ForeignKey('county.id'), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    
    # Contact information
    key_personnel_name = db.Column(db.String(200))
    key_personnel_title = db.Column(db.String(100))
    key_personnel_phone = db.Column(db.String(50))
    key_personnel_email = db.Column(db.String(200))
    contact_info = db.Column(db.Text)  # JSON string
    address = db.Column(db.Text)
    website = db.Column(db.String(500))
    
    # Verification details
    verification_source = db.Column(db.String(200))  # e.g., "SAMHSA", "County Health Dept", "Manual Verification"
    verification_date = db.Column(db.DateTime, default=datetime.utcnow)
    verified_by = db.Column(db.String(100))  # Who verified this result
    
    # Search context
    search_query = db.Column(db.Text)  # Original search query that found this
    search_category = db.Column(db.String(100))  # e.g., "overdose response", "harm reduction", "naloxone distribution"
    
    # Quality metrics
    relevance_score = db.Column(db.Float, default=1.0)  # How relevant this is (1.0 = perfect)
    completeness_score = db.Column(db.Float, default=1.0)  # How complete the information is
    
    # Metadata
    notes = db.Column(db.Text)  # Additional notes about why this is a good example
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    county = db.relationship('County', backref='golden_results')
    state = db.relationship('State', backref='golden_results')
    
    def __repr__(self):
        return f'<GoldenResult {self.organization_name} in {self.county.name}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'organization_name': self.organization_name,
            'description': self.description,
            'services': self.services,
            'county': self.county.name,
            'state': self.state.name,
            'key_personnel_name': self.key_personnel_name,
            'key_personnel_title': self.key_personnel_title,
            'key_personnel_phone': self.key_personnel_phone,
            'key_personnel_email': self.key_personnel_email,
            'contact_info': self.contact_info,
            'address': self.address,
            'website': self.website,
            'verification_source': self.verification_source,
            'search_category': self.search_category,
            'relevance_score': self.relevance_score,
            'completeness_score': self.completeness_score,
            'notes': self.notes
        }
