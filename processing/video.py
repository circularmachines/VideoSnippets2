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
from typing import Dict
import sys
import config

logger = logging.getLogger(__name__)

def process_video(video_path: str, output_dir: str, status_dict=None, skip_audio=False, skip_transcription=False, skip_frames=False) -> dict:
    """
    Process a video file to extract audio and frames.
    Steps will be skipped if output files already exist or if explicitly skipped.
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to store processing outputs
        status_dict: Optional dictionary to update processing status
        skip_audio: Skip audio extraction even if audio file doesn't exist
        skip_transcription: Skip transcription even if transcription file doesn't exist
        skip_frames: Skip frame extraction even if frames don't exist
        
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
        # Check for existing audio
        audio_path = output_path / "audio.mp3"
        if not skip_audio:
            if not audio_path.exists():
                if status_dict:
                    status_dict[video_id] = {
                        'status': 'extracting',
                        'message': 'Extracting audio from video...'
                    }
                audio_path = extract_audio(video_path, output_path)
                logger.info(f"Extracted audio from video: {video_id}")
            else:
                logger.info(f"Using existing audio for video: {video_id}")
        else:
            logger.info(f"Skipping audio extraction for video: {video_id}")
                
        result['audio_path'] = str(audio_path)
        
        # Check for existing transcription
        transcription_path = output_path / "transcription.json"
        if not skip_transcription:
            if not transcription_path.exists():
                if status_dict:
                    status_dict[video_id] = {
                        'status': 'transcribing',
                        'message': 'Transcribing audio...'
                    }
                transcription_path = transcribe_audio(str(audio_path), str(output_path))
                logger.info(f"Created transcription for video: {video_id}")
            else:
                logger.info(f"Using existing transcription for video: {video_id}")
        else:
            logger.info(f"Skipping transcription for video: {video_id}")
                
        result['transcription_path'] = str(transcription_path)
        
        # Check for existing frames directory
        frames_dir = output_path / "frames"
        if not skip_frames:
            if not frames_dir.exists() or not any(frames_dir.iterdir()):
                if status_dict:
                    status_dict[video_id] = {
                        'status': 'extracting_frames',
                        'message': 'Extracting video frames...'
                    }
                frames_dir = extract_frames(video_path, transcription_path, frames_dir)
                logger.info(f"Extracted frames for video: {video_id}")
            else:
                logger.info(f"Using existing frames for video: {video_id}")
        else:
            logger.info(f"Skipping frame extraction for video: {video_id}")
                
        result['frames_dir'] = str(frames_dir)
        
        if status_dict:
            status_dict[video_id] = {
                'status': 'done',
                'message': 'Video processing complete'
            }
            
        return result
        
    except Exception as e:
        logger.exception("Error during video processing")
        if status_dict:
            status_dict[video_id] = {
                'status': 'error',
                'message': str(e)
            }
        raise

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

def cut_video_segments(video_path: str, snippets_data: Dict, output_dir: str = None) -> None:
    """Cut video into segments based on snippet data.
    
    Args:
        video_path: Path to the source video file
        snippets_data: Dictionary containing snippet information with timestamps
        output_dir: Directory to store video segments (default: same as video)
    """
    # Create videos directory
    if output_dir is None:
        output_dir = os.path.dirname(video_path)
    videos_dir = os.path.join(output_dir, 'videos')
    os.makedirs(videos_dir, exist_ok=True)
    
    # Process each snippet
    for snippet in snippets_data.get('snippets', []):
        if not snippet['segments']:
            print(f"Skipping snippet '{snippet['title']}' - no segments")
            continue
        
        # Get start time from first segment and end time from last segment
        start_time = snippet['segments'][0]['start']
        end_time = snippet['segments'][-1]['end']
        
        # Create a safe filename from the snippet title
        safe_name = "".join(c if c.isalnum() else "_" for c in snippet['title'].lower())
        output_file = os.path.join(videos_dir, f"{safe_name}.mp4")
        
        # Get video settings from config
        vs = config.VIDEO_SETTINGS
        
        # Build FFmpeg filter for aspect ratio handling
        if vs['force_aspect_ratio']:
            vf = f'scale={vs["width"]}:{vs["height"]}:force_original_aspect_ratio=decrease,pad={vs["width"]}:{vs["height"]}:(ow-iw)/2:(oh-ih)/2'
        else:
            vf = f'scale={vs["width"]}:{vs["height"]}'
        
        # Cut the video segment with configured settings
        cmd = [
            'ffmpeg', '-y',  # Overwrite output files
            '-i', video_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-vf', vf,
            '-c:v', vs['codec'],
            '-preset', vs['preset'],
            '-crf', str(vs['crf']),
            '-c:a', vs['audio_codec'],
            '-b:a', vs['audio_bitrate'],
            '-movflags', '+faststart',  # Enable fast start for web playback
            output_file
        ]
        
        print(f"Cutting video for '{snippet['title']}'...")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            # Add video path to the snippet
            snippet['video_path'] = os.path.relpath(output_file, output_dir)
        except subprocess.CalledProcessError as e:
            print(f"Error cutting video for '{snippet['title']}': {e.stderr.decode()}")
            continue
    
    # Save updated snippets
    snippets_json = os.path.join(output_dir, 'snippets', 'snippets.json')
    os.makedirs(os.path.dirname(snippets_json), exist_ok=True)
    with open(snippets_json, 'w', encoding='utf-8') as f:
        json.dump(snippets_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete. Video segments saved to: {videos_dir}")

def cut_library_snippets(library_dir: str) -> None:
    """Cut video into snippets for a library directory.
    
    Args:
        library_dir: Path to library directory containing video and snippets
    """
    video_name = os.path.basename(library_dir)
    
    # Try both .mp4 and .mov extensions
    video_path = None
    for ext in ['.mp4', '.MOV', '.mov']:
        test_path = os.path.join('uploads', f"{video_name}{ext}")
        if os.path.exists(test_path):
            video_path = test_path
            break
    
    if not video_path:
        raise FileNotFoundError(f"Video file not found in uploads directory: {video_name}.*")
    
    snippets_path = os.path.join(library_dir, 'snippets', 'snippets.json')
    
    # Load snippets
    with open(snippets_path, 'r', encoding='utf-8') as f:
        snippets = json.load(f)
    
    # Cut video
    cut_video_segments(video_path, snippets, library_dir)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Video processing utilities')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Process video command
    process_parser = subparsers.add_parser('process', help='Process a video file')
    process_parser.add_argument('video_path', help='Path to video file')
    process_parser.add_argument('--output-dir', help='Output directory (default: same as video)')
    process_parser.add_argument('--skip-audio', action='store_true', help='Skip audio extraction')
    process_parser.add_argument('--skip-transcription', action='store_true', help='Skip transcription')
    process_parser.add_argument('--skip-frames', action='store_true', help='Skip frame extraction')
    
    # Cut snippets command
    cut_parser = subparsers.add_parser('cut', help='Cut video into snippets')
    cut_parser.add_argument('library_dir', help='Path to library directory')
    
    args = parser.parse_args()
    
    if args.command == 'process':
        output_dir = args.output_dir or os.path.dirname(args.video_path)
        process_video(args.video_path, output_dir, skip_audio=args.skip_audio, skip_transcription=args.skip_transcription, skip_frames=args.skip_frames)
    elif args.command == 'cut':
        cut_library_snippets(args.library_dir)
    else:
        parser.print_help()
