from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from config import Config
import threading
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Create static directory if it doesn't exist
os.makedirs('static', exist_ok=True)

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
    
    # Count only states that have counties available for searching
    states_with_counties = db.session.query(State.id).join(County).group_by(State.id).count()
    
    stats = {
        'total_jobs': ProspectingJob.query.count(),
        'active_jobs': ProspectingJob.query.filter_by(status='running').count(),
        'total_results': SearchResult.query.count(),
        'states_available': states_with_counties
    }
    return render_template('index.html', recent_jobs=recent_jobs, stats=stats)

@app.route('/start-search')
def start_search_form():
    """Form to start a new prospecting search"""
    # Only show states that have counties available for searching
    states = State.query.join(County).group_by(State.id).order_by(State.name).all()
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
    
    # Start the prospecting process in background with app context
    from services.prospector import ProspectorService
    
    def run_job_with_context(job_id):
        """Run job with Flask app context"""
        with app.app_context():
            prospector = ProspectorService()
            prospector.run_job(job_id)
    
    thread = threading.Thread(target=run_job_with_context, args=(job.id,))
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
    # Count unique counties processed, not total results
    counties_processed = db.session.query(SearchResult.county_id).filter_by(job_id=job_id).distinct().count()
    
    return jsonify({
        'status': job.status,
        'progress': {
            'total': counties_total,
            'processed': counties_processed,
            'percentage': round((counties_processed / counties_total) * 100, 1) if counties_total > 0 else 0
        },
        'current_county': job.current_county,
        'results_count': SearchResult.query.filter_by(job_id=job_id).filter(SearchResult.organization_name.isnot(None)).count()
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
        'job_search_query': result.job.search_query,
        # Key personnel information
        'key_personnel_name': result.key_personnel_name,
        'key_personnel_title': result.key_personnel_title,
        'key_personnel_phone': result.key_personnel_phone,
        'key_personnel_email': result.key_personnel_email
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
        'Key Personnel Name', 'Key Personnel Title', 'Key Personnel Phone', 'Key Personnel Email',
        'General Phone', 'General Email', 'General Website', 'Address', 'Additional Notes', 
        'Confidence Score', 'Found Date'
    ])
    
    # Write data
    for result in results:
        # Parse general contact info
        general_contact = {}
        if result.contact_info:
            try:
                general_contact = json.loads(result.contact_info)
            except:
                general_contact = {}
        
        writer.writerow([
            result.county.name,
            result.county.state.name,
            result.organization_name or '',
            result.description or '',
            result.key_personnel_name or '',
            result.key_personnel_title or '',
            result.key_personnel_phone or '',
            result.key_personnel_email or '',
            general_contact.get('phone', ''),
            general_contact.get('email', ''),
            general_contact.get('website', ''),
            result.address or '',
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

@app.route('/api/result/<int:result_id>/delete', methods=['DELETE', 'POST'])
def api_delete_result(result_id):
    """Delete an individual search result"""
    try:
        result = SearchResult.query.get_or_404(result_id)
        
        # Store information for the response
        organization_name = result.organization_name or "Unknown Organization"
        county_name = result.county.name
        state_name = result.county.state.name
        job_id = result.job_id
        
        # Check if the associated job is currently running
        job = ProspectingJob.query.get(job_id)
        if job and job.status == 'running':
            return jsonify({
                'success': False,
                'error': 'Cannot delete results from a job that is currently running. Please wait for it to complete.'
            }), 400
        
        # Delete the result
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted result "{organization_name}" from {county_name}, {state_name}.',
            'job_id': job_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete result: {str(e)}'
        }), 500

@app.route('/api/job/<int:job_id>/pause', methods=['POST'])
def api_pause_job(job_id):
    """Pause a running job"""
    try:
        job = ProspectingJob.query.get_or_404(job_id)
        
        if job.status != 'running':
            return jsonify({
                'success': False,
                'error': f'Cannot pause job with status: {job.status}. Only running jobs can be paused.'
            }), 400
        
        # Update job status to paused
        job.status = 'paused'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Job #{job_id} has been paused. You can resume it later or delete it.',
            'new_status': 'paused'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to pause job: {str(e)}'
        }), 500

@app.route('/api/job/<int:job_id>/resume', methods=['POST'])
def api_resume_job(job_id):
    """Resume a paused job"""
    try:
        job = ProspectingJob.query.get_or_404(job_id)
        
        if job.status != 'paused':
            return jsonify({
                'success': False,
                'error': f'Cannot resume job with status: {job.status}. Only paused jobs can be resumed.'
            }), 400
        
        # Update job status and restart
        job.status = 'running'
        job.current_county = None  # Will be set when processing resumes
        db.session.commit()
        
        # Start the prospecting process in background
        from services.prospector import ProspectorService
        
        def run_job_with_context(job_id):
            """Run job with Flask app context"""
            with app.app_context():
                prospector = ProspectorService()
                prospector.run_job(job_id)
        
        import threading
        thread = threading.Thread(target=run_job_with_context, args=(job.id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Job #{job_id} has been resumed and is now running.',
            'new_status': 'running'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to resume job: {str(e)}'
        }), 500

@app.route('/api/job/<int:job_id>/force-stop', methods=['POST'])
def api_force_stop_job(job_id):
    """Force stop a stuck job and mark it as failed"""
    try:
        job = ProspectingJob.query.get_or_404(job_id)
        
        if job.status not in ['running', 'paused']:
            return jsonify({
                'success': False,
                'error': f'Cannot force stop job with status: {job.status}.'
            }), 400
        
        # Force stop the job
        job.status = 'failed'
        job.error_message = 'Job was force stopped due to being stuck or unresponsive'
        job.completed_at = datetime.utcnow()
        job.current_county = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Job #{job_id} has been force stopped and marked as failed. You can now delete it if needed.',
            'new_status': 'failed'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to force stop job: {str(e)}'
        }), 500

@app.route('/api/job/<int:job_id>/delete', methods=['DELETE', 'POST'])
def api_delete_job(job_id):
    """Delete a job and all its associated results"""
    try:
        job = ProspectingJob.query.get_or_404(job_id)
        
        # Check if job is currently running
        if job.status == 'running':
            return jsonify({
                'success': False,
                'error': 'Cannot delete a job that is currently running. Please wait for it to complete or pause it first.'
            }), 400
        
        # Delete all associated search results first (due to foreign key constraints)
        results_count = SearchResult.query.filter_by(job_id=job_id).count()
        SearchResult.query.filter_by(job_id=job_id).delete()
        
        # Delete the job
        job_query = job.search_query[:50] + '...' if len(job.search_query) > 50 else job.search_query
        state_name = job.state.name
        
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted job "{job_query}" for {state_name} and {results_count} associated results.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete job: {str(e)}'
        }), 500

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
# Add this to your app.py file

@app.route('/admin/populate-counties')
def populate_all_counties():
    """Admin endpoint to populate all US counties using comprehensive dataset"""
    try:
        from services.data_loader import DataLoader
        
        # Get current count
        initial_counties = County.query.count()
        
        # Load counties using our comprehensive dataset
        loader = DataLoader()
        state_objects = {state.abbreviation: state for state in State.query.all()}
        counties_added = loader._load_all_counties_from_data(state_objects)
        db.session.commit()
        
        final_counties = County.query.count()
        
        return jsonify({
            "success": True,
            "message": f"Successfully populated counties database",
            "counties_added": counties_added,
            "initial_count": initial_counties,
            "final_count": final_counties,
            "states_with_counties": [
                {
                    "state": state.name,
                    "abbreviation": state.abbreviation,
                    "county_count": County.query.filter_by(state_id=state.id).count()
                } for state in State.query.order_by(State.name).all()
                if County.query.filter_by(state_id=state.id).count() > 0
            ]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/admin/migrate-database')
def admin_migrate_database():
    """Admin endpoint to trigger database migration"""
    try:
        from migrate_database import migrate_database
        migrate_database()
        return jsonify({"success": True, "message": "Database migration completed successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/map')
def map_dashboard():
    """Interactive US map dashboard"""
    return render_template('map_dashboard.html')

@app.route('/api/map/states')
def api_map_states():
    """Get state-level statistics for map visualization"""
    try:
        from sqlalchemy import func, distinct
        
        # Get state coverage statistics
        state_stats = db.session.query(
            State.abbreviation,
            State.name,
            func.count(SearchResult.id).label('team_count'),
            func.count(distinct(SearchResult.county_id)).label('counties_with_teams'),
            func.count(distinct(County.id)).label('total_counties')
        ).outerjoin(County).outerjoin(SearchResult, County.id == SearchResult.county_id).group_by(State.id, State.abbreviation, State.name).all()
        
        # Format data for frontend
        map_data = []
        for stat in state_stats:
            map_data.append({
                'state_code': stat.abbreviation,
                'state_name': stat.name,
                'team_count': stat.team_count or 0,
                'counties_with_teams': stat.counties_with_teams or 0,
                'total_counties': stat.total_counties or 0,
                'coverage_percentage': round((stat.counties_with_teams or 0) / max(stat.total_counties or 1, 1) * 100, 1)
            })
        
        return jsonify({"success": True, "data": map_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/map/state/<state_abbr>')
def api_map_state_details(state_abbr):
    """Get detailed results for a specific state"""
    try:
        state = State.query.filter_by(abbreviation=state_abbr.upper()).first()
        if not state:
            return jsonify({"success": False, "error": "State not found"})
        
        # Get existing teams in this state
        teams = db.session.query(SearchResult).join(County).filter(
            County.state_id == state.id,
            SearchResult.organization_name.isnot(None)
        ).order_by(SearchResult.confidence_score.desc()).limit(20).all()
        
        # Get recent jobs for this state
        recent_jobs = ProspectingJob.query.filter_by(state_id=state.id).order_by(
            ProspectingJob.created_at.desc()
        ).limit(5).all()
        
        team_data = []
        for team in teams:
            team_data.append({
                'id': team.id,
                'organization_name': team.organization_name,
                'county': team.county.name,
                'key_personnel_name': team.key_personnel_name,
                'key_personnel_title': team.key_personnel_title,
                'key_personnel_phone': team.key_personnel_phone,
                'key_personnel_email': team.key_personnel_email,
                'confidence_score': team.confidence_score,
                'created_at': team.created_at.strftime('%Y-%m-%d')
            })
        
        job_data = []
        for job in recent_jobs:
            job_data.append({
                'id': job.id,
                'search_query': job.search_query,
                'status': job.status,
                'progress_percentage': job.progress_percentage,
                'created_at': job.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            "success": True,
            "state": {
                "name": state.name,
                "abbreviation": state.abbreviation
            },
            "teams": team_data,
            "recent_jobs": job_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/map/start-search/<state_abbr>', methods=['POST'])
def api_map_start_search(state_abbr):
    """Start a new search from map interface"""
    try:
        data = request.get_json()
        search_query = data.get('search_query', 'overdose response team')
        
        state = State.query.filter_by(abbreviation=state_abbr.upper()).first()
        if not state:
            return jsonify({"success": False, "error": "State not found"})
        
        # Create new job
        job = ProspectingJob(
            search_query=search_query,
            state_id=state.id,
            status='pending'
        )
        db.session.add(job)
        db.session.commit()
        
        # Start the job in background
        from services.prospector import ProspectorService
        prospector = ProspectorService()
        prospector.start_job(job.id)
        
        return jsonify({
            "success": True,
            "job_id": job.id,
            "message": f"Search started for {state.name}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files including GeoJSON"""
    return send_file(f'static/{filename}')
