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
        Uses Golden Dataset examples to improve accuracy.
        """
        
        # Get golden examples to improve the search
        golden_examples = self._get_golden_examples(county_name, state_name, search_query)
        
        prompt = self._build_research_prompt(county_name, state_name, search_query, golden_examples)
        
        try:
            # Adjust parameters based on model
            # Allow temperature override via environment variable
            custom_temperature = os.environ.get('TEMPERATURE')
            
            if 'gpt-5' in self.model:
                # GPT-5 uses responses API - no temperature parameter available
                max_tokens = 6000  # GPT-5 can handle more tokens
                use_responses_api = True  # Use the new responses API for GPT-5
                temperature = None  # Not used for GPT-5
            elif 'gpt-4o' in self.model:
                temperature = float(custom_temperature) if custom_temperature else 0.2  # Slightly increased for better results
                max_tokens = 4000
                use_responses_api = False
                supports_json_format = True
            elif 'gpt-4' in self.model:
                temperature = float(custom_temperature) if custom_temperature else 0.3
                max_tokens = 2000
                use_responses_api = False
                supports_json_format = False  # GPT-4 doesn't support response_format
            else:
                temperature = float(custom_temperature) if custom_temperature else 0.3
                max_tokens = 2000
                use_responses_api = False
                supports_json_format = False
            
            if self.client:
                if use_responses_api and 'gpt-5' in self.model:
                    # Use the new responses API for GPT-5 (no temperature parameter)
                    response = self.client.responses.create(
                        model=self.model,
                        input=prompt,
                        max_tokens=max_tokens
                    )
                    raw_response = response.output_text
                else:
                    # Use chat completions API for other models
                    response_params = {
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a thorough researcher specializing in finding public health and social service organizations. You must respond with valid JSON format as specified in the user's request. Be factual and accurate - if you cannot find specific information, clearly state that rather than making assumptions."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    
                    # Only add response_format for models that support it
                    if supports_json_format:
                        response_params["response_format"] = {"type": "json_object"}
                    
                    response = self.client.chat.completions.create(**response_params)
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
    
    def _build_research_prompt(self, county_name: str, state_name: str, search_query: str, golden_examples: List = None) -> str:
        """Build a detailed research prompt for the AI"""
        
        if 'gpt-5' in self.model:
            # GPT-5 specific prompt - more detailed and structured
            golden_examples_text = self._format_golden_examples(golden_examples) if golden_examples else ""
            
            prompt = f"""
You are a professional researcher tasked with finding organizations in {county_name} County, {state_name} that match this specific criteria: "{search_query}"

{golden_examples_text}

CRITICAL REQUIREMENTS:
1. Focus EXCLUSIVELY on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.
2. Be thorough and systematic in your research approach.
3. Only include organizations you can verify exist.
4. If no organizations are found, clearly state this.
5. PRIORITY: Find the key personnel (director, manager, coordinator, head) of each organization and their direct contact information.
6. Use the examples above as templates for what constitutes a high-quality, verified result.

CRITICAL - NO MADE UP INFORMATION:
- NEVER make up names, phone numbers, or email addresses
- If you cannot find a specific person's name, use null
- If you cannot find a specific phone number, use null  
- If you cannot find a specific email address, use null
- Only use information you can verify from official sources
- Generic contact info (like general@organization.org) is acceptable if verified
- When in doubt, use null rather than guessing

For each organization you find, provide complete information in this exact JSON format:

{{
  "organizations": [
    {{
      "name": "Full organization name",
      "description": "Detailed description of services and mission",
      "key_personnel": {{
        "name": "Real name of director/manager/coordinator (or null if not found)",
        "title": "Their specific title (or null if not found)",
        "phone": "Real direct phone number (or null if not found)",
        "email": "Real direct email address (or null if not found)"
      }},
      "general_contact": {{
        "phone": "Real general organization phone (or null if not found)",
        "email": "Real general organization email (or null if not found)", 
        "website": "Real organization website URL (or null if not found)"
      }},
      "address": "Real full physical address (or null if not found)",
      "notes": "Any additional relevant information about the organization or key personnel (or null)",
      "confidence": 0.95
    }}
  ],
  "search_summary": "Comprehensive summary of your research process, sources consulted, and findings"
}}

IMPORTANT: Focus on finding the specific person in charge (director, manager, coordinator, head) of each organization and their real, verified contact information. If you cannot find specific contact information, use null rather than making up fake information.

If no organizations are found, return:
{{
  "organizations": [],
  "search_summary": "No organizations matching '{search_query}' were found in {county_name} County, {state_name} after thorough research."
}}

Respond with ONLY valid JSON in the exact format specified above.
"""
        else:
            # Standard prompt for GPT-4o and other models
            golden_examples_text = self._format_golden_examples(golden_examples) if golden_examples else ""
            
            prompt = f"""
Research organizations in {county_name} County, {state_name} that match: "{search_query}"

{golden_examples_text}

IMPORTANT: Focus ONLY on {county_name} County. Do not include organizations from other counties unless they explicitly serve {county_name} County.

PRIORITY: Find the key personnel (director, manager, coordinator, head) of each organization and their direct contact information.

Use the examples above as templates for what constitutes a high-quality, verified result.

CRITICAL - NO MADE UP INFORMATION:
- NEVER make up names, phone numbers, or email addresses
- If you cannot find a specific person's name, use null
- If you cannot find a specific phone number, use null  
- If you cannot find a specific email address, use null
- Only use information you can verify from official sources
- Generic contact info (like general@organization.org) is acceptable if verified
- When in doubt, use null rather than guessing

For each organization found, provide:
- name: Organization name
- description: Brief description of services
- key_personnel: Object with name, title, phone, email of the person in charge (use null if not found)
- general_contact: Object with general organization phone, email, website (use null if not found)
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
        "name": "Real name of director/manager/coordinator (or null if not found)",
        "title": "Their title (or null if not found)",
        "phone": "Real direct phone number (or null if not found)",
        "email": "Real direct email address (or null if not found)"
      }},
      "general_contact": {{
        "phone": "Real general organization phone (or null if not found)",
        "email": "Real general organization email (or null if not found)",
        "website": "Real organization website (or null if not found)"
      }},
      "address": "Real address (or null if not found)",
      "notes": "Additional info (or null if not found)",
      "confidence": 0.9
    }}
  ],
  "search_summary": "Brief summary of search process and findings"
}}
"""
        return prompt
    
    def _get_golden_examples(self, county_name: str, state_name: str, search_query: str) -> List[Dict]:
        """
        Get relevant golden examples to improve AI search accuracy.
        Returns examples from similar counties/states and matching search categories.
        """
        try:
            # Import here to avoid circular imports
            from models import GoldenResult, County, State
            
            # Get golden examples from the same state first
            state_examples = GoldenResult.query.join(County).join(State).filter(
                State.name == state_name,
                GoldenResult.search_category == "overdose_response"
            ).limit(3).all()
            
            # If not enough state examples, get from similar search categories
            if len(state_examples) < 3:
                category_examples = GoldenResult.query.filter(
                    GoldenResult.search_category == "overdose_response"
                ).limit(5 - len(state_examples)).all()
                
                # Combine and remove duplicates
                all_examples = list(state_examples) + list(category_examples)
                unique_examples = []
                seen_names = set()
                
                for example in all_examples:
                    if example.organization_name not in seen_names:
                        unique_examples.append(example)
                        seen_names.add(example.organization_name)
                        if len(unique_examples) >= 5:
                            break
                
                return unique_examples
            
            return list(state_examples)
            
        except Exception as e:
            print(f"Error getting golden examples: {e}")
            return []
    
    def _format_golden_examples(self, golden_examples: List) -> str:
        """
        Format golden examples for inclusion in AI prompts.
        """
        if not golden_examples:
            return ""
        
        examples_text = "\n\nEXAMPLES OF HIGH-QUALITY RESULTS:\n"
        
        for i, example in enumerate(golden_examples[:3], 1):  # Limit to 3 examples
            examples_text += f"""
Example {i}: {example.organization_name}
- Location: {example.county.name} County, {example.state.name}
- Key Personnel: {example.key_personnel_name or 'Not specified'} ({example.key_personnel_title or 'Not specified'})
- Contact: {example.key_personnel_phone or 'Not specified'} | {example.key_personnel_email or 'Not specified'}
- Services: {example.description or 'Not specified'}
- Why this is a good example: Verified overdose response services with real contact information
"""
        
        examples_text += "\nUse these examples as templates for what constitutes a high-quality, verified result."
        return examples_text
    
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
