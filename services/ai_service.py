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
import os
from config import Config
from typing import Dict, List, Optional

class AIService:
    def __init__(self, model_name: str = None):
        # Allow model to be configurable via environment variable or parameter
        self.model = model_name or os.environ.get('OPENAI_MODEL', 'gpt-4o')
        
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
            except Exception as e:
                print(f"OpenAI client initialization error: {e}")
                # Fallback to legacy API if available
                if 'openai' in globals():
                    openai.api_key = Config.OPENAI_API_KEY
                    self.client = None
                else:
                    raise e
        else:
            # Legacy OpenAI API
            openai.api_key = Config.OPENAI_API_KEY
            self.client = None
    
    def research_county(self, county_name: str, state_name: str, search_query: str) -> Dict:
        """
        Research a specific county for organizations matching the search query.
        Each call creates a fresh conversation to prevent hallucination.
        """
        
        prompt = self._build_research_prompt(county_name, state_name, search_query)
        
        try:
            # Adjust parameters based on model
            temperature = 0.1 if 'gpt-4o' in self.model else 0.3
            max_tokens = 4000 if 'gpt-4o' in self.model else 2000
            
            if self.client:
                # New OpenAI client API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a thorough researcher specializing in finding public health and social service organizations. You must respond with valid JSON format as specified in the user's request. Be factual and accurate - if you cannot find specific information, clearly state that rather than making assumptions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}  # Force JSON response for GPT-4o
                )
                raw_response = response.choices[0].message.content
            else:
                # Legacy OpenAI API
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a thorough researcher specializing in finding public health and social service organizations. You must respond with valid JSON format as specified in the user's request. Be factual and accurate - if you cannot find specific information, clearly state that rather than making assumptions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                raw_response = response.choices[0].message.content
            
            return self._parse_ai_response(raw_response, county_name, state_name)
            
        except Exception as e:
            print(f"AI research error for {county_name}, {state_name}: {str(e)}")
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
Research organizations in {county_name} County, {state_name} that match: "{search_query}"

IMPORTANT: Focus ONLY on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.

For each organization found, provide:
- name: Organization name
- description: Brief description of services
- contact: Object with phone, email, website (use null if not available)
- address: Physical address (use null if not available)
- notes: Additional relevant information
- confidence: Number between 0.0 and 1.0 indicating your confidence

If no organizations are found, return an empty organizations array.

Respond with ONLY valid JSON in this exact format:
{{
  "organizations": [
    {{
      "name": "Organization Name",
      "description": "What they do",
      "contact": {{
        "phone": "phone number or null",
        "email": "email or null",
        "website": "website or null"
      }},
      "address": "address or null",
      "notes": "additional info or null",
      "confidence": 0.9
    }}
  ],
  "search_summary": "Brief summary of search process and findings"
}}
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
