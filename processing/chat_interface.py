"""
Chat interface for curating video snippets and generating audio responses.
"""
import logging
import argparse
import datetime
import base64
import json
from pathlib import Path
from openai import OpenAI
import sys
import os
import hashlib

# Add the processing directory to Python path when running as script
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

# Set up logging
logger = logging.getLogger(__name__)
llm_logger = logging.getLogger("llm_calls")

def setup_logging(log_dir="logs"):
    """Set up logging configuration"""
    log_dir = Path(log_dir)
    log_dir = log_dir if log_dir.is_absolute() else Path.cwd() / log_dir
    log_dir.mkdir(exist_ok=True)
    
    print(f"Setting up logging in: {log_dir}")
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create handlers
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"llm_calls_{current_time}.log"
    print(f"Log file will be: {log_file}")
    
    llm_handler = logging.FileHandler(log_file)
    llm_handler.setFormatter(file_formatter)
    
    # Set up LLM logger
    llm_logger.setLevel(logging.DEBUG)
    llm_logger.addHandler(llm_handler)
    
    # Set up main logger
    logger.setLevel(logging.INFO)
    
    print(f"Logging initialized. Check {log_file} for details.")

class VideoSnippetChat:
    def __init__(self, library_path=None):
        """
        Initialize the chat interface.
        
        Args:
            library_path: Path to video library directory
        """
        self.client = OpenAI()
        self.library_path = Path(library_path) if library_path else Path.cwd()
        self.conversation_history = []
        
    def add_message(self, role, content=None, audio_id=None):
        """Add a message to the conversation history."""
        message = {"role": role}
        if content:
            message["content"] = content
        if audio_id:
            message["audio"] = {"id": audio_id}
        self.conversation_history.append(message)
        
    def get_available_snippets(self):
        """
        Get all available snippets from the library.
        
        Returns:
            dict: Dictionary of snippets with their metadata
        """
        all_snippets = {}
        
        llm_logger.debug(f"Looking for snippets in: {self.library_path}")
        
        # Search through all parent video directories in library
        for parent_dir in self.library_path.glob("*"):
            if not parent_dir.is_dir():
                continue
                
            llm_logger.debug(f"Checking directory: {parent_dir}")
            
            # Look for snippets.json in the snippets subdirectory
            snippets_dir = parent_dir / "snippets"
            snippets_file = snippets_dir / "snippets.json"
            
            llm_logger.debug(f"Looking for snippets file: {snippets_file}")
            llm_logger.debug(f"Snippets file exists: {snippets_file.exists()}")
            
            if not snippets_file.exists():
                llm_logger.warning(f"No snippets.json found in {parent_dir}/snippets")
                continue
                
            try:
                with open(snippets_file) as f:
                    snippets_data = json.load(f)
                    llm_logger.debug(f"Successfully loaded snippets from {snippets_file}")
                    llm_logger.debug(f"Snippets data: {json.dumps(snippets_data, indent=2)}")
                    all_snippets[parent_dir.name] = snippets_data
            except json.JSONDecodeError as e:
                llm_logger.error(f"Failed to parse snippets file {snippets_file}: {str(e)}")
                continue
            except Exception as e:
                llm_logger.error(f"Error reading snippets file {snippets_file}: {str(e)}")
                continue
        
        llm_logger.debug(f"Total snippets found: {len(all_snippets)}")
        llm_logger.debug(f"All snippets: {json.dumps(all_snippets, indent=2)}")
        
        return all_snippets
        
    def search_snippets(self, query, snippets_context=None):
        """
        Search for relevant video snippets based on user query.
        
        Args:
            query: User's search query
            snippets_context: Pre-formatted snippets data with transcripts
            
        Returns:
            tuple: (List of relevant video paths, List of snippet contexts)
        """
        # Add user query to conversation
        self.add_message("user", content=query)
        
        # Get snippets context if not provided
        if snippets_context is None:
            # Get all available snippets
            all_snippets = self.get_available_snippets()
            
            if not all_snippets:
                logger.warning("No snippets found in library")
                return [], []
            
            # Format snippets data for GPT analysis
            snippets_context = []
            for parent_video, snippets in all_snippets.items():
                for snippet_id, data in snippets.items():
                    if "transcript" in data:
                        snippets_context.append({
                            "id": f"{parent_video}/{snippet_id}",
                            "transcript": data["transcript"],
                            "start": data.get("start", 0),
                            "end": data.get("end", 0)
                        })
        
        if not snippets_context:
            logger.warning("No snippets with transcripts found")
            return [], []
        
        # Log the context being sent to GPT
        llm_logger.debug(f"Snippets context for query '{query}':\n{json.dumps(snippets_context, indent=2)}")
        
        # Use OpenAI to find relevant snippets
        messages = [
            {"role": "system", "content": """You are a helpful assistant that finds relevant video snippets based on user queries.
            For each snippet, analyze its transcript and determine if it's relevant to the user's query.
            Return only the IDs of relevant snippets in a JSON array."""},
            {"role": "user", "content": f"""Here are the available video snippets with their transcripts:
            {json.dumps(snippets_context, indent=2)}
            
            Query: {query}
            
            Return only the relevant snippet IDs in a JSON array."""}
        ]
        
        # Log the messages being sent to GPT
        llm_logger.debug(f"Messages to GPT:\n{json.dumps(messages, indent=2)}")
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            response_format={ "type": "json_object" }
        )
        
        # Log the GPT response
        llm_logger.debug(f"GPT Response:\n{response.choices[0].message.content}")
        
        try:
            result = json.loads(response.choices[0].message.content)
            relevant_ids = result.get("relevant_snippets", [])
            
            # Log the parsed results
            llm_logger.debug(f"Parsed relevant IDs: {relevant_ids}")
            
            # Convert IDs to full paths and keep relevant contexts
            relevant_snippets = []
            relevant_contexts = []
            for snippet_id in relevant_ids:
                parent_video, snippet_name = snippet_id.split("/")
                video_dir = self.library_path / parent_video / "videos"
                if video_dir.exists():
                    snippet_path = video_dir / f"{snippet_name}.mp4"
                    if snippet_path.exists():
                        relevant_snippets.append(str(snippet_path))
                        # Find and keep the relevant context
                        for context in snippets_context:
                            if context["id"] == snippet_id:
                                relevant_contexts.append(context)
                                break
            
            # Log the final snippet paths
            llm_logger.debug(f"Found snippet paths: {relevant_snippets}")
            llm_logger.debug(f"Found snippet contexts: {json.dumps(relevant_contexts, indent=2)}")
            return relevant_snippets, relevant_contexts
            
        except (json.JSONDecodeError, KeyError) as e:
            llm_logger.error(f"Failed to parse GPT response: {e}")
            return [], []
        
    def generate_audio_response(self, query, output_path, relevant_snippets=None, snippets_context=None):
        """
        Generate audio response using OpenAI's chat completions with audio modality.
        
        Args:
            query: Text query to respond to
            output_path: Path to save audio file
            relevant_snippets: List of relevant snippet paths
            snippets_context: List of snippet contexts with transcripts
            
        Returns:
            dict containing audio path, transcript, and audio_id
        """
        # Create system message with context about available snippets
        system_message = {
            "role": "system",
            "content": "You are a helpful assistant that provides concise responses about video content. "
        }
        
        # Add snippets context if available
        if snippets_context and relevant_snippets:
            relevant_info = []
            for snippet in snippets_context:
                if any(snippet['id'] in path for path in relevant_snippets):
                    relevant_info.append({
                        'id': snippet['id'],
                        'transcript': snippet['transcript']
                    })
            
            if relevant_info:
                system_message["content"] += f"\nHere are the relevant video snippets:\n{json.dumps(relevant_info, indent=2)}"
        
        messages = [
            system_message,
            {"role": "user", "content": query}
        ]
        
        # Log the messages being sent for audio generation
        llm_logger.debug(f"Messages for audio generation:\n{json.dumps(messages, indent=2)}")
        
        response = self.client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text", "audio"],
            audio={"voice": "alloy", "format": "wav"},
            messages=messages
        )
        
        # Log the audio response metadata
        llm_logger.debug(f"Audio response metadata:\nTranscript: {response.choices[0].message.audio.transcript}\nAudio ID: {response.choices[0].message.audio.id}")
        
        # Get the response data
        choice = response.choices[0]
        message = choice.message
        
        # Save the audio file
        output_path = Path(output_path)
        with open(output_path, 'wb') as f:
            audio_data = base64.b64decode(message.audio.data)
            f.write(audio_data)
            
        # Add assistant's response to conversation history
        self.add_message("assistant", audio_id=message.audio.id)
        
        return {
            "audio_path": str(output_path),
            "transcript": message.audio.transcript,
            "audio_id": message.audio.id
        }
        
    def chat(self, query, output_dir=None):
        """
        Process a chat query and return a response.
        
        Args:
            query (str): The user's query
            output_dir (Path, optional): Directory to save audio responses
            
        Returns:
            dict: Response containing text and audio path
        """
        # Get available snippets
        snippets = self.get_available_snippets()
        
        # Format snippets for context
        snippets_text = []
        for parent_video, snippets_data in snippets.items():
            for snippet in snippets_data.get('snippets', []):
                if snippet.get('description'):
                    snippets_text.append(f"{parent_video} - {snippet.get('title', 'unknown')}: {snippet.get('description')}")
        
        # Create system message with snippets context
        system_message = {
            "role": "system",
            "content": (
                "You are a helpful assistant that provides concise responses about video content.\n\n"
                "Available video snippets:\n"
                "=======================\n"
                "\n".join(snippets_text) + "\n"
                "Analyze the user's query and provide a relevant response based on these video snippets."
            )
        }
        
        # Create user message
        user_message = {
            "role": "user",
            "content": f"Based on the query: {query}, provide a brief response about the relevant video snippets."
        }
        
        messages = [system_message, user_message]
        
        # Log the messages being sent
        llm_logger.debug(f"Messages for audio generation:\n{json.dumps(messages, indent=2)}")
        
        # Get text response from OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        text_response = response.choices[0].message.content
        
        # Generate audio response
        audio_response = self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text_response
        )
        
        # Save audio response if output directory provided
        audio_path = None
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            audio_id = hashlib.md5(text_response.encode()).hexdigest()
            audio_path = output_dir / f"audio_{audio_id}.mp3"
            audio_response.stream_to_file(audio_path)
            
            # Log the response
            llm_logger.debug(f"Audio response metadata:\nTranscript: {text_response}\nAudio ID: audio_{audio_id}")
        
        return {
            "text_response": text_response,
            "audio_path": str(audio_path) if audio_path else None
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat interface for video snippet curation")
    parser.add_argument("--library", "-l", type=str, help="Path to video library", default="./library")
    parser.add_argument("--output", "-o", type=str, help="Output directory for responses", default="./chat_responses")
    parser.add_argument("--log-dir", type=str, help="Directory for log files", default="./logs")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_dir)
    llm_logger.info("Starting VideoSnippet Chat Interface")
    
    # Initialize chat interface
    chat = VideoSnippetChat(library_path=args.library)
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Get and display available snippets
    all_snippets = chat.get_available_snippets()
    
    # Log all available snippets
    llm_logger.info("Available snippets at startup:")
    if not all_snippets:
        llm_logger.warning("No snippets found in library!")
    else:
        for parent_video, snippets_data in all_snippets.items():
            llm_logger.info(f"\nParent Video: {parent_video}")
            for snippet in snippets_data.get('snippets', []):
                for segment in snippet.get('segments', []):
                    snippet_info = {
                        "id": f"{parent_video}/{snippet.get('title', 'unknown')}",
                        "transcript": segment.get('text', 'No transcript'),
                        "start": segment.get('start', 0),
                        "end": segment.get('end', 0),
                        "description": snippet.get('description', '')
                    }
                    llm_logger.info(f"Snippet: {json.dumps(snippet_info, indent=2)}")
    
    # Format snippets data for GPT analysis
    snippets_text = []
    for parent_video, snippets_data in all_snippets.items():
        for snippet in snippets_data.get('snippets', []):
            if snippet.get('description'):
                snippets_text.append(f"{parent_video} - {snippet.get('title', 'unknown')}: {snippet.get('description')}")
    
    # Create and log the system message that will be used for chat
    system_message = {
        "role": "system",
        "content": (
            "You are a helpful assistant that provides concise responses about video content.\n\n"
            "Available video snippets:\n"
            "=======================\n"
            "\n".join(snippets_text) + "\n"
            "Analyze the user's query and provide a relevant response based on these video snippets."
        )
    }
    llm_logger.info("System message that will be used for chat:")
    llm_logger.info(system_message["content"])
    
    print("\nVideoSnippet Chat Interface")
    print("==========================")
    print(f"Library path: {args.library}")
    print(f"Output directory: {args.output}")
    print(f"Log directory: {args.log_dir}")
    print("\nAvailable Snippets:")
    print("-----------------")
    
    if not all_snippets:
        print("No snippets found in library!")
    else:
        for parent_video, snippets_data in all_snippets.items():
            print(f"\nParent Video: {parent_video}")
            for snippet in snippets_data.get('snippets', []):
                print(f"  - {snippet.get('title', 'unknown')}")
                if 'description' in snippet:
                    print(f"    Description: {snippet['description']}")
                if 'segments' in snippet:
                    total_duration = snippet['segments'][-1].get('end', 0) - snippet['segments'][0].get('start', 0)
                    print(f"    Duration: {total_duration:.1f}s")
                    # Show first 100 chars of combined transcript
                    full_transcript = ' '.join(segment.get('text', '') for segment in snippet['segments'])
                    transcript_preview = full_transcript[:100] + "..." if len(full_transcript) > 100 else full_transcript
                    print(f"    Transcript: {transcript_preview}")
    
    print("\nType 'quit' or 'exit' to end the conversation")
    print()
    
    while True:
        try:
            # Get user input
            query = input("\nYour query: ").strip()
            
            # Check for exit command
            if query.lower() in ['quit', 'exit']:
                print("\nGoodbye!")
                break
            
            if not query:
                continue
            
            # Process query and get response
            print("\nProcessing your query...")
            response = chat.chat(query, output_dir=output_dir)
            
            # Display results
            print("\nResponse:")
            print("---------")
            print(response['text_response'])
            print(f"\nAudio response saved to: {response['audio_path']}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            print(f"\nError: {str(e)}")
            continue
