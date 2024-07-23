import tempfile
import os
from openai import OpenAI
import pygame
import time
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

# Retrieve the OpenAI API key and Porcupine access key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
assistant_api_key = os.getenv("ASSISTANT_API_KEY")

sd.default.device = None  # 'seeed-2mic-voicecard'

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key, default_headers={"OpenAI-Beta": "assistants=v2"})

thread_id = None  # Store the thread ID

def query_and_record(prompt):
    """
    Send a prompt to the OpenAI assistant and record the response as an MP3 file.
    """
    assistant_id = assistant_api_key

    global thread_id  # Access the global thread ID

    if not prompt.strip():
        print("Error: The prompt is empty.")
        return

    if thread_id is None:
        # Create a thread for communication
        thread = client.beta.threads.create()
        thread_id = thread.id
        print(f"New thread created with ID: {thread_id}")
    else:
        # Retrieve the existing thread
        thread = client.beta.threads.retrieve(thread_id)
        print(f"Using existing thread with ID: {thread_id}")

    try:
        # Send user's prompt to the AI
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        
        # Start the AI to process the user prompt
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id,
            instructions="Please address the user as Jane Doe. The user has a premium account."
        )
        
        # Wait until AI is complete with processing
        while run.status in ["in_progress", "queued"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status == "completed":
            message_list = client.beta.threads.messages.list(
                thread_id=thread.id
            )

            # Ensure there's a valid response
            if not message_list.data or not message_list.data[0].content:
                print("Error: No response content available.")
                return

            text_response = message_list.data[0].content[0].text.value

            # Generate an audio response from the text
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice="echo",
                input=text_response,
            )

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmpfile:
                mp3_filename = tmpfile.name
                response.stream_to_file(mp3_filename)

            print("Response recorded to " + mp3_filename)

            # Initialize pygame mixer
            pygame.mixer.init()

            # Load the mp3 file
            pygame.mixer.music.load(mp3_filename)

            # Play the mp3 file
            pygame.mixer.music.play()

            # Wait until the response finishes playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

    except Exception as e:
        print("Error during query and recording:", str(e))


def handle_interaction(prompt):
    """
    Handle the interaction with the AI.
    """
    query_and_record(prompt)
