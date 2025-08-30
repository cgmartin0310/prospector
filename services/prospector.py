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
                    
                    # Conduct AI research for this county
                    research_result = self.ai_service.research_county(
                        county.name, 
                        state.name, 
                        job.search_query
                    )
                    
                    print(f"AI research completed for {county.name} County")
                    
                    # Save or update the result for this county
                    self._save_or_update_county_result(job_id, county.id, research_result)
                    
                    print(f"Result saved/updated for {county.name} County")
                    
                    # Delay between searches to be respectful to AI API
                    if i < len(counties) - 1:  # Don't delay after the last county
                        print(f"Waiting {job.delay_between_searches} seconds before next county...")
                        time.sleep(job.delay_between_searches)
                
                except Exception as e:
                    print(f"Error processing {county.name}: {str(e)}")
                    print(f"Continuing to next county...")
                    # Continue with next county even if one fails
                    continue
            
            print(f"All {len(counties)} counties processed. Marking job as completed.")
            
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
    

    
    def run_job_for_county(self, job_id: int, county_id: int):
        """
        Run a prospecting job for a specific county only.
        This runs in a background thread.
        Note: This method expects to be called within a Flask app context.
        """
        job = ProspectingJob.query.get(job_id)
        if not job:
            return
            
        county = County.query.get(county_id)
        if not county:
            return
            
        state = State.query.get(county.state_id)
        if not state:
            return
            
        try:
            # Update job status
            job.status = 'running'
            job.started_at = datetime.utcnow()
            job.current_county = county.name
            db.session.commit()
            
            print(f"Starting prospecting job {job_id} for {county.name} County, {state.name}")
            print(f"Search query: '{job.search_query}'")
            
            # Conduct AI research for this specific county
            research_result = self.ai_service.research_county(
                county.name, 
                state.name, 
                job.search_query
            )
            
            print(f"AI research completed for {county.name} County")
            
            # Save or update the result for this county
            self._save_or_update_county_result(job_id, county.id, research_result)
            
            print(f"Result saved/updated for {county.name} County")
            
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

    def _save_or_update_county_result(self, job_id: int, county_id: int, research_result: dict):
        """
        Saves or updates a SearchResult for a given county.
        If an existing result exists, it will be replaced if the new result has a higher confidence score.
        """
        county_name = County.query.get(county_id).name
        
        if not research_result.get('success', False):
            print(f"AI research failed for {county_name} County")
            # If AI research failed, save a record for progress tracking
            existing_result = SearchResult.query.filter_by(
                job_id=job_id, 
                county_id=county_id
            ).first()
            
            if existing_result:
                # Update existing record to indicate research failed
                existing_result.organization_name = None
                existing_result.description = f"Search failed: {research_result.get('error', 'Unknown error')}"
                existing_result.confidence_score = 0.0
                existing_result.ai_response_raw = research_result.get('raw_response', '')
                # Clear key personnel fields
                existing_result.key_personnel_name = ''
                existing_result.key_personnel_title = ''
                existing_result.key_personnel_phone = ''
                existing_result.key_personnel_email = ''
                existing_result.contact_info = '{}'
                db.session.commit()
                print(f"Updated existing result for {county_name} to indicate research failed.")
            else:
                # Create new record to indicate research failed
                result = SearchResult(
                    job_id=job_id,
                    county_id=county_id,
                    organization_name=None,
                    description=f"Search failed: {research_result.get('error', 'Unknown error')}",
                    confidence_score=0.0,
                    ai_response_raw=research_result.get('raw_response', ''),
                    key_personnel_name='',
                    key_personnel_title='',
                    key_personnel_phone='',
                    key_personnel_email='',
                    contact_info='{}'
                )
                db.session.add(result)
                db.session.commit()
                print(f"Saved 'research failed' record for {county_name} County.")
            return

        organizations = research_result.get('organizations', [])

        if not organizations:
            print(f"No organizations found for {county_name} County")
            # If AI research found no organizations, save a "no results" record for progress tracking
            existing_result = SearchResult.query.filter_by(
                job_id=job_id, 
                county_id=county_id
            ).first()
            
            if existing_result:
                # Update existing record to indicate no organizations found
                existing_result.organization_name = None
                existing_result.description = "No organizations found matching the search criteria"
                existing_result.additional_notes = research_result.get('search_summary', '')
                existing_result.confidence_score = 0.0
                existing_result.ai_response_raw = research_result.get('raw_response', '')
                # Clear key personnel fields
                existing_result.key_personnel_name = ''
                existing_result.key_personnel_title = ''
                existing_result.key_personnel_phone = ''
                existing_result.key_personnel_email = ''
                existing_result.contact_info = '{}'
                db.session.commit()
                print(f"Updated existing result for {county_name} to indicate no organizations found.")
            else:
                # Create new record to indicate no organizations found
                result = SearchResult(
                    job_id=job_id,
                    county_id=county_id,
                    organization_name=None,
                    description="No organizations found matching the search criteria",
                    additional_notes=research_result.get('search_summary', ''),
                    confidence_score=0.0,
                    ai_response_raw=research_result.get('raw_response', ''),
                    key_personnel_name='',
                    key_personnel_title='',
                    key_personnel_phone='',
                    key_personnel_email='',
                    contact_info='{}'
                )
                db.session.add(result)
                db.session.commit()
                print(f"Saved 'no results' record for {county_name} County.")
            return

        # Find the organization with the highest confidence score
        best_org = max(organizations, key=lambda org: org.get('confidence', 0.0))
        print(f"Found {len(organizations)} organizations for {county_name} County, best confidence: {best_org.get('confidence', 0.0):.2f}")

        # Convert general contact to JSON string for backward compatibility
        contact_info = json.dumps(best_org.get('general_contact', {}))

        # Prepare new result data
        new_result_data = {
            'job_id': job_id,
            'county_id': county_id,
            'organization_name': best_org.get('name', 'Unknown'),
            'description': best_org.get('description', ''),
            'contact_info': contact_info,
            'address': best_org.get('address', ''),
            'additional_notes': best_org.get('notes', ''),
            'confidence_score': best_org.get('confidence', 0.7),
            'ai_response_raw': research_result.get('raw_response', '')
        }

        # Handle key personnel information
        key_personnel = best_org.get('key_personnel', {})
        new_result_data['key_personnel_name'] = key_personnel.get('name', '')
        new_result_data['key_personnel_title'] = key_personnel.get('title', '')
        new_result_data['key_personnel_phone'] = key_personnel.get('phone', '')
        new_result_data['key_personnel_email'] = key_personnel.get('email', '')

        existing_result = SearchResult.query.filter_by(
            job_id=job_id, 
            county_id=county_id
        ).first()

        if existing_result:
            # If an existing result exists, update it if the new one has a higher confidence score
            if new_result_data['confidence_score'] > existing_result.confidence_score:
                for key, value in new_result_data.items():
                    setattr(existing_result, key, value)
                db.session.commit()
                print(f"Updated result for {county_name} with higher confidence score: {new_result_data['confidence_score']:.2f} > {existing_result.confidence_score:.2f}")
            else:
                # If the new result has a lower confidence score, keep the existing one
                print(f"Kept existing result for {county_name} - existing confidence {existing_result.confidence_score:.2f} >= new confidence {new_result_data['confidence_score']:.2f}")
        else:
            # If no existing result, save the new one
            result = SearchResult(**new_result_data)
            db.session.add(result)
            db.session.commit()
            print(f"Saved new result for {county_name} with confidence {new_result_data['confidence_score']:.2f}")

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
