"""
Main prospecting service that coordinates the research process.
This service manages the county-by-county search process.
"""

import time
import json
from datetime import datetime
from flask import current_app
from models import db, State, County, ProspectingJob, SearchResult
from .ai_service import AIService

class ProspectorService:
    def __init__(self):
        self.ai_service = AIService()
    
    def run_job(self, job_id: int):
        """
        Run a prospecting job - search through all counties in a state.
        This runs in a background thread.
        Note: This method expects to be called within a Flask app context.
        """
        job = ProspectingJob.query.get(job_id)
        if not job:
            return
            
        try:
            # Update job status
            job.status = 'running'
            job.started_at = datetime.utcnow()
            db.session.commit()
            
            # Get all counties for this state
            counties = County.query.filter_by(state_id=job.state_id).order_by(County.name).all()
            state = State.query.get(job.state_id)
            
            print(f"Starting prospecting job {job_id}: '{job.search_query}' in {state.name}")
            print(f"Processing {len(counties)} counties...")
            
            for i, county in enumerate(counties):
                try:
                    # Update current county
                    job.current_county = county.name
                    db.session.commit()
                    
                    print(f"Processing {county.name} County ({i+1}/{len(counties)})...")
                    
                    # Check if we already have results for this county in this job
                    existing_result = SearchResult.query.filter_by(
                        job_id=job_id, 
                        county_id=county.id
                    ).first()
                    
                    if existing_result:
                        print(f"Skipping {county.name} - already processed")
                        continue
                    
                    # Conduct AI research for this county
                    research_result = self.ai_service.research_county(
                        county.name, 
                        state.name, 
                        job.search_query
                    )
                    
                    # Save results to database
                    self._save_research_results(job_id, county.id, research_result)
                    
                    # Delay between searches to be respectful to AI API
                    if i < len(counties) - 1:  # Don't delay after the last county
                        time.sleep(job.delay_between_searches)
                
                except Exception as e:
                    print(f"Error processing {county.name}: {str(e)}")
                    # Continue with next county even if one fails
                    continue
            
            # Mark job as completed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.current_county = None
            db.session.commit()
            
            results_count = SearchResult.query.filter_by(job_id=job_id).count()
            print(f"Job {job_id} completed! Found results in {results_count} counties.")
            
        except Exception as e:
            # Mark job as failed
            try:
                db.session.rollback()  # Roll back any pending transactions
                job = ProspectingJob.query.get(job_id)  # Refresh the job object
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.session.commit()
            except Exception as commit_error:
                print(f"Error updating job status: {str(commit_error)}")
                db.session.rollback()
            print(f"Job {job_id} failed: {str(e)}")
    
    def _save_research_results(self, job_id: int, county_id: int, research_result: dict):
        """Save the AI research results to the database"""
        
        if not research_result.get('success', False):
            # Save a record indicating no results found
            result = SearchResult(
                job_id=job_id,
                county_id=county_id,
                organization_name=None,
                description=f"Search failed: {research_result.get('error', 'Unknown error')}",
                ai_response_raw=research_result.get('raw_response', ''),
                confidence_score=0.0
            )
            db.session.add(result)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
            return
        
        organizations = research_result.get('organizations', [])
        
        if not organizations:
            # Save a record indicating no results found
            result = SearchResult(
                job_id=job_id,
                county_id=county_id,
                organization_name=None,
                description="No organizations found matching the search criteria",
                additional_notes=research_result.get('search_summary', ''),
                ai_response_raw=research_result.get('raw_response', ''),
                confidence_score=0.0
            )
            db.session.add(result)
        else:
            # Save each organization found
            for org in organizations:
                # Handle key personnel information
                key_personnel = org.get('key_personnel', {})
                general_contact = org.get('general_contact', {})
                
                # Convert general contact to JSON string for backward compatibility
                contact_info = json.dumps(general_contact)
                
                result = SearchResult(
                    job_id=job_id,
                    county_id=county_id,
                    organization_name=org.get('name', 'Unknown'),
                    description=org.get('description', ''),
                    
                    # Key personnel information
                    key_personnel_name=key_personnel.get('name', ''),
                    key_personnel_title=key_personnel.get('title', ''),
                    key_personnel_phone=key_personnel.get('phone', ''),
                    key_personnel_email=key_personnel.get('email', ''),
                    
                    # General contact information
                    contact_info=contact_info,
                    address=org.get('address', ''),
                    additional_notes=org.get('notes', ''),
                    confidence_score=org.get('confidence', 0.7),
                    ai_response_raw=research_result.get('raw_response', '')
                )
                db.session.add(result)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def pause_job(self, job_id: int):
        """Pause a running job"""
        job = ProspectingJob.query.get(job_id)
        if job and job.status == 'running':
            job.status = 'paused'
            db.session.commit()
            return True
        return False
    
    def resume_job(self, job_id: int):
        """Resume a paused job"""
        job = ProspectingJob.query.get(job_id)
        if job and job.status == 'paused':
            # Restart the job in a new thread
            import threading
            thread = threading.Thread(target=self.run_job, args=(job_id,))
            thread.daemon = True
            thread.start()
            return True
        return False
    
    def get_job_progress(self, job_id: int) -> dict:
        """Get detailed progress information for a job"""
        job = ProspectingJob.query.get(job_id)
        if not job:
            return None
        
        total_counties = County.query.filter_by(state_id=job.state_id).count()
        # Count unique counties processed, not total results
        processed_counties = db.session.query(SearchResult.county_id).filter_by(job_id=job_id).distinct().count()
        
        # Count organizations found
        organizations_found = SearchResult.query.filter_by(job_id=job_id).filter(
            SearchResult.organization_name.isnot(None)
        ).count()
        
        return {
            'job_id': job_id,
            'status': job.status,
            'current_county': job.current_county,
            'progress': {
                'total_counties': total_counties,
                'processed_counties': processed_counties,
                'percentage': round((processed_counties / total_counties) * 100, 1) if total_counties > 0 else 0
            },
            'results': {
                'organizations_found': organizations_found,
                'counties_with_results': processed_counties
            },
            'timing': {
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            }
        }
