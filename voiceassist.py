"""
This script is designed for detecting a wake word and handling voice interactions with an OpenAI assistant. 
The script performs the following tasks:

1. Imports necessary libraries such as sounddevice, numpy, tempfile, wavio, and OpenAI.
2. Loads environment variables to retrieve the OpenAI API key and Porcupine access key, which are essential for authentication and wake word detection.
3. Initializes the Porcupine wake word engine to listen for specific keywords ("picovoice" and "bumblebee").
4. Sets up an OpenAI client for sending user prompts and receiving responses.
5. Defines functions to:
   - Detect the wake word using an audio stream.
   - Record audio until silence is detected, indicating the end of the user's command.
   - Handle follow-up commands by continuously listening after the initial response.
6. The main loop continuously listens for the wake word and handles interactions as long as the script is running.
7. Ensures proper cleanup by deleting the Porcupine instance when the script is interrupted.
"""
#import necessary libraries
import sounddevice as sd
import numpy as np
import tempfile
import wavio
from openai import OpenAI
import threading
import os
import pvporcupine
import time
from response import handle_interaction
from dotenv import load_dotenv
import schedule
import datetime

# Load environment variables from a .env file
load_dotenv()

# Retrieve API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")

# Check if API keys are properly set
if not openai_api_key:
    raise ValueError("OpenAI API key is not set in environment variables.")
if not porcupine_access_key:
    raise ValueError("Porcupine access key is not set in environment variables.")

# Initialize Porcupine wake word engine with specific keywords
porcupine = pvporcupine.create(
    access_key=porcupine_access_key,
    keywords=["picovoice", "bumblebee"]
)

# Set up the OpenAI client with the provided API key
client = OpenAI(api_key=openai_api_key, default_headers={"OpenAI-Beta": "assistants=v2"})

# Define the audio stream parameters
frame_length = porcupine.frame_length
sample_rate = porcupine.sample_rate

# List to store reminders
reminders = []

#check if a given audio chunk is silent
def is_silent(chunk, threshold=1000):
    rms = np.sqrt(np.mean(np.square(chunk)))
    return rms < threshold

#detect the wake word
def detect_wake_word():
    try:
        # Open an audio input stream
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            while True:
                # Read audio data from the stream
                pcm = stream.read(frame_length)[0]
                pcm = np.frombuffer(pcm, dtype=np.int16)
                # Process the audio data to detect the wake word
                keyword_index = porcupine.process(pcm)

                if keyword_index == 0:
                    print("Detected 'picovoice'")
                    return 'picovoice'
                elif keyword_index == 1:
                    print("Detected 'bumblebee'")
                    return 'bumblebee'
    except KeyboardInterrupt:
        print("Script interrupted.")

# Function to record audio until silence is detected
def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=1000, silence_duration=10):
    print("Recording... Press Ctrl+C to stop.")
    audio_file = []
    silence_start_time = None
    
    try:
       # Open an audio input stream with a callback to append recorded data
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16', callback=lambda indata, frames, time, status: audio_file.append(indata.copy())):
            while True:
                if len(audio_file) > 0:
                    last_chunk = audio_file[-1]

                     # Check if the last chunk of audio is silent
                    if is_silent(last_chunk, silence_threshold):
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > silence_duration:
                            print("Silence detected, stopping recording.")
                            break
                    else:
                        silence_start_time = None

    except KeyboardInterrupt:
        print("Recording stopped manually.")
    
    return np.concatenate(audio_file, axis=0) if audio_file else np.array([])

def extract_time_info(command, keyword):
    if keyword in command.lower():
        try:
            time_part = command.split("at")[-1].strip()
            reminder_time = datetime.datetime.strptime(time_part, "%I:%M %p").time()
            return reminder_time
        except Exception as e:
            print(f"Error parsing {keyword} time: {e}")
    return None

def handle_follow_up():
    print("Listening for follow-up command...")
    audio_file = record_audio(silence_duration=5)
    
    if len(audio_file) > 0:
        # Save the recorded audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            tmpfilename = tmpfile.name
            wavio.write(tmpfilename, audio_file, 44100, sampwidth=2)

        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=open(tmpfilename, "rb"),
        )
        # Transcribe the recorded audio using OpenAI's Whisper model
        transcription_text = transcription.text.strip()
        print("Transcription:", transcription_text)

        # Check if the transcription is empty or too short
        if len(transcription_text) == 0 or len(transcription_text) < 10:
            print("No valid input detected, returning to wake word detection.")
            wake_word_thread = threading.Thread(target=detect_wake_word_instance)
            wake_word_thread.start()
            return
        
        reminder_time = extract_time_info(transcription_text, "remind me to")

        if reminder_time:
            reminder_text = transcription_text.split("remind me to")[1].split("at")[0].strip()
            store_reminder(reminder_time, reminder_text)
        else:
            interaction_thread = threading.Thread(target=handle_interaction, args=(transcription_text,))
            interaction_thread.start()
            interaction_thread.join()

        handle_follow_up()
    else:
        print("No follow-up detected. Restarting wake word detection.")
        wake_word_thread = threading.Thread(target=detect_wake_word_instance)
        wake_word_thread.start()

def store_reminder(reminder_time, reminder_text):
    reminder_datetime = datetime.datetime.combine(datetime.datetime.now().date(), reminder_time)
    reminders.append({"time": reminder_datetime, "text": reminder_text})
    print(f"Reminder set: '{reminder_text}' at {reminder_datetime.strftime('%I:%M %p')}")

def check_reminders():
    while True:
        now = datetime.datetime.now()
        
        # Check reminders
        for reminder in reminders:
            if now >= reminder["time"]:
                print(f"Reminder: {reminder['text']}")
                reminders.remove(reminder)
                
        time.sleep(30)

def detect_wake_word_instance():
    while True:
        wake_word = detect_wake_word()
        if wake_word == 'bumblebee':
            handle_follow_up()
        else:
            break

# Start the reminder checking thread
check_thread = threading.Thread(target=check_reminders, daemon=True)
check_thread.start()

try:
    while True:
        wake_word_thread = threading.Thread(target=detect_wake_word_instance)
        wake_word_thread.start()
        wake_word_thread.join()

except KeyboardInterrupt:
    print("Script interrupted.")
finally:
    if porcupine is not None:
        porcupine.delete()
