"""Anthropic Claude LLM service for text processing."""

import anthropic
from typing import Dict, Any, List
import json
from config import Config

class AnthropicService:
    """Service for interacting with Anthropic Claude API."""
    
    def __init__(self):
        """Initialize Anthropic client."""
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    def _chat(self, content: str, **params):
        """Send a chat request to Claude."""
        # Set default model if not provided
        model = params.get('model', 'claude-sonnet-4-5-20250929')
        
        # Extract parameters to avoid passing them twice
        max_tokens = params.get('max_tokens', 4000)
        temperature = params.get('temperature', 0.3)
        
        # Remove extracted parameters from params
        params_clean = {k: v for k, v in params.items() 
                       if k not in ['model', 'max_tokens', 'temperature']}
        
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": content}],
            **params_clean
        )
        return response

    def _text(self, res) -> str:
        """Extract text from Anthropic response."""
        try:
            if hasattr(res, 'content') and res.content:
                return res.content[0].text.strip()
            return str(res)
        except Exception:
            return str(res)

    def parse_bug_report(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Parse Slack conversation into structured bug report.
        
        Args:
            conversation: List of messages from Slack thread
            
        Returns:
            Structured bug report data
        """
        print(f"Parsing bug report from {len(conversation)} messages")
        
        # Format conversation for LLM
        try:
            formatted_conv = "\n".join([
                f"{msg['user']}: {msg['text']}" 
                for msg in conversation
            ])
        except Exception as e:
            print(f"Failed to format conversation: {e}")
            raise
        
        prompt = f"""You are analyzing a Slack conversation about a bug or issue. Extract and structure the information into a clear bug report.

            Conversation:
            {formatted_conv}

            Extract the following information:
            1. Bug Title (concise, descriptive)
            2. Bug Description (detailed explanation)
            3. Steps to Reproduce (if mentioned)
            4. Expected Behavior
            5. Actual Behavior  
            6. Severity (Critical/High/Medium/Low)
            7. Affected Components (files, services, features mentioned)
            8. Additional Context

            Return as JSON with these exact keys: title, description, steps_to_reproduce, expected_behavior, actual_behavior, severity, affected_components, additional_context"""

        try:
            response = self._chat(
                prompt,
                model="claude-sonnet-4-5-20250929",
                temperature=0.3,
                max_tokens=1000,
            )
            
            # Parse response
            text = self._text(response)
            
            # Find JSON in response
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                result = json.loads(json_str)
                return result
        except Exception as e:
            print(f"Error parsing response: {e}")
            import traceback
            traceback.print_exc()
        
        # Fallback structure
        return {
            "title": "Bug Report from Slack",
            "description": formatted_conv[:500],
            "steps_to_reproduce": "See conversation",
            "expected_behavior": "System should work as intended",
            "actual_behavior": "Issue reported in conversation",
            "severity": "Medium",
            "affected_components": [],
            "additional_context": formatted_conv
        }
    
    def generate_code_fix(self, bug_report: Dict[str, Any], code_context: str) -> Dict[str, Any]:
        """Generate code fix based on bug report and codebase context.
        
        Args:
            bug_report: Structured bug report
            code_context: Relevant code from repository
            
        Returns:
            Generated fix with code changes
        """
        print(f"Generating code fix for: {bug_report.get('title', 'N/A')}")
        print(f"Code context length: {len(code_context)} chars")
        
        # Build comprehensive prompt
        prompt = f"""You are an expert software engineer. Analyze the bug report and code context to generate a precise fix.

Bug Report:
Title: {bug_report.get('title', '')}
Description: {bug_report.get('description', '')}
Expected: {bug_report.get('expected_behavior', '')}
Actual: {bug_report.get('actual_behavior', '')}
Severity: {bug_report.get('severity', 'Medium')}
Affected Components: {bug_report.get('affected_components', [])}

Code Context:
{code_context[:8000]}

Generate a fix that:
1. Identifies the root cause
2. Provides a clear fix description
3. Shows specific code changes
4. Includes testing notes

Return as JSON with these exact keys:
- root_cause: Brief explanation of the issue
- fix_description: What the fix does
- code_changes: Array of changes [{{"file": "path/to/file", "changes": "COMPLETE FILE CONTENT WITH MINIMAL CHANGES"}}]
- testing_notes: How to test the fix

CRITICAL REQUIREMENTS:
1. For text replacements: Find the exact text and replace ONLY that text
2. Preserve the ENTIRE file structure and content
3. Make the smallest possible change
4. Include the COMPLETE file content in "changes", not just the modified lines
5. For HTML files: Keep all tags, classes, structure intact

Example for name changes:
- Original: <div class="logo">adam wang</div>
- Fixed: <div class="logo">conan wang</div>
- Include the ENTIRE file content with this one change"""

        try:
            response = self._chat(
                prompt,
                model="claude-sonnet-4-5-20250929",
                temperature=0.1,
                max_tokens=4000,
            )
            
            text = self._text(response)
            
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                result = json.loads(json_str)
                
                print(f"Generated fix with {len(result.get('code_changes', []))} code changes")
                return result
        except Exception as e:
            print(f"Error generating fix: {e}")
            import traceback
            traceback.print_exc()
        
        # Fallback
        return {
            "root_cause": "Analysis needed",
            "fix_description": "Manual review required",
            "code_changes": [],
            "testing_notes": "Test thoroughly before deployment"
        }
    
