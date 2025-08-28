"""
AI service for conducting research in each county.
This service creates isolated chat sessions to prevent hallucination.
"""

try:
    from openai import OpenAI
except ImportError:
    # Fallback for older openai package versions
    import openai
    OpenAI = None

import json
import time
from config import Config
from typing import Dict, List, Optional

class AIService:
    def __init__(self):
        if OpenAI:
            # New OpenAI client (v1.0+) with explicit httpx client
            try:
                import httpx
                # Create httpx client without problematic parameters
                http_client = httpx.Client(timeout=30.0)
                self.client = OpenAI(
                    api_key=Config.OPENAI_API_KEY,
                    http_client=http_client
                )
                self.model = "gpt-4o"
            except Exception as e:
                print(f"OpenAI client initialization error: {e}")
                # Fallback to legacy API if available
                if 'openai' in globals():
                    openai.api_key = Config.OPENAI_API_KEY
                    self.client = None
                    self.model = "gpt-4o"
                else:
                    raise e
        else:
            # Legacy OpenAI API
            openai.api_key = Config.OPENAI_API_KEY
            self.client = None
            self.model = "gpt-4o"
    
    def research_county(self, county_name: str, state_name: str, search_query: str) -> Dict:
        """
        Research a specific county for organizations matching the search query.
        Each call creates a fresh conversation to prevent hallucination.
        """
        
        prompt = self._build_research_prompt(county_name, state_name, search_query)
        
        try:
            if self.client:
                # New OpenAI client API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a thorough researcher specializing in finding public health and social service organizations. Provide accurate, factual information based on real organizations. If you cannot find specific information, clearly state that rather than making assumptions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more factual responses
                    max_tokens=2000
                )
                raw_response = response.choices[0].message.content
            else:
                # Legacy OpenAI API
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a thorough researcher specializing in finding public health and social service organizations. Provide accurate, factual information based on real organizations. If you cannot find specific information, clearly state that rather than making assumptions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for more factual responses
                    max_tokens=2000
                )
                raw_response = response.choices[0].message.content
            
            return self._parse_ai_response(raw_response, county_name, state_name)
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "county": county_name,
                "state": state_name,
                "organizations": []
            }
    
    def _build_research_prompt(self, county_name: str, state_name: str, search_query: str) -> str:
        """Build a detailed research prompt for the AI"""
        
        prompt = f"""
Please research and find information about organizations in {county_name} County, {state_name} that match this description: "{search_query}"

Focus specifically on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.

For each organization you find, please provide:
1. Organization name
2. Brief description of services
3. Contact information (phone, email, website if available)
4. Physical address if available
5. Any additional relevant notes

Please format your response as a JSON array of organizations, like this:
```json
{{
  "organizations": [
    {{
      "name": "Organization Name",
      "description": "Brief description of what they do",
      "contact": {{
        "phone": "phone number if available",
        "email": "email if available", 
        "website": "website if available"
      }},
      "address": "physical address if available",
      "notes": "any additional relevant information",
      "confidence": 0.9
    }}
  ],
  "search_summary": "Brief summary of your search process and findings"
}}
```

If you cannot find any organizations matching the criteria in {county_name} County, please return an empty organizations array and explain in the search_summary.

Be thorough but factual. Only include organizations you can verify exist.
"""
        return prompt
    
    def _parse_ai_response(self, raw_response: str, county_name: str, state_name: str) -> Dict:
        """Parse the AI response and extract structured data"""
        
        try:
            # Try to extract JSON from the response
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                result = {
                    "success": True,
                    "county": county_name,
                    "state": state_name,
                    "organizations": parsed_data.get("organizations", []),
                    "search_summary": parsed_data.get("search_summary", ""),
                    "raw_response": raw_response
                }
                
                # Add confidence scores if missing
                for org in result["organizations"]:
                    if "confidence" not in org:
                        org["confidence"] = 0.7  # Default confidence
                
                return result
            else:
                # Fallback: try to parse as plain text
                return self._parse_plain_text_response(raw_response, county_name, state_name)
                
        except json.JSONDecodeError:
            # Fallback to plain text parsing
            return self._parse_plain_text_response(raw_response, county_name, state_name)
        except Exception as e:
            return {
                "success": False,
                "error": f"Parsing error: {str(e)}",
                "county": county_name,
                "state": state_name,
                "organizations": [],
                "raw_response": raw_response
            }
    
    def _parse_plain_text_response(self, raw_response: str, county_name: str, state_name: str) -> Dict:
        """Fallback parser for plain text responses"""
        
        # Simple parsing logic for when JSON parsing fails
        organizations = []
        lines = raw_response.split('\n')
        
        current_org = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_org.get('name'):
                    organizations.append(current_org)
                    current_org = {}
                continue
            
            # Try to identify organization names (often start with numbers or bullets)
            if any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•']):
                if current_org.get('name'):
                    organizations.append(current_org)
                
                # Extract organization name
                name = line
                for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '•', '*']:
                    name = name.replace(prefix, '').strip()
                
                current_org = {
                    'name': name,
                    'description': '',
                    'contact': {},
                    'address': '',
                    'notes': '',
                    'confidence': 0.6
                }
            elif current_org.get('name'):
                # Add to description or notes
                if 'phone' in line.lower() or 'email' in line.lower() or 'website' in line.lower():
                    current_org['notes'] += line + ' '
                else:
                    current_org['description'] += line + ' '
        
        # Add the last organization
        if current_org.get('name'):
            organizations.append(current_org)
        
        return {
            "success": True,
            "county": county_name,
            "state": state_name,
            "organizations": organizations,
            "search_summary": f"Parsed {len(organizations)} organizations from plain text response",
            "raw_response": raw_response
        }
