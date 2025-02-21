"""
Audio processing module for transcribing audio with timestamps.
"""
import logging
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

def process_audio(audio_path):
    """
    Process audio file to get transcription with timestamps.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        dict: Transcription data with word-level timestamps
    """
    logger.info(f"Processing audio file: {audio_path}")
    return transcribe_audio(audio_path)

def transcribe_audio(input_file, language="sv"):
    """
    Transcribe audio file with word-level timestamps
    
    Args:
        input_file: Path to input audio file
        language: Language code (default: sv for Swedish)
    
    Returns:
        Dictionary containing transcription data
    """
    client = OpenAI()
    
    try:
        with open(input_file, "rb") as audio_file:
            logger.info(f"Transcribing {input_file}...")
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format='verbose_json',
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

            segments_data = []
            for segment in response.segments:
                segment_data = {
                    'text': segment.text,
                    'start': segment.start,
                    'end': segment.end,
                    'duration': round(segment.end - segment.start, 3)
                }
                segments_data.append(segment_data)
            
            # Create final output structure
            transcription_data = {
                'metadata': {
                    'filename': Path(input_file).name,
                    'filepath': str(Path(input_file).absolute()),
                    'language': language,
                    'duration': round(response.duration, 2)
                },
                'text': response.text,
                'segments': segments_data,
                'words': words_data
            }
            
            logger.info("Transcription complete")
            return transcription_data
            
    except Exception as e:
        logger.exception(f"Error transcribing {input_file}")
        raise
