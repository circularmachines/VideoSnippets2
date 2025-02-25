"""Module for creating and managing video snippets based on transcription segments."""

import json
import os
import io
import base64
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
import logging

class LLMProcessor:
    def __init__(self, model: str = "gpt-4o"):
        """Initialize the LLM processor.
        
        Args:
            model: Name of the model to use
        """
        self.model = model
        
    def create_messages(self, system_message: str, content: Union[str, list]) -> list:
        """Create messages array with system message and content."""
        if isinstance(content, str):
            user_content = content
        else:
            user_content = content  # Already a list for multimodal content
            
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content}
        ]
        return messages
    
    def process_string(self, 
                      content: str,
                      system_message: str,
                      schema: Dict[str, Any],
                      max_tokens: int = 4096) -> Dict[str, Any]:
        """Process a string input with OpenAI API using structured output."""
        messages = self.create_messages(system_message, content)
        return self._make_api_call(messages, schema, max_tokens)
    
    def process_multimodal(self, 
                          content_list: list,
                          system_message: str,
                          schema: Dict[str, Any],
                          max_tokens: int = 4096) -> Dict[str, Any]:
        """Process a list of content items (text and images) with OpenAI API."""
        messages = self.create_messages(system_message, content_list)
        return self._make_api_call(messages, schema, max_tokens)
    
    def _make_api_call(self,
                      messages: list,
                      schema: Dict[str, Any],
                      max_tokens: int) -> Dict[str, Any]:
        """Make the API call to OpenAI."""
        response_format = {
            "type": "json_object"
        }
        
        try:
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                response_format=response_format
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return result
            
        except Exception as e:
            print(f"Error during API call: {str(e)}")
            return None

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        try:
            with open(image_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding image {image_path}: {e}")
            return None
            
    def prepare_content(self, text: str, segments_data: Dict, video_dir: str) -> List[Dict]:
        """Prepare content list with text and images.
        
        Args:
            text: Text content
            segments_data: Segment data with frame paths
            video_dir: Path to video directory
            
        Returns:
            List of content items
        """
        content = [{"type": "text", "text": text}]
        
        # Add images
        for segment in segments_data.get('segments', []):
            if 'frame_path' in segment:
                # Frame paths are relative to video directory
                frame_path = os.path.join(video_dir, segment['frame_path'])
                image_data = self.encode_image(frame_path)
                if image_data:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    })
        
        return content

def load_and_simplify_segments(transcription_path: str) -> tuple[str, str, Dict]:
    """Load transcription JSON file and create a numbered list of segments.
    
    Args:
        transcription_path: Path to the transcription JSON file
        
    Returns:
        tuple containing:
        - simplified_text: Numbered list of segment texts
        - language: Detected language of the content
        - segments_data: Complete transcription data
    """
    with open(transcription_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create numbered list of segments
    simplified_text = ""
    for i, segment in enumerate(data['segments']):
        simplified_text += f"{i}. {segment['text'].strip()}\n"
    
    return simplified_text, data.get('metadata', {}).get('language', 'en'), data

def get_structured_output(text: str, language: str, segments_data: Dict, output_path: str, skip_analysis: bool = False) -> Dict:
    """Send text and frames to OpenAI and get structured response.
    
    This function:
    1. Processes both transcript text and extracted frames
    2. Identifies key objects, actions, and themes
    3. Creates structured analysis with segment references
    4. Saves results back to the transcription JSON
    
    Args:
        text: Simplified text with numbered segments
        language: Language of the content
        segments_data: Complete transcription data with frame paths
        output_path: Path to save the updated JSON with analysis
        skip_analysis: Skip LLM analysis if True and use existing analysis from segments_data
        
    Returns:
        Dict containing structured analysis results
    """
    # Check if we should skip analysis
    if skip_analysis and 'analysis' in segments_data:
        logging.info("Using existing analysis")
        return segments_data['analysis']
        
    load_dotenv()
    
    # Define schema for video content analysis
    schema = {
        "type": "object",
        "properties": {
            "snippets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short title for this snippet"},
                        "description": {"type": "string", "description": "Description of what happens in this snippet"},
                        "segments": {
                            "type": "array", 
                            "items": {"type": "integer"},
                            "description": "List of segment indices that belong to this snippet"
                        }
                    }
                }
            }
        }
    }

    system_message = f"""You are an expert video content analyzer. Analyze the video content and create meaningful snippets.
A snippet is a group of segments that belong together thematically.

For each snippet:
1. Give it a clear title
2. Write a description of what happens
3. List which segments belong to it (use segment numbers from the input)

The input is in {language}.

Output a JSON object following this schema:
{json.dumps(schema, indent=2)}"""

    user_prompt = f"""Here is the video content as numbered segments:

{text}

For each segment that has frames, I'll show you the frames.
Create snippets that group related segments together."""

    # Initialize LLM processor
    llm = LLMProcessor()
    
    # Prepare content with text and frames
    content = llm.prepare_content(user_prompt, segments_data, os.path.dirname(output_path))
    
    # Get analysis from LLM
    result = llm.process_multimodal(content, system_message, schema)
    
    if result:
        # Save the analysis in the segments data
        segments_data['analysis'] = result
        
        # Save updated segments data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, indent=2, ensure_ascii=False)
            
        # Save LLM call details
        output_dir = os.path.dirname(output_path)
        save_llm_call(output_dir, system_message, user_prompt, schema, result)
        
        return result
    else:
        raise RuntimeError("Failed to get analysis from LLM")

def create_snippets(segments_data: Dict, snippets_dir: str, skip_existing: bool = False) -> List[Dict]:
    """Create video snippets based on analysis.
    
    Args:
        segments_data: Complete transcription data with analysis
        snippets_dir: Directory to save snippet files
        skip_existing: Skip creating snippets that already exist
        
    Returns:
        List of snippet metadata
    """
    # Create snippets directory
    os.makedirs(snippets_dir, exist_ok=True)
    
    snippets = []
    analysis = segments_data.get('analysis', {})
    
    for i, snippet_data in enumerate(analysis.get('snippets', [])):
        snippet_id = f"snippet_{i+1}"
        
        # Check if snippet already exists
        snippet_path = os.path.join(snippets_dir, f"{snippet_id}.json")
        if skip_existing and os.path.exists(snippet_path):
            logging.info(f"Snippet {snippet_id} already exists, skipping")
            with open(snippet_path, 'r') as f:
                snippet = json.load(f)
            snippets.append(snippet)
            continue
            
        # Create snippet
        snippet = {
            'id': snippet_id,
            'title': snippet_data['title'],
            'description': snippet_data['description'],
            'segments': []
        }
        
        # Add segments
        for segment_idx in snippet_data['segments']:
            if 0 <= segment_idx < len(segments_data['segments']):
                segment = segments_data['segments'][segment_idx]
                snippet['segments'].append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'frame_path': segment.get('frame_path')
                })
        
        # Save snippet
        with open(snippet_path, 'w', encoding='utf-8') as f:
            json.dump(snippet, f, indent=2, ensure_ascii=False)
            
        snippets.append(snippet)
        
    return snippets

def save_llm_call(output_dir: str, system_prompt: str, user_prompt: str, schema: Dict, response: Dict) -> None:
    """Save LLM call details to markdown file.
    
    Args:
        output_dir: Directory to save markdown file
        system_prompt: System prompt sent to LLM
        user_prompt: User prompt sent to LLM
        schema: JSON schema for response
        response: Response from LLM
    """
    markdown = f"""# LLM Call Details

## System Prompt
```
{system_prompt}
```

## User Prompt
```
{user_prompt}
```

## Response Schema
```json
{json.dumps(schema, indent=2)}
```

## Response
```json
{json.dumps(response, indent=2)}
```
"""
    
    # Save to markdown file
    md_path = os.path.join(output_dir, 'llm_call.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

def process_snippets(transcription_path: str, skip_analysis: bool = False, skip_existing: bool = False) -> List[Dict]:
    """Process video segments into snippets.
    
    Args:
        transcription_path: Path to transcription JSON file
        skip_analysis: Skip LLM analysis if True and use existing analysis
        skip_existing: Skip creating snippets that already exist
        
    Returns:
        List of snippet metadata
    """
    # Load and simplify segments
    text, language, segments_data = load_and_simplify_segments(transcription_path)
    
    # Get structured output
    analysis = get_structured_output(text, language, segments_data, transcription_path, skip_analysis)
    
    # Create snippets directory
    snippets_dir = os.path.join(os.path.dirname(transcription_path), 'snippets')
    
    # Create snippets
    return create_snippets(segments_data, snippets_dir, skip_existing)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Process video segments into snippets')
    parser.add_argument('transcription_path', help='Path to transcription JSON file')
    parser.add_argument('--skip-analysis', action='store_true', help='Skip LLM analysis if analysis exists')
    parser.add_argument('--skip-existing', action='store_true', help='Skip creating snippets that already exist')
    args = parser.parse_args()
    
    process_snippets(args.transcription_path, args.skip_analysis, args.skip_existing)
