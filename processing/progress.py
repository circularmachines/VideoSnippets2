"""Progress tracking module for video processing."""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks progress of video processing with percentage completion."""
    
    # Define steps and their relative progress percentages
    STEPS = {
        'uploading': 0,
        'audio': 15,
        'transcription': 30,
        'frames': 45,
        'snippets': 60,
        'videos': 75,
        'complete': 100
    }
    
    def __init__(self, video_id: str, status_dict: Optional[Dict] = None):
        """Initialize progress tracker.
        
        Args:
            video_id: ID of the video being processed
            status_dict: Optional dictionary to update with progress
        """
        self.video_id = video_id
        self.status_dict = status_dict
        
    def update(self, status: str, message: str, sleep: bool = True):
        """Update progress status with optional sleep.
        
        Args:
            status: Status code (e.g., 'extracting', 'transcribing')
            message: Status message to display
            sleep: Whether to sleep before updating status
        """
        if self.status_dict is not None:
            if sleep:
                time.sleep(1)  # Give UI time to update
                
            # Get progress percentage for this step
            progress = self.STEPS.get(status, 0)
            
            self.status_dict[self.video_id] = {
                'status': status,
                'message': message,
                'progress': progress
            }
            logger.info(f"[{self.video_id}] {message} ({progress}%)")
            
    def using_existing(self, item: str):
        """Update status when using existing file."""
        if item == 'audio':
            self.update('audio', f'Using existing {item}...')
        elif item == 'transcription':
            self.update('transcription', f'Using existing {item}...')
        elif item == 'frames':
            self.update('frames', f'Using existing {item}...')
        elif item == 'snippets':
            self.update('snippets', f'Using existing {item}...')
        elif item == 'video segments':
            self.update('videos', f'Using existing {item}...')
        
    def skipping(self, item: str):
        """Update status when skipping a step."""
        if item == 'audio extraction':
            self.update('audio', f'Skipping {item}...')
        elif item == 'transcription':
            self.update('transcription', f'Skipping {item}...')
        elif item == 'frame extraction':
            self.update('frames', f'Skipping {item}...')
        
    def processing(self, item: str):
        """Update status when processing something."""
        self.update('processing', f'Processing {item}...')
        
    def extracting(self):
        """Update status for audio extraction."""
        self.update('audio', 'Extracting audio from video...')
        
    def transcribing(self):
        """Update status for transcription."""
        self.update('transcription', 'Transcribing audio...')
        
    def extracting_frames(self):
        """Update status for frame extraction."""
        self.update('frames', 'Extracting video frames...')
        
    def analyzing(self):
        """Update status for content analysis."""
        self.update('snippets', 'Analyzing content...')
        
    def creating_snippets(self):
        """Update status for snippet creation."""
        self.update('snippets', 'Creating snippets...')
        
    def cutting_video(self):
        """Update status for video cutting."""
        self.update('videos', 'Cutting video segments...')
        
    def complete(self, num_snippets: int = 0):
        """Update status for completion."""
        if num_snippets > 0:
            self.update('complete', f'Processing complete. Created {num_snippets} snippets!', sleep=False)
        else:
            self.update('complete', 'Processing complete', sleep=False)
        
    def error(self, error_message: str):
        """Update status for error."""
        self.update('error', str(error_message), sleep=False)
