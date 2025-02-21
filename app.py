"""
VideoSnippets API Server
Handles HTTP endpoints and request routing.
"""
from flask import Flask, jsonify, request, send_from_directory, send_file, make_response
from flask_cors import CORS
from pathlib import Path
import logging
import threading
import json
import re
from processing.video import process_video
from processing.snippets import load_and_simplify_segments, get_structured_output, create_snippets

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

@app.route('/library')
def library():
    """Serve library page."""
    logger.debug('Serving library.html')
    return send_from_directory('static', 'library.html')

def process_video_async(video_path, video_name):
    """Process video in a separate thread."""
    try:
        # Create output directory
        output_dir = Path('library') / video_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process video (audio, transcription, frames)
        result = process_video(str(video_path), str(output_dir), processing_status)
        
        # Create snippets
        processing_status[video_name] = {
            'status': 'creating_snippets',
            'message': 'Analyzing content and creating snippets...'
        }
        
        # Load and analyze segments
        transcription_path = result['transcription_path']
        simplified_text, language, segments_data = load_and_simplify_segments(transcription_path)
        analysis = get_structured_output(simplified_text, language, segments_data, transcription_path)
        
        # Create snippets directory
        snippets_dir = output_dir / 'snippets'
        snippets = create_snippets(segments_data, str(snippets_dir))
        
        # Update status
        processing_status[video_name] = {
            'status': 'complete',
            'message': f'Processing complete. Created {len(snippets)} snippets!'
        }
        
        logger.info('Video processing complete')
        
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
    try:
        # Load transcription JSON
        transcription_path = Path('library') / video_name / 'transcription.json'
        if not transcription_path.exists():
            return jsonify({'error': 'Transcription not found'}), 404
            
        with open(transcription_path, 'r', encoding='utf-8') as f:
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
            
        with open(snippets_path, 'r', encoding='utf-8') as f:
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
                
            # Add each snippet with its video info
            for snippet in data['snippets']:
                snippets.append({
                    'id': snippet['title'],
                    'title': snippet['title'],
                    'description': snippet['description'] if 'description' in snippet else '',
                    'video_name': item_dir.name,
                    'segments': snippet['segments']
                })
        
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
                
            # Find matching snippet
            for snippet in data['snippets']:
                if snippet['title'] == snippet_id:
                    logger.info(f'Found snippet in {item_dir.name}')
                    logger.info(f'Snippet title: {snippet["title"]}')
                    return jsonify({
                        'id': snippet['title'],
                        'title': snippet['title'],
                        'description': snippet['description'] if 'description' in snippet else '',
                        'video_name': item_dir.name,
                        'segments': snippet['segments']
                    })
        
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
        snippets = []
        
        for item_dir in library_dir.iterdir():
            if not item_dir.is_dir():
                continue
                
            snippets_file = item_dir / 'snippets' / 'snippets.json'
            if not snippets_file.exists():
                continue
            
            with open(snippets_file) as f:
                data = json.load(f)
            
            # Search in snippet titles and text
            for snippet in data['snippets']:
                if (query in snippet['title'].lower() or 
                    any(query in segment['text'].lower() for segment in snippet['segments'])):
                    snippets.append({
                        'id': f"{item_dir.name}/{snippet['title']}",
                        'title': snippet['title'],
                        'description': snippet.get('description', ''),
                        'video_path': snippet.get('video_path', ''),
                        'segments': snippet['segments']
                    })
        
        return jsonify(snippets)
    except Exception as e:
        logger.exception('Error searching snippets')
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<path:video_path>')
def serve_video(video_path):
    """Serve video file with range request support."""
    try:
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
            match = re.search('(\d+)-(\d*)', range_header)
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

if __name__ == '__main__':
    logger.info('Starting Flask server')
    app.run(debug=True, port=5000)
