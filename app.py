"""
VideoSnippets API Server
Handles HTTP endpoints and request routing.
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import logging
import threading
import json
from processing.video import process_video

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def process_video_async(video_path, video_name):
    """Process video in a separate thread."""
    try:
        # Create output directory
        output_dir = Path('library') / video_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process video
        result = process_video(str(video_path), str(output_dir), processing_status)
        
        # Update status
        processing_status[video_name] = {
            'status': 'complete',
            'message': 'Processing complete!'
        }
        
        logger.info('Video processing complete')
        return result
        
    except Exception as e:
        logger.exception('Error processing video')
        processing_status[video_name] = {
            'status': 'error',
            'message': str(e)
        }
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
        processing_status[video_name] = {
            'status': 'uploading',
            'message': 'Video uploaded, starting processing...'
        }
        
        # Start processing in a separate thread
        thread = threading.Thread(
            target=process_video_async,
            args=(video_path, video_name)
        )
        thread.start()
        
        # Return immediately with success
        return jsonify({
            'status': 'success',
            'video_name': video_name
        })
        
    except Exception as e:
        logger.exception('Error during upload')
        if video_name in processing_status:
            processing_status[video_name] = {
                'status': 'error',
                'message': str(e)
            }
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

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
    logger.debug(f'Transcription request for: {video_name}')
    
    try:
        transcription_path = Path('library') / video_name / 'transcription.json'
        if not transcription_path.exists():
            return jsonify({'error': 'Transcription not found'}), 404
            
        with open(transcription_path) as f:
            transcription = json.load(f)
            
        return jsonify(transcription)
        
    except Exception as e:
        logger.exception('Error reading transcription')
        return jsonify({
            'error': f'Error reading transcription: {str(e)}'
        }), 500

if __name__ == '__main__':
    logger.info('Starting Flask server')
    app.run(debug=True, port=5000)
