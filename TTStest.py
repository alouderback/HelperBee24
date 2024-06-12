from openai import OpenAI

client = OpenAI()

response = client.audio.speech.create(
    model="tts-1-hd",
    voice="echo",
    input="Test Audio",
)

response.stream_to_file("output.mp3")