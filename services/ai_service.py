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

    def research_county(self, county_name, state_name, search_query):
        """Research a county for overdose response teams"""
        
        prompt = f"""
OVERDOSE RESPONSE TEAMS RESEARCH

IMPORTANT: We are specifically looking for OVERDOSE RESPONSE TEAMS, NOT treatment centers. These teams focus on post-overdose intervention and ongoing support.

OVERDOSE RESPONSE TEAM CRITERIA:
WHAT TO LOOK FOR:
- Post-Overdose Intervention: Teams that respond to overdose incidents
- Peer Support: Often involve peer support specialists or recovery coaches
- Follow-up: Ongoing support and follow-up care
- Care Coordination: Connecting patients with MAT, therapists, and other services
- Emergency Response: Immediate response to overdose situations
- Recovery Support: Long-term support for recovery

WHAT TO EXCLUDE:
- Treatment Centers: Inpatient/outpatient drug treatment facilities
- Prevention Programs: Education and awareness programs
- General Mental Health: General mental health services
- Substance Abuse Counseling: General counseling services

SEARCH STRATEGY:
Comprehensive Coverage: Search for county-specific overdose response programs
Geographic Verification: Ensure results are actually in {county_name}, {state_name}
Service Overlap: Look for programs that may serve multiple counties

CONTACT INFORMATION SEARCH TECHNIQUES:
- Search county government websites for health departments
- Look for public health initiatives and programs
- Check for emergency response teams and protocols
- Search for peer support programs and recovery services
- Look for partnerships with hospitals and emergency services
- Check for recent news articles about overdose response
- Search for grant-funded programs and initiatives
- Look for community health organizations
- Check for 990 tax forms for non-profit organizations
- Search for state health department programs serving this county

RESEARCH DEPTH REQUIREMENTS:
- Thorough investigation of each potential organization
- Multiple search terms and variations
- Geographic and service variations
- Recent information (within last 2 years)
- Partnership networks and collaborations

COUNTY: {county_name}, {state_name}
SEARCH QUERY: {search_query}

Please research and provide detailed information about overdose response teams in this county. Focus on finding organizations that provide immediate post-overdose intervention and ongoing support, not treatment centers.

Return your findings in this exact JSON format:
{{
    "organization_name": "Name of the organization or 'No organizations found'",
    "description": "Detailed description of services and programs",
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

If no organizations are found that meet the criteria, return:
{{
    "organization_name": "No organizations found",
    "description": "No overdose response teams found in {county_name}, {state_name} that meet the specific criteria. We are looking for teams that provide post-overdose intervention and ongoing support, not treatment centers.",
    "key_personnel_name": "",
    "key_personnel_title": "",
    "key_personnel_phone": "",
    "key_personnel_email": "",
    "contact_info": "",
    "address": "",
    "additional_notes": "No qualifying organizations found. This county may not have dedicated overdose response teams, or they may be organized differently (e.g., through state programs, regional partnerships, or integrated into emergency services).",
    "confidence_score": 0.9,
    "source_urls": [],
    "ai_response_raw": "Search completed. No overdose response teams found that meet the specific criteria for post-overdose intervention and ongoing support.",
    "search_summary": "Comprehensive search completed for {county_name}, {state_name}. Searched for overdose response teams, peer support programs, emergency response protocols, and public health initiatives. No organizations found that specifically provide post-overdose intervention and ongoing support services as defined in our criteria."
}}
"""

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
