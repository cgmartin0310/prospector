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
            if 'gpt-5' in self.model:
                temperature = 0.1  # Very precise for GPT-5
                max_tokens = 6000  # GPT-5 can handle more tokens
                use_responses_api = True  # Use the new responses API for GPT-5
            elif 'gpt-4o' in self.model:
                temperature = 0.1
                max_tokens = 4000
                use_responses_api = False
            else:
                temperature = 0.3
                max_tokens = 2000
                use_responses_api = False
            
            if self.client:
                if use_responses_api and 'gpt-5' in self.model:
                    # Use the new responses API for GPT-5
                    response = self.client.responses.create(
                        model=self.model,
                        input=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    raw_response = response.output_text
                else:
                    # Use chat completions API for other models
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
                        response_format={"type": "json_object"} if not use_responses_api else None
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
        
        if 'gpt-5' in self.model:
            # GPT-5 specific prompt - more detailed and structured
            prompt = f"""
You are a professional researcher tasked with finding organizations in {county_name} County, {state_name} that match this specific criteria: "{search_query}"

CRITICAL REQUIREMENTS:
1. Focus EXCLUSIVELY on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.
2. Be thorough and systematic in your research approach.
3. Only include organizations you can verify exist.
4. If no organizations are found, clearly state this.
5. PRIORITY: Find the key personnel (director, manager, coordinator, head) of each organization and their direct contact information.

For each organization you find, provide complete information in this exact JSON format:

{{
  "organizations": [
    {{
      "name": "Full organization name",
      "description": "Detailed description of services and mission",
      "key_personnel": {{
        "name": "Name of director/manager/coordinator",
        "title": "Their specific title (e.g., Director, Manager, Coordinator)",
        "phone": "Direct phone number or null",
        "email": "Direct email address or null"
      }},
      "general_contact": {{
        "phone": "General organization phone or null",
        "email": "General organization email or null", 
        "website": "Organization website URL or null"
      }},
      "address": "full physical address or null",
      "notes": "any additional relevant information about the organization or key personnel or null",
      "confidence": 0.95
    }}
  ],
  "search_summary": "Comprehensive summary of your research process, sources consulted, and findings"
}}

IMPORTANT: Focus on finding the specific person in charge (director, manager, coordinator, head) of each organization and their direct contact information. This is more valuable than general organization contact info.

If no organizations are found, return:
{{
  "organizations": [],
  "search_summary": "No organizations matching '{search_query}' were found in {county_name} County, {state_name} after thorough research."
}}

Respond with ONLY valid JSON in the exact format specified above.
"""
        else:
            # Standard prompt for GPT-4o and other models
            prompt = f"""
Research organizations in {county_name} County, {state_name} that match: "{search_query}"

IMPORTANT: Focus ONLY on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.

PRIORITY: Find the key personnel (director, manager, coordinator, head) of each organization and their direct contact information.

For each organization found, provide:
- name: Organization name
- description: Brief description of services
- key_personnel: Object with name, title, phone, email of the person in charge
- general_contact: Object with general organization phone, email, website
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
      "key_personnel": {{
        "name": "Name of director/manager/coordinator",
        "title": "Their title (e.g., Director, Manager, Coordinator)",
        "phone": "Direct phone number or null",
        "email": "Direct email address or null"
      }},
      "general_contact": {{
        "phone": "General organization phone or null",
        "email": "General organization email or null",
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
