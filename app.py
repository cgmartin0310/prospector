from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
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
from models import db, State, County, ProspectingJob, SearchResult, GoldenResult
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

@app.route('/migrate', methods=['POST'])
def run_migration():
    """Run the database migration"""
    try:
        import subprocess
        import sys
        
        # Run the migration script
        result = subprocess.run([
            sys.executable, 'migrate_county_organization_fields.py'
        ], capture_output=True, text=True, cwd='/opt/render/project/src')
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Migration completed successfully',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Migration failed',
                'output': result.stdout,
                'error_output': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
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
        'total_results': SearchResult.query.filter(SearchResult.organization_name.isnot(None)).count(),
        'states_available': states_with_counties,
        'golden_results': GoldenResult.query.count() if GoldenResult else 0
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
        'source_urls': result.source_urls,
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
        
        # Get state coverage statistics with explicit joins
        state_stats = db.session.query(
            State.abbreviation,
            State.name,
            func.count(distinct(SearchResult.organization_name)).label('team_count'),
            func.count(distinct(SearchResult.county_id)).label('counties_with_teams'),
            func.count(distinct(County.id)).label('total_counties')
        ).select_from(State).outerjoin(County, State.id == County.state_id).outerjoin(SearchResult, County.id == SearchResult.county_id).filter(SearchResult.organization_name.isnot(None)).group_by(State.id, State.abbreviation, State.name).all()
        
        # Get all states to ensure we include those with 0 organizations
        all_states = db.session.query(State.abbreviation, State.name).all()
        state_dict = {stat.abbreviation: stat for stat in state_stats}
        
        # Create complete map data including states with 0 organizations
        map_data = []
        for state in all_states:
            if state.abbreviation in state_dict:
                stat = state_dict[state.abbreviation]
                map_data.append({
                    'state_code': stat.abbreviation,
                    'state_name': stat.name,
                    'team_count': stat.team_count or 0,
                    'total_counties': stat.total_counties or 0,
                    'coverage_percentage': round((stat.team_count or 0) / max(stat.total_counties or 1, 1) * 100, 1)
                })
            else:
                # State with no organizations
                map_data.append({
                    'state_code': state.abbreviation,
                    'state_name': state.name,
                    'team_count': 0,
                    'total_counties': 0,
                    'coverage_percentage': 0.0
                })
        

        
        return jsonify({"success": True, "data": map_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/map/state/<state_abbr>')
def api_map_state_details(state_abbr):
    """Get county details for a specific state"""
    try:
        state = State.query.filter_by(abbreviation=state_abbr.upper()).first()
        if not state:
            return jsonify({"success": False, "error": "State not found"})
        
        # Get all counties in this state
        counties = County.query.filter_by(state_id=state.id).order_by(County.name).all()
        
        # Get existing search results for this state
        search_results = db.session.query(SearchResult).join(County).filter(
            County.state_id == state.id,
            SearchResult.organization_name.isnot(None)
        ).all()
        
        # Create a map of county_id to search result
        results_by_county = {}
        for result in search_results:
            results_by_county[result.county_id] = result
        
        counties_data = []
        for county in counties:
            result = results_by_county.get(county.id)
            
            county_data = {
                'id': county.id,
                'name': county.name,
                'fips_code': county.fips_code,
                'population': county.population,
                'has_result': result is not None,
                'result': None
            }
            
            if result:
                county_data['result'] = {
                    'id': result.id,
                    'organization_name': result.organization_name,
                    'key_personnel_name': result.key_personnel_name,
                    'key_personnel_title': result.key_personnel_title,
                    'key_personnel_phone': result.key_personnel_phone,
                    'key_personnel_email': result.key_personnel_email,
                    'confidence_score': result.confidence_score,
                    'created_at': result.created_at.strftime('%Y-%m-%d'),
                    'verified': getattr(result, 'verified', False)
                }
            
            counties_data.append(county_data)
        
        return jsonify({
            "success": True,
            "state": {
                "name": state.name,
                "abbreviation": state.abbreviation
            },
            "counties": counties_data
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
        
        return jsonify({
            "success": True,
            "job_id": job.id,
            "message": f"Search started for {state.name}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/county/<int:county_id>/search', methods=['POST'])
def api_county_search(county_id):
    """Search for organizations in a specific county"""
    try:
        data = request.get_json()
        search_query = data.get('search_query', 'overdose response team')
        
        county = County.query.get(county_id)
        if not county:
            return jsonify({"success": False, "error": "County not found"})
        
        # Create new job for this county
        job = ProspectingJob(
            search_query=search_query,
            state_id=county.state_id,
            status='pending'
        )
        db.session.add(job)
        db.session.commit()
        
        # Start the prospecting process in background with app context
        from services.prospector import ProspectorService
        
        def run_job_with_context(job_id, target_county_id):
            """Run job with Flask app context"""
            with app.app_context():
                prospector = ProspectorService()
                # Modify to only search the specific county
                prospector.run_job_for_county(job_id, target_county_id)
        
        thread = threading.Thread(target=run_job_with_context, args=(job.id, county_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "job_id": job.id,
            "message": f"Search started for {county.name} County"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/search-result/<int:result_id>/delete', methods=['DELETE'])
def api_delete_search_result(result_id):
    """Delete a search result"""
    try:
        result = SearchResult.query.get(result_id)
        if not result:
            return jsonify({"success": False, "error": "Search result not found"})
        
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Search result deleted successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/search-result/<int:result_id>/golden', methods=['POST'])
def api_mark_as_golden(result_id):
    """Mark a search result as golden"""
    try:
        result = SearchResult.query.get(result_id)
        if not result:
            return jsonify({"success": False, "error": "Search result not found"})
        
        result.verified = True
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Search result marked as golden"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/search-result/<int:result_id>', methods=['GET'])
def api_get_search_result(result_id):
    """Get a specific search result"""
    try:
        result = SearchResult.query.get(result_id)
        if not result:
            return jsonify({"success": False, "error": "Search result not found"})
        
        result_data = {
            'id': result.id,
            'organization_name': result.organization_name,
            'description': result.description,
            'key_personnel_name': result.key_personnel_name,
            'key_personnel_title': result.key_personnel_title,
            'key_personnel_phone': result.key_personnel_phone,
            'key_personnel_email': result.key_personnel_email,
            'address': result.address,
            'additional_notes': result.additional_notes,
            'confidence_score': result.confidence_score,
            'source_urls': result.source_urls,
            'contact_info': result.contact_info,
            'ai_response_raw': result.ai_response_raw,
            'created_at': result.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'verified': result.verified
        }
        
        return jsonify({
            "success": True,
            "result": result_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/search-result/<int:result_id>/update', methods=['PUT'])
def api_update_search_result(result_id):
    """Update a search result"""
    try:
        result = SearchResult.query.get(result_id)
        if not result:
            return jsonify({"success": False, "error": "Search result not found"})
        
        data = request.get_json()
        
        # Update fields if provided
        if 'organization_name' in data:
            result.organization_name = data['organization_name']
        if 'description' in data:
            result.description = data['description']
        if 'key_personnel_name' in data:
            result.key_personnel_name = data['key_personnel_name']
        if 'key_personnel_title' in data:
            result.key_personnel_title = data['key_personnel_title']
        if 'key_personnel_phone' in data:
            result.key_personnel_phone = data['key_personnel_phone']
        if 'key_personnel_email' in data:
            result.key_personnel_email = data['key_personnel_email']
        if 'address' in data:
            result.address = data['address']
        if 'additional_notes' in data:
            result.additional_notes = data['additional_notes']
        if 'confidence_score' in data:
            result.confidence_score = data['confidence_score']
        if 'source_urls' in data:
            result.source_urls = data['source_urls']
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Search result updated successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    """Search a specific county using AI"""
    try:
        data = request.get_json()
        search_query = data.get('search_query', 'overdose response team')
        
        county = County.query.get_or_404(county_id)
        
        # Perform AI research for this county
        from services.ai_service import AIService
        ai_service = AIService()
        
        research_result = ai_service.research_county(
            county_name=county.name,
            state_name=county.state.name,
            search_query=search_query
        )
        
        if research_result.get('success', False):
            # Find existing result for this county (if any)
            existing_result = SearchResult.query.filter_by(county_id=county_id).first()
            
            if existing_result:
                # Update existing result
                if research_result.get('organizations'):
                    best_org = max(research_result['organizations'], key=lambda x: x.get('confidence_score', 0))
                    existing_result.organization_name = best_org.get('organization_name')
                    existing_result.description = best_org.get('description')
                    existing_result.key_personnel_name = best_org.get('key_personnel_name')
                    existing_result.key_personnel_title = best_org.get('key_personnel_title')
                    existing_result.key_personnel_phone = best_org.get('key_personnel_phone')
                    existing_result.key_personnel_email = best_org.get('key_personnel_email')
                    existing_result.contact_info = json.dumps(best_org.get('contact_info', {}))
                    existing_result.address = best_org.get('address')
                    existing_result.confidence_score = best_org.get('confidence_score', 0.0)
                    existing_result.ai_response_raw = research_result.get('ai_response_raw', '')
                    existing_result.additional_notes = best_org.get('additional_notes')
                else:
                    # No organizations found, clear the result
                    existing_result.organization_name = None
                    existing_result.description = None
                    existing_result.key_personnel_name = None
                    existing_result.key_personnel_title = None
                    existing_result.key_personnel_phone = None
                    existing_result.key_personnel_email = None
                    existing_result.contact_info = '{}'
                    existing_result.address = None
                    existing_result.confidence_score = 0.0
                    existing_result.ai_response_raw = research_result.get('ai_response_raw', '')
                    existing_result.additional_notes = None
                
                db.session.commit()
                message = f"Updated result for {county.name} County"
            else:
                # Create new result
                if research_result.get('organizations'):
                    best_org = max(research_result['organizations'], key=lambda x: x.get('confidence_score', 0))
                    new_result = SearchResult(
                        county_id=county_id,
                        organization_name=best_org.get('organization_name'),
                        description=best_org.get('description'),
                        key_personnel_name=best_org.get('key_personnel_name'),
                        key_personnel_title=best_org.get('key_personnel_title'),
                        key_personnel_phone=best_org.get('key_personnel_phone'),
                        key_personnel_email=best_org.get('key_personnel_email'),
                        contact_info=json.dumps(best_org.get('contact_info', {})),
                        address=best_org.get('address'),
                        confidence_score=best_org.get('confidence_score', 0.0),
                        ai_response_raw=research_result.get('ai_response_raw', ''),
                        additional_notes=best_org.get('additional_notes')
                    )
                    db.session.add(new_result)
                    db.session.commit()
                    message = f"Found {len(research_result['organizations'])} organization(s) in {county.name} County"
                else:
                    # Create a "no results" record
                    new_result = SearchResult(
                        county_id=county_id,
                        organization_name=None,
                        confidence_score=0.0,
                        ai_response_raw=research_result.get('ai_response_raw', '')
                    )
                    db.session.add(new_result)
                    db.session.commit()
                    message = f"No organizations found in {county.name} County"
            
            return jsonify({
                "success": True,
                "message": message,
                "organizations_found": len(research_result.get('organizations', []))
            })
        else:
            return jsonify({
                "success": False,
                "error": research_result.get('error', 'AI research failed')
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/result/<int:result_id>/toggle-golden', methods=['POST'])
def api_toggle_golden(result_id):
    """Toggle golden status for a search result"""
    try:
        result = SearchResult.query.get_or_404(result_id)
        
        if not result.organization_name:
            return jsonify({"success": False, "error": "Cannot mark result as golden - no organization found"})
        
        if result.is_golden:
            # Remove from golden dataset
            result.is_golden = False
            
            # Also remove from GoldenResult table if it exists
            golden_result = GoldenResult.query.filter_by(
                organization_name=result.organization_name,
                county_id=result.county_id
            ).first()
            
            if golden_result:
                db.session.delete(golden_result)
            
            db.session.commit()
            message = f"Removed '{result.organization_name}' from Golden Dataset"
        else:
            # Add to golden dataset
            result.is_golden = True
            
            # Create GoldenResult entry
            golden_result = GoldenResult(
                organization_name=result.organization_name,
                description=result.description,
                services=json.dumps({
                    "overdose_response": True,
                    "harm_reduction": True,
                    "naloxone_distribution": True
                }),
                county_id=result.county_id,
                state_id=result.county.state_id,
                key_personnel_name=result.key_personnel_name,
                key_personnel_title=result.key_personnel_title,
                key_personnel_phone=result.key_personnel_phone,
                key_personnel_email=result.key_personnel_email,
                contact_info=result.contact_info,
                address=result.address,
                verification_source="Manual Verification",
                verified_by="User",
                search_query=result.job.search_query if result.job else "overdose response team",
                search_category="overdose_response",
                relevance_score=1.0,
                completeness_score=1.0,
                notes=f"Marked as golden by user - verified perfect match for {result.county.name} County"
            )
            
            db.session.add(golden_result)
            db.session.commit()
            message = f"Added '{result.organization_name}' to Golden Dataset"
        
        return jsonify({
            "success": True,
            "message": message,
            "is_golden": result.is_golden
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files including GeoJSON"""
    return send_file(f'static/{filename}')

@app.route('/golden-dataset')
def golden_dataset():
    """Golden Dataset management page"""
    golden_results = GoldenResult.query.order_by(GoldenResult.created_at.desc()).all()
    stats = {
        'total_golden': len(golden_results),
        'states_covered': len(set(r.state_id for r in golden_results)),
        'avg_relevance': sum(r.relevance_score for r in golden_results) / len(golden_results) if golden_results else 0,
        'avg_completeness': sum(r.completeness_score for r in golden_results) / len(golden_results) if golden_results else 0
    }
    return render_template('golden_dataset.html', golden_results=golden_results, stats=stats)

@app.route('/api/golden-dataset')
def api_golden_dataset():
    """API endpoint to get golden dataset for AI prompts"""
    try:
        golden_results = GoldenResult.query.all()
        return jsonify({
            "success": True,
            "data": [result.to_dict() for result in golden_results]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/golden-result/<int:result_id>')
def api_golden_result_details(result_id):
    """Get details of a specific golden result"""
    try:
        result = GoldenResult.query.get_or_404(result_id)
        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/golden-result/<int:result_id>/delete', methods=['DELETE'])
def api_delete_golden_result(result_id):
    """Delete a golden result"""
    try:
        result = GoldenResult.query.get_or_404(result_id)
        organization_name = result.organization_name
        
        # Also remove golden flag from corresponding SearchResult if it exists
        search_result = SearchResult.query.filter_by(
            organization_name=result.organization_name,
            county_id=result.county_id
        ).first()
        
        if search_result:
            search_result.is_golden = False
        
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Deleted golden result: {organization_name}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/golden-dataset/export')
def api_export_golden_dataset():
    """Export golden dataset as CSV"""
    try:
        golden_results = GoldenResult.query.all()
        
        # Create CSV content
        csv_content = "Organization,Description,County,State,Key Personnel,Title,Phone,Email,Address,Website,Services,Verification Source,Search Category,Relevance Score,Completeness Score,Notes\n"
        
        for result in golden_results:
            # Escape commas and quotes in CSV
            def escape_csv(value):
                if value is None:
                    return ""
                value = str(value).replace('"', '""')
                if ',' in value or '"' in value or '\n' in value:
                    return f'"{value}"'
                return value
            
            services = result.services if result.services else "{}"
            
            csv_content += f"{escape_csv(result.organization_name)}," \
                          f"{escape_csv(result.description)}," \
                          f"{escape_csv(result.county.name)}," \
                          f"{escape_csv(result.state.name)}," \
                          f"{escape_csv(result.key_personnel_name)}," \
                          f"{escape_csv(result.key_personnel_title)}," \
                          f"{escape_csv(result.key_personnel_phone)}," \
                          f"{escape_csv(result.key_personnel_email)}," \
                          f"{escape_csv(result.address)}," \
                          f"{escape_csv(result.website)}," \
                          f"{escape_csv(services)}," \
                          f"{escape_csv(result.verification_source)}," \
                          f"{escape_csv(result.search_category)}," \
                          f"{escape_csv(result.relevance_score)}," \
                          f"{escape_csv(result.completeness_score)}," \
                          f"{escape_csv(result.notes)}\n"
        
        # Create response
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=golden_dataset.csv'
        return response
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
