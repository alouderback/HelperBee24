import sounddevice as sd
import numpy as np
import tempfile
import wavio
from openai import OpenAI
import threading
import os
import pvporcupine
from pvrecorder import PvRecorder
import time
from response import handle_interaction  # Import the interaction handling function
from dotenv import load_dotenv

load_dotenv()

# Retrieve the OpenAI API key and Porcupine access key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")

sd.default.device = None  # 'seeed-2mic-voicecard'

if not openai_api_key:
    raise ValueError("OpenAI API key is not set in environment variables.")
if not porcupine_access_key:
    raise ValueError("Porcupine access key is not set in environment variables.")

# Initialize Porcupine
porcupine = pvporcupine.create(
    access_key=porcupine_access_key,
    keywords=["picovoice", "bumblebee"]
)

# Initialize the OpenAI client
client = OpenAI(api_key=openai_api_key, default_headers={"OpenAI-Beta": "assistants=v2"})

def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=2000, timeout=5):
    """
    Record audio from the default microphone until silence is detected,
    with a timeout period to allow capturing additional audio.
    """
    print("Recording... Press Ctrl+C to stop.")
    audio_file = []

    start_time = time.time()  # Record the start time
    try:
        while True:
            recording = sd.rec(int(chunk_duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
            sd.wait()
            audio_file.append(recording)

            # Check if the last recorded chunk is silent
            if is_silent(recording, silence_threshold):
                # Check if timeout period has elapsed
                if time.time() - start_time > timeout:
                    print("Timeout reached, stopping recording.")
                    break
                else:
                    print("Silence detected, waiting for more audio...")

    except KeyboardInterrupt:
        print("Recording stopped manually.")

    if audio_file:
        audio_file = np.concatenate(audio_file, axis=0)
        return audio_file
    else:
        raise ValueError("No audio file recorded.")

def is_silent(file, threshold=500):
    """
    Returns True if the audio file is below the silent threshold.
    """
    return np.abs(file).mean() < threshold

recorder = PvRecorder(frame_length=porcupine.frame_length)
recorder.start()

try:
    while True:
        pcm = recorder.read()
        keyword_index = porcupine.process(pcm)

        if keyword_index == 0:
            print("Detected 'picovoice'")
        elif keyword_index == 1:
            print("Detected 'bumblebee'")

            # Record audio from the microphone with extended silence detection
            audio_file = record_audio(timeout=5)  # Adjust timeout 

            # Convert audio to text using OpenAI API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                tmpfilename = tmpfile.name
                wavio.write(tmpfilename, audio_file, 44100, sampwidth=2)

            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(tmpfilename, "rb"),
            )

            print("Transcription:", transcription.text)

            # Start a new thread for handling the interaction
            interaction_thread = threading.Thread(target=handle_interaction, args=(transcription.text,))
            interaction_thread.start()

except KeyboardInterrupt:
    print("Script interrupted.")
finally:
    if porcupine is not None:
        porcupine.delete()
    recorder.stop()
    recorder.delete()