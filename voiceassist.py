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

load_dotenv()

# Retrieve the OpenAI API key and Porcupine access key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")

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


def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=1000, silence_duration=10):
    """
    Record audio in real-time and stop when silence is detected for the specified duration.
    """
    print("Recording... Press Ctrl+C to stop.")
    audio_file = []
    silence_start_time = None
    chunk_size = int(chunk_duration * samplerate)
    
    try:
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16', callback=lambda indata, frames, time, status: audio_file.append(indata.copy())):
            while True:
                if len(audio_file) > 0:
                    last_chunk = audio_file[-1]
                    
                    # Check if the last chunk is silent
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


# Define frame length and sample rate
frame_length = porcupine.frame_length
sample_rate = porcupine.sample_rate

def is_silent(chunk, threshold=1000):
    """
    Returns True if the audio chunk is below the silent threshold.
    """
    # Calculate the RMS value of the audio chunk
    rms = np.sqrt(np.mean(np.square(chunk)))
    return rms < threshold

def detect_wake_word():
    """
    Detect wake words using Porcupine.
    """
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            while True:
                pcm = stream.read(frame_length)[0]
                pcm = np.frombuffer(pcm, dtype=np.int16)
                keyword_index = porcupine.process(pcm)

                if keyword_index == 0:
                    print("Detected 'picovoice'")
                    return 'picovoice'
                elif keyword_index == 1:
                    print("Detected 'bumblebee'")
                    return 'bumblebee'

    except KeyboardInterrupt:
        print("Script interrupted.")

try:
    while True:
        wake_word = detect_wake_word()

        if wake_word == 'bumblebee':
            # Record audio from the microphone with real-time silence detection
            audio_file = record_audio(silence_duration=5)

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
