"""Module for creating and managing video snippets based on transcription segments."""

import json
import os
import io
import base64
from typing import Dict, List, Any, Tuple
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import logging
from openai import OpenAI
from .llm_config import Snippet, SnippetsResponse
from . import llm_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to LLM config file
LLM_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'llm_config.json')

def load_and_simplify_segments(transcription_path: str) -> Tuple[str, str, Dict]:
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

class LLMProcessor:
    """Handles interactions with the OpenAI API."""
    
    def __init__(self, model: str = None):
        """Initialize the LLM processor.
        
        Args:
            model: Name of the model to use, if None will load from config
        """
        self.model = model or llm_config.MODEL
        self.client = OpenAI()
    
    def process_content(self, system_message: str, text: str, segments_data: Dict, video_dir: str) -> Dict:
        """Process content with OpenAI API using structured output.
        
        Args:
            system_message: System message for the LLM
            text: Text content
            segments_data: Segment data with frame paths
            video_dir: Path to video directory
            
        Returns:
            Dict containing structured analysis
        """
        # Prepare messages with text and images
        messages = [{"role": "system", "content": system_message}]
        
        # Add text and images
        content = [{"type": "text", "text": text}]
        for segment in segments_data.get('segments', []):
            if 'frame_path' in segment:
                frame_path = os.path.join(video_dir, segment['frame_path'])
                image_data = self.encode_image(frame_path)
                if image_data:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    })
        
        messages.append({"role": "user", "content": content})
        
        # Make API call with structured output
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=llm_config.SnippetsResponse,
        )
        
        return completion.choices[0].message.parsed.model_dump()
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                
                return base64.b64encode(img_byte_arr).decode('utf-8')
        except Exception as e:
            logging.error(f"Error encoding image {image_path}: {str(e)}")
            return None

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
        skip_analysis: Skip LLM analysis if True and use existing analysis
        
    Returns:
        Dict containing structured analysis
    """
    # Check if we should skip analysis
    if skip_analysis and 'analysis' in segments_data:
        logging.info("Using existing analysis")
        return segments_data['analysis']
        
    # Check if snippets already exist
    snippets_dir = os.path.join(os.path.dirname(output_path), 'snippets')
    snippets_json = os.path.join(snippets_dir, 'snippets.json')
    if os.path.exists(snippets_json):
        logging.info("Skipping snippet generation - file already exists: " + snippets_json)
        return {'snippets': json.load(open(snippets_json, 'r'))}
        
    load_dotenv()
    
    # Format system message with language
    system_message = llm_config.SYSTEM_MESSAGE + "\n" + llm_config.PROMPTS['language_suffix'].format(
        language=language
    )

    # Format user prompt with text
    user_prompt = llm_config.PROMPTS['user_prompt'].format(text=text)

    # Initialize LLM processor with model from config
    llm = LLMProcessor()
    
    # Get analysis from LLM
    result = llm.process_content(
        system_message=system_message,
        text=user_prompt,
        segments_data=segments_data,
        video_dir=os.path.dirname(output_path)
    )
    
    if result:
        # Save the analysis in the segments data
        segments_data['analysis'] = result
        
        # Save updated segments data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(segments_data, f, indent=2, ensure_ascii=False)
            
        # Save LLM call details with schema
        output_dir = os.path.dirname(output_path)
        schema = llm_config.SnippetsResponse.model_json_schema()
        save_llm_call(output_dir, system_message, text, schema, result)
        
        return result
    else:
        logging.error("No result from LLM")
        return None

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
    
    # Create snippets from segments
    snippets = []
    current_snippet = None
    
    for segment in segments_data['segments']:
        # Start a new snippet if needed
        if current_snippet is None:
            current_snippet = {
                'title': '',  # Will be filled in by LLM
                'description': '',  # Will be filled in by LLM
                'segments': [segment],
                'video_path': f'videos/{os.path.basename(segments_data["video_path"])}',
                'id': f'videos/{os.path.basename(segments_data["video_path"])}',  # Use video path as ID
                'product_type': None,
                'condition': None,
                'brand': None,
                'compatibility': None,
                'intended_use': None,
                'modifications': [],
                'missing_parts': []
            }
        
        # Add segments
        current_snippet['segments'].append(segment)
    
    # Save snippet
    snippet_id = current_snippet['id']
    snippet_path = os.path.join(snippets_dir, f"{snippet_id}.json")
    if skip_existing and os.path.exists(snippet_path):
        logging.info(f"Snippet {snippet_id} already exists, skipping")
        with open(snippet_path, 'r') as f:
            snippet = json.load(f)
    else:
        with open(snippet_path, 'w', encoding='utf-8') as f:
            json.dump(current_snippet, f, indent=2, ensure_ascii=False)
        snippet = current_snippet
    
    snippets.append(snippet)
    
    # Save all snippets to snippets.json
    snippets_json_path = os.path.join(snippets_dir, 'snippets.json')
    with open(snippets_json_path, 'w', encoding='utf-8') as f:
        json.dump(snippets, f, indent=2, ensure_ascii=False)
        
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
