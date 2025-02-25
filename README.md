# Snuttification

A web application for processing videos with automatic transcription, frame extraction, and smart snippet generation.

## Features

- Upload and process videos
- Extract audio using FFmpeg
- Automatic transcription with timestamps using OpenAI Whisper API
- Extract frames from key moments in the video
- AI-powered content analysis with GPT-4o
- Automatic snippet generation based on objects and actions
- View transcriptions with associated frames and snippets
- Modern web interface with real-time progress tracking

## Project Structure

```
Snuttification/
├── processing/           # Processing modules
│   ├── video.py         # Video processing (audio, frames)
│   ├── transcribe.py    # Audio transcription with Whisper
│   └── snippets.py      # Content analysis and snippet creation
├── static/              # Frontend assets
│   ├── js/             # JavaScript files
│   ├── css/            # CSS files
│   ├── index.html      # Upload page
│   └── verify.html     # Transcription viewer
├── uploads/            # Temporary upload storage
├── library/           # Processed video library
│   └── <video_name>/  # Per-video storage
│       ├── audio.mp3  # Extracted audio
│       ├── frames/    # Extracted frames
│       ├── snippets/  # Generated snippets
│       └── transcription.json  # Transcription and analysis
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
   - Analyzed to generate snippets
4. View the results at /verify when complete

## Development

- Code style: PEP 8
- Logging: Python standard library logging
- Error handling: Detailed error messages and status tracking
- Asynchronous processing: Threading for long-running tasks

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-sa/4.0/).

![CC BY-SA 4.0](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)
