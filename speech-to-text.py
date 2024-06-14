from openai import OpenAI
import sounddevice as sd
import numpy as np
import tempfile
import wavio 

def is_silent(file, threshold=500):
    """Returns 'True' if below the 'silent' threshold"""
    return np.abs(file).mean() < threshold

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
