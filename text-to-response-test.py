from openai import OpenAI
import io
import os
import time

client = OpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})


def query_and_record(prompt, mp3_filename):
    # Retrieve the OpenAI API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is not set in environment variables.")


    assistant = client.beta.assistants.create(
        name="Senior Tech Help",
        instructions="You are a helpful tech teach specifically for seniors. You will help older adults (ages 50+) with quick questions about smartphones, voice assistants, computers, cameras, the internet, digital shopping, or any other technology related topic. You will always ask for specifics, like what device or phone they are using, and provide them with step by step instructions for their response.",
        model="gpt-4-turbo",
    )
    

    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="Please address the user as Jane Doe. The user has a premium account."
    )
    
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

    #print(text_response)

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice="echo",
        input=text_response,
    )

    response.stream_to_file(mp3_filename)

    return print("Response recorded to " + mp3_filename)

# Example usage
prompt = input("Enter your tech question for Helper Bee:")
mp3_filename = "response.mp3"
query_and_record(prompt, mp3_filename)
