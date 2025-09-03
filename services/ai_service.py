"""
AI service for conducting research in each county.
This service creates isolated chat sessions to prevent hallucination.
"""

import os
import json
import requests

class AIService:
    def __init__(self):
        self.grok_api_key = os.getenv('GROK_API_KEY')
        
        if not self.grok_api_key:
            raise ValueError("GROK_API_KEY must be set")
            
        print("Grok AI service initialized successfully")

    def _call_grok_api(self, prompt, max_tokens=4000):
        """Call Grok API using direct HTTP requests"""
        try:
            headers = {
                'Authorization': f'Bearer {self.grok_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Use chat format with system and user messages
            data = {
                'model': 'grok-4',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are an analyst researching information about overdose response teams and best contact information for the head of the program. IMPORTANT: Do not make up or fabricate any results. If no organizations are found for a county, clearly state "No organizations found" rather than creating fictional information.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': max_tokens
            }
            
            print(f"Calling Grok API with model: grok-4")
            print(f"API Key (first 10 chars): {self.grok_api_key[:10]}...")
            print(f"Request data: {json.dumps(data, indent=2)}")
            
            # Call the xAI chat endpoint
            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=120  # Increased from 60 to 120 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"Grok API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Grok API call error: {str(e)}")
            raise e

    def research_county(self, county_name, state_name, search_query, max_tokens=4000):
        """Research a county for overdose response teams"""
        
        # Simple prompt with JSON formatting requirement
        prompt = f"""Research this in {county_name} County, {state_name}: {search_query}

Please return your findings in this exact JSON format:
{{
    "organization_name": "Name of the organization or 'No organizations found'",
    "description": "Brief description of services",
    "key_personnel_name": "Name of key contact person",
    "key_personnel_title": "Title/role of key contact person", 
    "key_personnel_phone": "Phone number for key contact person",
    "key_personnel_email": "Email for key contact person",
    "contact_info": "General contact information",
    "address": "Physical address of the organization",
    "additional_notes": "Additional relevant information",
    "confidence_score": 0.85,
    "source_urls": ["url1", "url2"],
    "ai_response_raw": "Full AI response text",
    "search_summary": "Summary of search strategy and findings"
}}

If no organizations are found, return:
{{
    "organization_name": "No organizations found",
    "description": "No organizations found in {county_name}, {state_name}",
    "key_personnel_name": "",
    "key_personnel_title": "",
    "key_personnel_phone": "",
    "key_personnel_email": "",
    "contact_info": "",
    "address": "",
    "additional_notes": "",
    "confidence_score": 0.9,
    "source_urls": [],
    "ai_response_raw": "Search completed. No organizations found.",
    "search_summary": "Search completed for {county_name}, {state_name}."
}}"""

        try:
            print("Using Grok AI for research...")
            response = self._call_grok_api(prompt, max_tokens)
            
            print(f"Grok response received: {response[:500]}...")  # Show first 500 chars
                
            # Parse the response
            try:
                result = json.loads(response)
                print(f"JSON parsing successful for {county_name}")
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to parse AI response as JSON: {e}")
                print(f"Raw response: {response}")
                # Return a fallback response
                return {
                    "organization_name": "Error parsing AI response",
                    "description": f"Failed to parse AI response: {str(e)}",
                    "key_personnel_name": "",
                    "key_personnel_title": "",
                    "key_personnel_phone": "",
                    "key_personnel_email": "",
                    "contact_info": "",
                    "address": "",
                    "additional_notes": f"AI response parsing error: {str(e)}",
                    "confidence_score": 0.0,
                    "source_urls": [],
                    "ai_response_raw": response,
                    "search_summary": "Error occurred while processing AI response"
                }
                
        except Exception as e:
            print(f"AI service error: {e}")
            raise Exception(f"AI service error: {str(e)}")
