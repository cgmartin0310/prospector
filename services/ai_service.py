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
                self.model = "gpt-4"
            except Exception as e:
                print(f"OpenAI client initialization error: {e}")
                # Fallback to legacy API if available
                if 'openai' in globals():
                    openai.api_key = Config.OPENAI_API_KEY
                    self.client = None
                    self.model = "gpt-4"
                else:
                    raise e
        else:
            # Legacy OpenAI API
            openai.api_key = Config.OPENAI_API_KEY
            self.client = None
            self.model = "gpt-4"
    
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
                            "content": "You are a precise researcher specializing in finding specific public health and social service organizations. ONLY include organizations that directly match the exact search criteria. Do NOT include organizations that provide tangentially related services. If you cannot find organizations that specifically match the criteria, return an empty list rather than including loosely related organizations. Be extremely selective and accurate."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # Very low temperature for maximum precision and specificity
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
                            "content": "You are a precise researcher specializing in finding specific public health and social service organizations. ONLY include organizations that directly match the exact search criteria. Do NOT include organizations that provide tangentially related services. If you cannot find organizations that specifically match the criteria, return an empty list rather than including loosely related organizations. Be extremely selective and accurate."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # Very low temperature for maximum precision and specificity
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
SEARCH CRITERIA: Find organizations in {county_name} County, {state_name} that SPECIFICALLY match: "{search_query}"

STRICT REQUIREMENTS:
- ONLY include organizations that directly provide the exact services mentioned in the search query
- Do NOT include general health organizations, hospitals, or clinics unless they have dedicated programs matching the search
- Do NOT include organizations that "might" or "could" provide related services
- Do NOT include broad social services organizations unless they have specific programs matching the criteria
- If an organization provides the service as just one small part of many services, exclude it unless it's a major focus

GEOGRAPHIC FOCUS:
- Focus specifically on {county_name} County, {state_name}
- Only include organizations based in this county or explicitly serving this county

CONFIDENCE SCORING:
- Set confidence to 0.9-1.0 for organizations that are an exact match
- Set confidence to 0.7-0.8 for organizations that closely match but aren't perfect
- Do NOT include anything with confidence below 0.7

Please format your response as JSON:
```json
{{
  "organizations": [
    {{
      "name": "Organization Name",
      "description": "Brief description focusing on how they match the search criteria",
      "contact": {{
        "phone": "phone number if available",
        "email": "email if available", 
        "website": "website if available"
      }},
      "address": "physical address if available",
      "notes": "explain specifically why this organization matches the search criteria",
      "confidence": 0.9
    }}
  ],
  "search_summary": "Brief summary explaining your search process and why you included or excluded organizations"
}}
```

IMPORTANT: If you cannot find organizations that SPECIFICALLY match the criteria, return an empty organizations array. It is better to find nothing than to include loosely related organizations.
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
