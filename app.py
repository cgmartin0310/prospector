from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import Config
import threading
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
from models import db, State, County, ProspectingJob, SearchResult
db.init_app(app)

# Custom template filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """Main dashboard showing recent jobs and stats"""
    recent_jobs = ProspectingJob.query.order_by(ProspectingJob.created_at.desc()).limit(10).all()
    stats = {
        'total_jobs': ProspectingJob.query.count(),
        'active_jobs': ProspectingJob.query.filter_by(status='running').count(),
        'total_results': SearchResult.query.count(),
        'states_available': State.query.count()
    }
    return render_template('index.html', recent_jobs=recent_jobs, stats=stats)

@app.route('/start-search')
def start_search_form():
    """Form to start a new prospecting search"""
    states = State.query.order_by(State.name).all()
    return render_template('start_search.html', states=states)

@app.route('/start-search', methods=['POST'])
def start_search():
    """Start a new prospecting job"""
    search_query = request.form.get('search_query')
    state_id = request.form.get('state_id')
    
    if not search_query or not state_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Create new job
    job = ProspectingJob(
        search_query=search_query,
        state_id=state_id,
        status='pending'
    )
    db.session.add(job)
    db.session.commit()
    
    # Start the prospecting process in background
    from services.prospector import ProspectorService
    prospector = ProspectorService()
    thread = threading.Thread(target=prospector.run_job, args=(job.id,))
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('job_status', job_id=job.id))

@app.route('/job/<int:job_id>')
def job_status(job_id):
    """Show status and results for a specific job"""
    job = ProspectingJob.query.get_or_404(job_id)
    results = SearchResult.query.filter_by(job_id=job_id).all()
    return render_template('job_status.html', job=job, results=results)

@app.route('/api/job/<int:job_id>/status')
def api_job_status(job_id):
    """API endpoint for job status updates"""
    job = ProspectingJob.query.get_or_404(job_id)
    counties_total = County.query.filter_by(state_id=job.state_id).count()
    counties_processed = SearchResult.query.filter_by(job_id=job_id).count()
    
    return jsonify({
        'status': job.status,
        'progress': {
            'total': counties_total,
            'processed': counties_processed,
            'percentage': round((counties_processed / counties_total) * 100, 1) if counties_total > 0 else 0
        },
        'current_county': job.current_county,
        'results_count': SearchResult.query.filter_by(job_id=job_id).count()
    })

@app.route('/results')
def view_results():
    """View all search results with filtering"""
    page = request.args.get('page', 1, type=int)
    job_id = request.args.get('job_id', type=int)
    
    query = SearchResult.query
    if job_id:
        query = query.filter_by(job_id=job_id)
    
    results = query.order_by(SearchResult.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    jobs = ProspectingJob.query.order_by(ProspectingJob.created_at.desc()).all()
    return render_template('results.html', results=results, jobs=jobs, current_job_id=job_id)

@app.route('/api/result/<int:result_id>')
def api_result_details(result_id):
    """API endpoint for result details"""
    result = SearchResult.query.get_or_404(result_id)
    return jsonify({
        'id': result.id,
        'organization_name': result.organization_name,
        'description': result.description,
        'contact_info': result.contact_info,
        'address': result.address,
        'additional_notes': result.additional_notes,
        'confidence_score': result.confidence_score,
        'ai_response_raw': result.ai_response_raw,
        'created_at': result.created_at.isoformat(),
        'county_name': result.county.name,
        'state_name': result.county.state.name,
        'job_id': result.job_id,
        'job_search_query': result.job.search_query
    })

@app.route('/api/job/<int:job_id>/export')
def api_export_job_results(job_id):
    """Export job results as CSV"""
    import csv
    import io
    from flask import Response
    
    job = ProspectingJob.query.get_or_404(job_id)
    results = SearchResult.query.filter_by(job_id=job_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'County', 'State', 'Organization Name', 'Description', 
        'Address', 'Contact Info', 'Additional Notes', 
        'Confidence Score', 'Found Date'
    ])
    
    # Write data
    for result in results:
        writer.writerow([
            result.county.name,
            result.county.state.name,
            result.organization_name or '',
            result.description or '',
            result.address or '',
            result.contact_info or '',
            result.additional_notes or '',
            result.confidence_score,
            result.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=job_{job_id}_results.csv'
        }
    )

def init_db():
    """Initialize database and load initial data"""
    with app.app_context():
        db.create_all()
        # Initialize data if needed
        from services.data_loader import DataLoader
        loader = DataLoader()
        loader.ensure_us_data_loaded()

# Initialize database on startup
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
