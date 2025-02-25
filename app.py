"""
Snuttification API Server
Handles HTTP endpoints and request routing.
"""
from flask import Flask, jsonify, request, send_from_directory, send_file, make_response
from flask_cors import CORS
from pathlib import Path
import os
import json
import logging
from threading import Thread
from werkzeug.utils import secure_filename
from processing.video import process_video, cut_library_snippets
from processing.snippets import load_and_simplify_segments, get_structured_output, process_snippets
from processing.progress import ProgressTracker
import time
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable debug logging for werkzeug
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Create Flask app
app = Flask(__name__, static_url_path='/static')
CORS(app)

# In-memory status tracking
processing_status = {}

# Serve static files
@app.route('/')
def index():
    logger.debug('Serving index.html')
    return send_from_directory('static', 'index.html')

@app.route('/verify')
def verify():
    logger.debug('Serving verify.html')
    return send_from_directory('static', 'verify.html')

@app.route('/library')
def library():
    """Serve library page."""
    logger.debug('Serving library.html')
    return send_from_directory('static', 'library.html')

def process_video_async(video_path: str, video_name: str):
    """Process video in a separate thread."""
    try:
        # Create output directory
        output_dir = Path('library') / video_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        snippets_dir = output_dir / 'snippets'
        snippets_dir.mkdir(parents=True, exist_ok=True)
        videos_dir = output_dir / 'videos'
        videos_dir.mkdir(parents=True, exist_ok=True)
        
        progress = ProgressTracker(video_name, processing_status)
        
        # Check if snippets already exist
        snippets_file = snippets_dir / 'snippets.json'
        
        # Check for existing files
        audio_exists = (output_dir / "audio.mp3").exists()
        transcription_exists = (output_dir / "transcription.json").exists()
        frames_exist = (output_dir / "frames").exists() and any((output_dir / "frames").iterdir())
        snippets_exist = snippets_file.exists()
        videos_exist = videos_dir.exists() and any(videos_dir.iterdir())
        
        if audio_exists and transcription_exists and frames_exist and snippets_exist and videos_exist:
            # Simulate the processing steps with existing files
            progress.using_existing('audio')
            progress.using_existing('transcription')
            progress.using_existing('frames')
            
            with open(snippets_file) as f:
                data = json.load(f)
            
            logger.info(f"Loaded data from {snippets_file}: {data}")
            
            # Add each snippet with its video info
            for snippet in data:
                logger.info(f"Processing snippet: {snippet}")
            
            progress.using_existing('snippets')
            progress.using_existing('video segments')
            progress.complete(len(data))
            logger.info(f"Using existing snippets and videos for: {video_name}")
            return
            
        # Process video
        logger.info(f'Processing video: {video_name}')
        result = process_video(str(video_path), str(output_dir), status_dict=processing_status)
        
        # Create snippets
        progress.creating_snippets()
        logger.info('Creating snippets')
        snippets = process_snippets(
            result['transcription_path'],
            skip_analysis='analysis' in result,
            skip_existing=True
        )
        
        # Cut video into segments
        progress.cutting_video()
        logger.info('Cutting video segments')
        try:
            cut_library_snippets(str(output_dir))
            # Update status only after cutting is complete
            progress.complete(len(snippets))
            logger.info('Video processing complete')
        except Exception as e:
            logger.exception('Error cutting video segments')
            progress.error(str(e))
            raise
        
    except Exception as e:
        logger.exception('Error processing video')
        progress.error(str(e))
        raise

# API Endpoints
@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video upload and audio extraction."""
    logger.debug('Upload request received')
    
    if 'video' not in request.files:
        logger.error('No video file in request')
        return jsonify({'error': 'No video file provided'}), 400
        
    video = request.files['video']
    if video.filename == '':
        logger.error('Empty filename')
        return jsonify({'error': 'No video file selected'}), 400
        
    logger.info(f'Processing video: {video.filename}')
    
    try:
        # Save uploaded video
        video_path = Path('uploads') / video.filename
        video_path.parent.mkdir(exist_ok=True)
        logger.debug(f'Saving video to: {video_path}')
        video.save(str(video_path))
        
        # Initialize status
        video_name = video_path.stem
        logger.debug(f'Video name for status tracking: {video_name}')
        progress = ProgressTracker(video_name, processing_status)
        progress.update('uploading', 'Video uploaded, starting processing...', sleep=False)
        
        # Start processing in a separate thread
        thread = Thread(
            target=process_video_async,
            args=(str(video_path), video_name)
        )
        thread.start()
        
        # Return immediately with success
        return jsonify({
            'status': 'success',
            'video_name': video_name
        })
        
    except Exception as e:
        logger.exception('Error during upload')
        if 'video_name' in locals():
            progress = ProgressTracker(video_name, processing_status)
            progress.error(str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<video_name>')
def get_status(video_name):
    """Get the current processing status for a video."""
    logger.debug(f'Status request for: {video_name}')
    
    if video_name not in processing_status:
        return jsonify({'error': 'Video not found'}), 404
        
    logger.debug(f'Current status: {processing_status[video_name]}')
    return jsonify(processing_status[video_name])

@app.route('/api/transcription/<video_name>')
def get_transcription(video_name):
    """Get the transcription for a video."""
    try:
        # Load transcription JSON
        transcription_path = Path('library') / video_name / 'transcription.json'
        if not transcription_path.exists():
            return jsonify({'error': 'Transcription not found'}), 404
            
        with open(transcription_path) as f:
            data = json.load(f)
            
        return jsonify(data)
        
    except Exception as e:
        logger.exception('Error loading transcription')
        return jsonify({'error': str(e)}), 500

@app.route('/api/snippets/<video_name>')
def get_snippets(video_name):
    """Get the snippets for a video."""
    try:
        # Load snippets JSON
        snippets_path = Path('library') / video_name / 'snippets' / 'snippets.json'
        if not snippets_path.exists():
            return jsonify({'error': 'Snippets not found'}), 404
            
        with open(snippets_path) as f:
            data = json.load(f)
            
        return jsonify(data)
        
    except Exception as e:
        logger.exception('Error loading snippets')
        return jsonify({'error': str(e)}), 500

@app.route('/api/library')
def get_library():
    """Get all snippets in the library."""
    try:
        library_dir = Path('library')
        snippets = []
        
        # List all directories in library
        for item_dir in library_dir.iterdir():
            if not item_dir.is_dir():
                continue
                
            snippets_file = item_dir / 'snippets' / 'snippets.json'
            if not snippets_file.exists():
                continue
            
            with open(snippets_file) as f:
                data = json.load(f)
            
            logger.info(f"Loaded data from {snippets_file}: {data}")
            
            # Get the list of snippets from the data
            snippets_list = data.get('snippets', [])
            
            # Add each snippet with its video info
            for snippet in snippets_list:
                snippet_data = snippet.copy()
                snippet_data['video_name'] = item_dir.name
                video_url = f'/api/video/{item_dir.name}/{snippet["video_path"]}'
                logger.info(f"Setting video URL to: {video_url}")
                snippet_data['video_url'] = video_url
                snippets.append(snippet_data)
        
        return jsonify(snippets)
    except Exception as e:
        logger.exception('Error getting library items')
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/<snippet_id>')
def get_library_item(snippet_id):
    """Get details for a specific snippet."""
    try:
        library_dir = Path('library')
        logger.info(f'Looking for snippet: {snippet_id}')
        
        # Search for the snippet in all video directories
        for item_dir in library_dir.iterdir():
            if not item_dir.is_dir():
                continue
                
            snippets_file = item_dir / 'snippets' / 'snippets.json'
            if not snippets_file.exists():
                continue
                
            with open(snippets_file) as f:
                data = json.load(f)
                
            # Get the list of snippets from the data
            snippets_list = data.get('snippets', [])
                
            # Find matching snippet
            for snippet in snippets_list:
                if snippet['id'] == snippet_id:
                    logger.info(f'Found snippet in {item_dir.name}')
                    logger.info(f'Snippet title: {snippet["title"]}')
                    snippet_data = snippet.copy()
                    # Add video info
                    snippet_data['video_name'] = item_dir.name
                    video_url = f'/api/video/{item_dir.name}/{snippet["video_path"]}'
                    logger.info(f"Setting video URL to: {video_url}")
                    snippet_data['video_url'] = video_url
                    return jsonify(snippet_data)
        
        logger.error(f'Snippet not found: {snippet_id}')
        return jsonify({'error': 'Snippet not found'}), 404
        
    except Exception as e:
        logger.exception('Error getting library item')
        return jsonify({'error': str(e)}), 500

@app.route('/api/library/search')
def search_library():
    """Search snippets."""
    query = request.args.get('q', '').lower()
    try:
        library_dir = Path('library')
        matches = []
        
        for item_dir in library_dir.iterdir():
            if not item_dir.is_dir():
                continue
                
            snippets_file = item_dir / 'snippets' / 'snippets.json'
            if not snippets_file.exists():
                continue
            
            with open(snippets_file) as f:
                data = json.load(f)
            
            # Get the list of snippets from the data
            snippets_list = data.get('snippets', [])
            
            # Add matching snippets
            for snippet in snippets_list:
                if (query in snippet['title'].lower() or 
                    any(query in segment['text'].lower() for segment in snippet['segments'])):
                    snippet_data = snippet.copy()
                    # Add video info
                    snippet_data['video_name'] = item_dir.name
                    snippet_data['id'] = f"{item_dir.name}/{snippet_data['id']}"
                    video_url = f'/api/video/{item_dir.name}/{snippet["video_path"]}'
                    logger.info(f"Setting video URL to: {video_url}")
                    snippet_data['video_url'] = video_url
                    matches.append(snippet_data)
        
        return jsonify(matches)
    except Exception as e:
        logger.exception('Error searching snippets')
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<path:video_path>')
def serve_video(video_path):
    """Serve video file with range request support."""
    try:
        logger.info(f"Raw video path from URL: {video_path}")
        # Ensure the video path is within the library directory
        full_path = Path('library') / video_path
        logger.info(f'Requested video path: {video_path}')
        logger.info(f'Full path: {full_path}')
        logger.info(f'File exists: {full_path.exists()}')
        
        if not full_path.exists():
            logger.error(f'Video file not found: {full_path}')
            return jsonify({'error': 'Video not found'}), 404
            
        logger.info(f'Serving video file: {full_path}')
        
        # Get file size
        file_size = full_path.stat().st_size
        
        # Get file extension and set MIME type
        ext = full_path.suffix.lower()
        mime_type = 'video/mp4' if ext == '.mp4' else 'video/quicktime' if ext == '.mov' else 'application/octet-stream'
        
        # Handle range request
        range_header = request.headers.get('Range')
        
        if range_header:
            logger.info(f'Range request: {range_header}')
            # Parse range header
            byte1, byte2 = 0, None
            match = re.search(r'(\d+)-(\d*)', range_header)
            groups = match.groups()
            
            if groups[0]: byte1 = int(groups[0])
            if groups[1]: byte2 = int(groups[1])
            
            if byte2 is None:
                byte2 = file_size - 1
            
            length = byte2 - byte1 + 1
            
            # Create response
            response = make_response()
            response.headers['Content-Range'] = f'bytes {byte1}-{byte2}/{file_size}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(length)
            response.headers['Content-Type'] = mime_type
            response.status_code = 206
            
            # Open file and seek to start byte
            with open(str(full_path), 'rb') as f:
                f.seek(byte1)
                response.data = f.read(length)
                
            return response
            
        # Non-range request - serve entire file
        response = make_response(send_file(
            str(full_path),
            mimetype=mime_type,
            as_attachment=False
        ))
        response.headers['Accept-Ranges'] = 'bytes'
        return response
        
    except Exception as e:
        logger.exception('Error serving video')
        return jsonify({'error': str(e)}), 500

@app.route('/api/frame/<path:frame_path>')
def serve_frame(frame_path):
    """Serve a frame image."""
    try:
        # Ensure the frame path is within the library directory
        full_path = Path('library') / frame_path
        logger.debug(f'Serving frame: {full_path}')
        
        if not full_path.exists():
            logger.error(f'Frame not found: {full_path}')
            return jsonify({'error': 'Frame not found'}), 404
            
        return send_file(str(full_path))
        
    except Exception as e:
        logger.exception('Error serving frame')
        return jsonify({'error': str(e)}), 500

@app.route('/api/snippets', methods=['POST'])
def create_video_snippets():
    """Create snippets from video segments."""
    if 'transcription_path' not in request.json:
        return jsonify({'error': 'No transcription path provided'}), 400
        
    transcription_path = request.json['transcription_path']
    if not Path(transcription_path).exists():
        return jsonify({'error': 'Transcription file not found'}), 404
        
    # Get skip options from request
    skip_analysis = request.json.get('skip_analysis', False)
    skip_existing = request.json.get('skip_existing', False)
    
    try:
        snippets = process_snippets(
            transcription_path,
            skip_analysis=skip_analysis,
            skip_existing=skip_existing
        )
        return jsonify({'snippets': snippets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    """Process a video file."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'No video file selected'}), 400
        
    # Get skip options from request
    skip_audio = request.form.get('skip_audio', '').lower() == 'true'
    skip_transcription = request.form.get('skip_transcription', '').lower() == 'true'
    skip_frames = request.form.get('skip_frames', '').lower() == 'true'
    
    # Save the uploaded file
    video_path = Path('uploads') / video_file.filename
    video_path.parent.mkdir(exist_ok=True)
    video_file.save(str(video_path))
    
    # Create a unique output directory for this video
    video_id = video_path.stem
    output_dir = Path('library') / video_id
    
    try:
        # Process the video with skip options
        result = process_video(
            str(video_path), 
            str(output_dir),
            status_dict=processing_status,
            skip_audio=skip_audio,
            skip_transcription=skip_transcription,
            skip_frames=skip_frames
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info('Starting Flask server')
    app.run(debug=True, port=5000)
