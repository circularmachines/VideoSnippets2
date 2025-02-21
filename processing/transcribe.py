"""
Audio transcription module using OpenAI Whisper API
"""
import json
from pathlib import Path
import logging
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path, output_dir):
    """
    Transcribe audio file using OpenAI Whisper API and save results
    Returns path to transcription file
    """
    logger.info(f"Starting transcription for: {audio_path}")
    
    client = OpenAI()
    
    try:
        with open(audio_path, "rb") as audio_file:
            logger.info("Calling Whisper API...")
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=None,
                response_format="verbose_json",
                timestamp_granularities=['word', 'segment']
            )
            
            # Extract word-level data
            words_data = []
            for word in response.words:
                word_data = {
                    'text': word.word,
                    'start': word.start,
                    'end': word.end,
                    'duration': round(word.end - word.start, 3)
                }
                words_data.append(word_data)

            # Extract segment-level data
            segments_data = []
            for segment in response.segments:
                segment_data = {
                    'text': segment.text,
                    'start': segment.start,
                    'end': segment.end,
                    'duration': round(segment.end - segment.start, 3)
                }
                segments_data.append(segment_data)
            
            # Combine into final result
            result = {
                'text': response.text,
                'segments': segments_data,
                'words': words_data,
                'language': response.language
            }
            
            # Save transcription
            output_path = Path(output_dir) / "transcription.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved transcription to: {output_path}")
            
            return str(output_path)
            
    except Exception as e:
        logger.exception("Error during transcription")
        raise RuntimeError(f"Failed to transcribe audio: {str(e)}")
