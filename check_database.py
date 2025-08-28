#!/usr/bin/env python3
"""
Script to check the Render PostgreSQL database and examine recent search results.
This will help us understand why GPT-4o might be returning no results.
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models import db, ProspectingJob, SearchResult, State, County
from config import Config

# Load environment variables
load_dotenv()

# Create Flask app context
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def check_database():
    """Check the database and examine recent results"""
    with app.app_context():
        print("=== DATABASE CHECK ===")
        
        # Check total counts
        total_jobs = ProspectingJob.query.count()
        total_results = SearchResult.query.count()
        total_states = State.query.count()
        total_counties = County.query.count()
        
        print(f"Total Jobs: {total_jobs}")
        print(f"Total Results: {total_results}")
        print(f"Total States: {total_states}")
        print(f"Total Counties: {total_counties}")
        
        if total_jobs == 0:
            print("\nNo jobs found in database.")
            return
        
        # Get recent jobs
        print(f"\n=== RECENT JOBS (last 5) ===")
        recent_jobs = ProspectingJob.query.order_by(ProspectingJob.created_at.desc()).limit(5).all()
        
        for job in recent_jobs:
            results_count = SearchResult.query.filter_by(job_id=job.id).count()
            state_name = job.state.name if job.state else "Unknown"
            
            print(f"\nJob #{job.id}:")
            print(f"  Query: {job.search_query}")
            print(f"  State: {state_name}")
            print(f"  Status: {job.status}")
            print(f"  Created: {job.created_at}")
            print(f"  Results: {results_count}")
            
            if job.error_message:
                print(f"  Error: {job.error_message}")
            
            if job.status == 'completed' and results_count == 0:
                print(f"  ⚠️  COMPLETED BUT NO RESULTS - This might be the GPT-4o issue!")
        
        # Check recent results
        if total_results > 0:
            print(f"\n=== RECENT RESULTS (last 5) ===")
            recent_results = SearchResult.query.order_by(SearchResult.created_at.desc()).limit(5).all()
            
            for result in recent_results:
                print(f"\nResult #{result.id}:")
                print(f"  Organization: {result.organization_name}")
                print(f"  County: {result.county.name}, {result.county.state.name}")
                print(f"  Job ID: {result.job_id}")
                print(f"  Confidence: {result.confidence_score}")
                print(f"  Created: {result.created_at}")
                
                # Show first 200 chars of raw AI response
                if result.ai_response_raw:
                    raw_preview = result.ai_response_raw[:200] + "..." if len(result.ai_response_raw) > 200 else result.ai_response_raw
                    print(f"  Raw AI Response: {raw_preview}")
                else:
                    print(f"  Raw AI Response: None")
        
        # Check for jobs with no results
        print(f"\n=== JOBS WITH NO RESULTS ===")
        jobs_with_no_results = []
        for job in ProspectingJob.query.filter_by(status='completed').all():
            results_count = SearchResult.query.filter_by(job_id=job.id).count()
            if results_count == 0:
                jobs_with_no_results.append(job)
        
        if jobs_with_no_results:
            print(f"Found {len(jobs_with_no_results)} completed jobs with no results:")
            for job in jobs_with_no_results:
                print(f"  Job #{job.id}: {job.search_query} in {job.state.name}")
        else:
            print("No completed jobs found with zero results.")

if __name__ == "__main__":
    check_database()
