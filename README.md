# VideoSnippets2

A web application for processing videos with automatic transcription and frame extraction.

## Features

- Upload and process videos
- Extract audio using FFmpeg
- Automatic transcription with timestamps using OpenAI Whisper API
- Extract frames from key moments in the video
- View transcriptions with associated frames
- Modern web interface with real-time progress tracking

## Project Structure

```
VideoSnippets2/
├── processing/           # Processing modules
│   ├── video.py         # Video processing (audio extraction, frames)
│   └── transcribe.py    # Audio transcription with Whisper
├── static/              # Frontend assets
│   ├── js/             # JavaScript files
│   ├── css/            # CSS files
│   ├── index.html      # Upload page
│   └── verify.html     # Transcription viewer
├── uploads/            # Temporary upload storage
├── library/           # Processed video library
├── app.py             # Flask application
└── requirements.txt   # Python dependencies
```

## Requirements

- Python 3.10+
- FFmpeg
- OpenAI API key
- OpenCV

## Setup

1. Install FFmpeg:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # macOS
   brew install ffmpeg
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY=your_key_here
   ```

5. Run the application:
   ```bash
   python app.py
   ```

The app will be available at http://localhost:5000

## Usage

1. Open http://localhost:5000 in your browser
2. Upload a video file
3. Watch the progress as the video is:
   - Processed to extract audio
   - Transcribed with Whisper
   - Analyzed to extract key frames
4. View the results at /verify when complete

## Development

- Code style: PEP 8
- Logging: Python standard library logging
- Error handling: Detailed error messages and status tracking
- Asynchronous processing: Threading for long-running tasks

## License

MIT License
