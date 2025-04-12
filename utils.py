import time
import openai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# OpenAI client setup
client = openai.OpenAI()
model = "gpt-3.5-turbo"

def get_assistant_response(thread_id, assistant_id, user_message):
    """Get response from assistant"""
    # Add user message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Create run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    # Wait for completion
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            return messages.data[0].content[0].text.value
        elif run_status.status in ["failed", "cancelled"]:
            return "Desculpe, ocorreu um erro."
        time.sleep(0.5) 