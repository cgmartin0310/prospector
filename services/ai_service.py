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
                        'content': 'You are an assistant researching the web for prospects.'
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
                timeout=60
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
        
        # Simple, direct prompt using only the user's search query
        prompt = f"Research this in {county_name} County, {state_name}: {search_query}"

        try:
            print("Using Grok AI for research...")
            response = self._call_grok_api(prompt, max_tokens)
                
            # Parse the response
            try:
                result = json.loads(response)
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
