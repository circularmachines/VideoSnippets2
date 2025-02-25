"""
Content analysis module.
Analyzes transcribed content to extract structured information.
"""
from typing import List, Dict
from pathlib import Path
import os
import json
import base64
import openai
import cv2

def analyze_content(transcription: dict, frames_dir: str = None) -> dict:
    """
    Analyze transcribed content and frames to extract structured information.
    
    Args:
        transcription: Transcription data including segments and words
        frames_dir: Optional path to directory containing extracted frames
        
    Returns:
        dict: Analysis results including objects and their metadata
    """
    result = {
        'objects': [],
        'metadata': {}
    }
    
    # Analyze content
    structured_data = extract_structured_data(transcription['segments'])
    result['objects'].extend(structured_data['objects'])
    
    # If frames are available, enhance analysis with visual information
    if frames_dir:
        visual_data = analyze_frames(frames_dir)
        result = merge_analysis_results(result, visual_data)
    
    return result

def extract_structured_data(segments: List[Dict]) -> dict:
    """
    Extract structured data from transcription segments using GPT-4.
    
    Args:
        segments: List of transcription segments
        
    Returns:
        dict: Structured data including objects and their metadata
    """
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
    
    # Combine segments into full text
    full_text = " ".join(segment['text'] for segment in segments)
    
    # Create prompt for GPT-4
    prompt = f"""Analyze the following video transcript and extract key information:
    
{full_text}

Please identify:
1. Main topics discussed
2. Key objects or items mentioned
3. Important actions or events
4. Temporal relationships
5. Any specific technical terms or jargon

Format the response as a JSON object with these categories."""

    # Call GPT-4 API
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a video content analyzer. Extract structured information from video transcripts."},
            {"role": "user", "content": prompt}
        ]
    )
    
    # Parse and structure the response
    analysis = json.loads(response.choices[0].message.content)
    
    return {
        'objects': analysis.get('objects', []),
        'metadata': {
            'topics': analysis.get('topics', []),
            'actions': analysis.get('actions', []),
            'temporal': analysis.get('temporal', []),
            'technical_terms': analysis.get('technical_terms', [])
        }
    }

def analyze_frames(frames_dir: str) -> dict:
    """
    Analyze extracted frames using OpenAI's Vision API.
    
    Args:
        frames_dir: Path to directory containing extracted frames
        
    Returns:
        dict: Visual analysis results
    """
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
    
    # Configure OpenAI client
    client = openai.OpenAI()
    
    # Get list of frames
    frames = sorted(Path(frames_dir).glob('*.jpg'))
    visual_objects = []
    
    # Analyze key frames
    for frame_path in frames[:5]:  # Analyze first 5 frames
        # Load and encode image
        image = cv2.imread(str(frame_path))
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Generate analysis prompt
        prompt = """Analyze this video frame and identify:
1. Main objects and subjects
2. Actions or activities
3. Setting and environment
4. Any text or symbols visible
5. Notable visual elements

Format the response as a JSON object with these keys: objects, actions, setting, text, visual_elements"""
        
        # Get analysis from OpenAI Vision
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        
        visual_objects.append({
            'frame': frame_path.name,
            'objects': analysis.get('objects', []),
            'actions': analysis.get('actions', []),
            'setting': analysis.get('setting', ''),
            'text': analysis.get('text', []),
            'visual_elements': analysis.get('visual_elements', [])
        })
    
    return {
        'objects': visual_objects,
        'metadata': {
            'analyzed_frames': [obj['frame'] for obj in visual_objects]
        }
    }

def merge_analysis_results(text_analysis: dict, visual_analysis: dict) -> dict:
    """
    Merge text and visual analysis results.
    
    Args:
        text_analysis: Results from text analysis
        visual_analysis: Results from visual analysis
        
    Returns:
        dict: Combined analysis results
    """
    # Combine objects from both analyses
    combined_objects = text_analysis['objects'] + [
        obj for frame in visual_analysis['objects']
        for obj in frame['objects']
    ]
    
    # Merge metadata
    combined_metadata = {
        **text_analysis.get('metadata', {}),
        'visual_analysis': visual_analysis.get('metadata', {})
    }
    
    return {
        'objects': combined_objects,
        'metadata': combined_metadata
    }
