from openai import OpenAI
import sounddevice as sd
import numpy as np
import tempfile
import wavio
import os
import time

#initialize OpenAi
client = OpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})

#function to query OpenAI assisatnat and record response to mp3
def query_and_record(prompt, mp3_filename):
    # Retrieve the OpenAI API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is not set in environment variables.")

    #creating an assistant instance
    assistant = client.beta.assistants.create(
        name="Senior Tech Help",
        instructions="You are a helpful tech teach specifically for seniors. You will help older adults (ages 50+) with quick questions about smartphones, voice assistants, computers, cameras, the internet, digital shopping, or any other technology related topic. You will always ask for specifics, like what device or phone they are using, and provide them with step by step instructions for their response.",
        model="gpt-4o",
    )
    
    #create a thread for communication
    thread = client.beta.threads.create()

    #send users prompt to the ai
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )
    #start the ai to process the user prompt
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="Please address the user as Jane Doe. The user has a premium account."
    )
    #wait until ai is complete with processing
    while run.status == "in_progress" or run.status == "queued":
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
    text_response = message_list.data[0].content[0].text.value

    #generate an audio response from the text
    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="echo",
        input=text_response,
    )

    response.stream_to_file(mp3_filename)

    return print("Response recorded to " + mp3_filename)

#function to check if audio is silent and if recording should be stopped
def is_silent(file, threshold=500):
    """Returns 'True' if below the 'silent' threshold"""
    return np.abs(file).mean() < threshold

#function recording audio
def record_audio(samplerate=44100, chunk_duration=1, silence_threshold=500, min_chunks=5):
    """
    Record audio from the microphone until silence is detected .
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

# Record audio from the microphone
audio_file = record_audio()

# Convert audio to text using SpeechRecognition
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
    tmpfilename = tmpfile.name
    wavio.write(tmpfilename, audio_file, 44100, sampwidth=2)

# Transcribe audio using OpenAI API
client = OpenAI()
transcription = client.audio.transcriptions.create(
    model="whisper-1",
    file=open(tmpfilename, "rb"),
)

print("Transcription:", transcription.text)

# Example usage
prompt = transcription.text
mp3_filename = "response.mp3"
query_and_record(prompt, mp3_filename)
