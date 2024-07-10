from dotenv import load_dotenv
import sounddevice as sd
import struct
import numpy as np
import tempfile
import pvporcupine
import wave
import os
import time
from pvrecorder import PvRecorder
import wavio
from openai import OpenAI

load_dotenv()

# Retrieve the OpenAI API key and Porcupine access key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY")
assistant_api_key = os.getenv("ASSISTANT_API_KEY")

sd.default.device = None #'seeed-2mic-voicecard'
 
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

def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=500):
    """
    Record audio from the default microphone until silence is detected.
    """
    print("Recording... Press Ctrl+C to stop.")
    audio_file = []

    try:
        while True:
            recording = sd.rec(int(chunk_duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
            sd.wait()
            audio_file.append(recording)

            # Check if the last recorded chunk is silent
            if is_silent(recording, silence_threshold):
                print("Silence detected, stopping recording.")
                break

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

def query_and_record(prompt, mp3_filename):
    """
    Send a prompt to the OpenAI assistant and record the response as an MP3 file.
    """
    # # Create an assistant instance
    # assistant = client.beta.assistants.create(
    #     name="Senior Tech Help",
    #     instructions="You are a helpful tech teacher specifically for seniors. You will help older adults (ages 50+) with quick questions about smartphones, voice assistants, computers, cameras, the internet, digital shopping, or any other technology-related topic. You will always ask for specifics, like what device or phone they are using, and provide them with step-by-step instructions for their response.",
    #     model="gpt-4o"
    # )
    assistant_id = assistant_api_key

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

        # Extract the text content from the response
        # text_response = ""
        # for message in message_list.data:
        #     if message.role == "assistant" and message.content:
        #         text_response += message.content + "\n"

        text_response = message_list.data[0].content[0].text.value

        # Generate an audio response from the text
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice="echo",
            input=text_response,
        )

        response.stream_to_file(mp3_filename)

        print("Response recorded to " + mp3_filename)


# Main loop for keyword detection and interaction
recorder = PvRecorder(frame_length=porcupine.frame_length)
recorder.start()
wav_file = None

try:
    while True:
        pcm = recorder.read()
        keyword_index = porcupine.process(pcm)

        if keyword_index == 0:
            print("Detected 'picovoice'")
        elif keyword_index == 1:
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

except KeyboardInterrupt:
    print("Script interrupted.")
finally:
# Ensuring proper release of resources
    if porcupine is not None:
        porcupine.delete()
    # if audio_frame is not None:
    #     audio_frame.close()
    # if paud is not None:
    #     paud.terminate()
