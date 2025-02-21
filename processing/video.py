"""
Video processing module.
Handles video file operations including:
- Extracting audio
- Extracting frames
- Video segmentation
"""
import os
from pathlib import Path
import logging
import cv2
import json
import subprocess
from .transcribe import transcribe_audio

logger = logging.getLogger(__name__)

def process_video(video_path: str, output_dir: str, status_dict=None) -> dict:
    """
    Process a video file to extract audio and frames.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to store processing outputs
        status_dict: Optional dictionary to update processing status
        
    Returns:
        dict: Processing results including paths to extracted audio and frames
    """
    video_id = Path(video_path).stem
    result = {
        'video_id': video_id,
        'audio_path': None,
        'frames_dir': None,
        'transcription_path': None
    }
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Extract audio
        if status_dict:
            status_dict[video_id] = {
                'status': 'extracting',
                'message': 'Extracting audio from video...'
            }
        audio_path = extract_audio(video_path, output_path)
        result['audio_path'] = str(audio_path)
        
        # Transcribe audio
        if status_dict:
            status_dict[video_id] = {
                'status': 'transcribing',
                'message': 'Transcribing audio...'
            }
        transcription_path = transcribe_audio(str(audio_path), str(output_path))
        result['transcription_path'] = transcription_path
        
        # Extract frames
        if status_dict:
            status_dict[video_id] = {
                'status': 'extracting_frames',
                'message': 'Extracting frames from video...'
            }
        frames_dir = output_path / 'frames'
        frames_dir.mkdir(exist_ok=True)
        extract_frames(video_path, transcription_path, frames_dir)
        result['frames_dir'] = str(frames_dir)
        
        return result
        
    except Exception as e:
        logger.exception("Error during video processing")
        raise RuntimeError(f"Failed to process video: {str(e)}")

def extract_audio(video_path: str, output_dir: Path) -> Path:
    """Extract audio from video file."""
    logger.info(f"Extracting audio from: {video_path}")
    
    try:
        output_path = output_dir / "audio.mp3"
        
        # Extract audio using ffmpeg
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # Disable video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # High quality (0-9, lower is better)
            '-y',  # Overwrite output
            str(output_path)
        ]
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {result.stderr}")
        
        logger.info(f"Audio extracted to: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.exception("FFmpeg error during audio extraction")
        raise RuntimeError(f"Failed to extract audio: {e.stderr}")
    except Exception as e:
        logger.exception("Error during audio extraction")
        raise RuntimeError(f"Failed to extract audio: {str(e)}")

def extract_frames(video_path: str, json_path: str, output_dir: Path):
    """
    Extract frames from the middle of each segment in a video.
    Updates the JSON file with frame paths.
    """
    logger.info(f"Extracting frames from: {video_path}")
    
    try:
        # Load transcription JSON
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Open video file
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        # Get rotation metadata
        rotation = int(cap.get(cv2.CAP_PROP_ORIENTATION_META))
        
        # Process each segment
        for i, segment in enumerate(data['segments']):
            # Calculate middle timestamp
            middle_time = (segment['start'] + segment['end']) / 2
            
            # Convert time to frame number
            frame_number = int(middle_time * fps)
            
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            # Read frame
            ret, frame = cap.read()
            if ret:
                # Correct rotation if needed
                if rotation == 90:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif rotation == 270:
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif rotation == 180:
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                    
                # Generate output filename
                output_filename = f"segment_{i:03d}_{middle_time:.2f}s.jpg"
                output_path = output_dir / output_filename
                
                # Save frame
                cv2.imwrite(str(output_path), frame)
                logger.info(f"Saved frame for segment {i} at {middle_time:.2f}s")
                
                # Add frame path to segment
                segment['frame_path'] = str(output_path.relative_to(output_dir.parent))
            else:
                logger.warning(f"Failed to extract frame for segment {i}")
                segment['frame_path'] = None
        
        # Release video capture
        cap.release()
        
        # Save updated JSON
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Updated {json_path} with frame paths")
        
    except Exception as e:
        logger.exception("Error during frame extraction")
        raise RuntimeError(f"Failed to extract frames: {str(e)}")
