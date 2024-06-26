from openai import OpenAI
from dotenv import load_dotenv
import sounddevice as sd
import struct
import pyaudio
import numpy as np
import tempfile
import pvporcupine
import wavio
import wave
import os
import time
from pvrecorder import PvRecorder


load_dotenv()
# Retrieve the OpenAI API key and Porcupine access key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")

sd.default.device = 'seeed-2mic-voicecard'

if not openai_api_key:
    raise ValueError("OpenAI API key is not set in environment variables.")
if not porcupine_access_key:
    raise ValueError("Porcupine access key is not set in environment variables.")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key, default_headers={"OpenAI-Beta": "assistants=v2"})

# Initialize Porcupine
porcupine = pvporcupine.create(
    access_key=porcupine_access_key,
    keywords=["picovoice", "bumblebee"]
)

# paud = pyaudio.PyAudio()
# audio_frame = paud.open(rate=porcupine.sample_rate, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)

def get_next_audio_frame():
    """
    Record a chunk of audio from the microphone.
    """
    

    
    # return sd.rec(int(porcupine.frame_length), samplerate=porcupine.sample_rate, channels=1, dtype='int16')

def query_and_record(prompt, mp3_filename):
    """
    Send a prompt to the OpenAI assistant and record the response as an MP3 file.
    """
    # Create an assistant instance
    assistant = client.beta.assistants.create(
        name="Senior Tech Help",
        instructions="You are a helpful tech teacher specifically for seniors. You will help older adults (ages 50+) with quick questions about smartphones, voice assistants, computers, cameras, the internet, digital shopping, or any other technology-related topic. You will always ask for specifics, like what device or phone they are using, and provide them with step-by-step instructions for their response.",
        model="gpt-4o"
    )
    
    # Create a thread for communication
    thread = client.beta.threads.create()
    
    # Send user's prompt to the AI
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )
    
    # Start the AI to process the user prompt
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
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

        # Extract the text from the response
        text_response = message_list.data[-1].content

        # Generate an audio response from the text
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice="echo",
            input=text_response,
        )

        response.stream_to_file(mp3_filename)

        print("Response recorded to " + mp3_filename)

def is_silent(file, threshold=500):
    """
    Returns 'True' if below the 'silent' threshold.
    """
    return np.abs(file).mean() < threshold

def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=500, min_chunks=5):
    """
    Record audio from the microphone until silence is detected.
    """
    print("Recording... Press Ctrl+C to stop.")
    audio_file = []

    try:
        while True:
            recording = sd.rec(int(chunk_duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
            sd.wait()
            audio_file.append(recording)
            # Ensure minimum recording length before checking for silence
            if len(audio_file) >= min_chunks and is_silent(recording, threshold=silence_threshold):
                print("Silence detected, stopping recording.")
                break
    except KeyboardInterrupt:
        print("Recording stopped manually.")

    # Concatenate all recorded chunks
    if audio_file:
        audio_file = np.concatenate(audio_file, axis=0)
        return audio_file
    else:
        raise ValueError("No audio file recorded.")

# Main loop for keyword detection and interaction
recorder = PvRecorder(
    frame_length=porcupine.frame_length,
    device_index=3
)
recorder.start()
wav_file = None
wav_file = wave.open("./test.wav", "w")
wav_file.setnchannels(1)
wav_file.setsampwidth(2)
wav_file.setframerate(16000)
print('Listening ... ')

try:
    while True:
        # keyword = audio_frame.read(porcupine.frame_length)
        # keyword = struct.unpack_from ("h" * porcupine.frame_length, keyword)
        # keyword_index= porcupine.process(keyword)

        

        

        pcm = recorder.read()
        keyword_index = porcupine.process(pcm)

        if wav_file is not None:
            wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))

        print(keyword_index)
        if keyword_index == 0:
            print("Detected 'picovoice'")
        elif keyword_index == 1:
            recorder.delete()
            print("Detected 'bumblebee'")

            # Record audio from the microphone
            audio_file = record_audio()

            # Convert audio to text using OpenAI API
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                tmpfilename = tmpfile.name
                wavio.write(tmpfilename, audio_file, 44100, sampwidth=2)

            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(tmpfilename, "rb"),
            )

            print("Transcription:", transcription.text)

            # Example usage
            prompt = transcription.text
            mp3_filename = "response.mp3"
            query_and_record(prompt, mp3_filename)

finally:
# Ensuring proper release of resources
    recorder.delete()
    porcupine.delete()
    if wav_file is not None:
        wav_file.close()
