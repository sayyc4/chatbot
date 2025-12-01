# helper.py
# Backend logic for the ImagineThat Architecture Assistant.
# All heavy logic (LLM, image generation, TTS) lives here.
# The Streamlit UI calls these functions from app.py.
# set OPENAI_API_KEY="import openai

import io
import urllib.request
from typing import List, Dict
from openai import OpenAI
from gtts import gTTS
import base64

# Create a single OpenAI client instance.
client = OpenAI()


def build_ideas_prompt(topic: str) -> str:
    """Build the prompt string for the chat model.

    This prompt follows the same structure as the original Colab notebook:
    - Ask for 3 ideas.
    - Force the format "1. Title: Description".
    - Use exactly one blank line between ideas.
    """
    message = f"""
Give me a list of 5 ideas for the future of {topic} in the context of convention centers.
Each idea must be formatted as:
<number>. <Title>: <Description>

Rules:
- Always include a colon ":" between the idea title and its description.
- Use exactly one blank line between ideas.
- Do not include bullet points or parentheses.
- Example format:

1. Smart Roofs: Solar panels that change color to adjust heat absorption.

2. Floating Stages: Modular stages that hover above crowds.

Return only the list, nothing else.
"""
    # Strip leading/trailing whitespace to keep the prompt clean.
    return message.strip()


def call_chat_for_ideas(topic: str) -> str:
    """Call the chat completion model and return the raw reply text.

    This function reproduces the behavior of the original code that used
    client.chat.completions.create with model "gpt-3.5-turbo".
    """
    prompt = build_ideas_prompt(topic)

    messages = [
        {"role": "system", "content": "You are an intelligent assistant."},
        {"role": "user", "content": prompt},
    ]

    chat = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages,
    )

    reply = chat.choices[0].message.content
    return reply


def parse_ideas_reply(reply: str) -> List[Dict[str, str]]:
    """Parse the raw reply text into a list of ideas.

    Expected format per idea (separated by a blank line):
        "1. Title: Description"

    Returns:
        List of dicts: [{"idea": title, "description": description}, ...]
    """
    items = reply.strip().split("\n\n")

    ideas: List[Dict[str, str]] = []

    for item in items:
        # Clean up whitespace and skip empty lines.
        line = item.strip()
        if not line:
            continue

        try:
            # Find the index of ". " that separates the number and the title.
            dot_index = line.index(". ")
            # Find the index of ": " that separates the title and description.
            colon_index = line.index(": ", dot_index + 2)

            title = line[dot_index + 2 : colon_index].strip()
            description = line[colon_index + 2 :].strip()

            if title and description:
                ideas.append(
                    {
                        "idea": title,
                        "description": description,
                    }
                )
        except ValueError:
            # If the format is not exactly as expected, skip this item.
            # In a production app, you may want to log this case.
            continue

    return ideas


def generate_image_bytes(prompt: str) -> bytes:
    """Generate an image via gpt-image-1-mini and return it as raw bytes.

    This function matches the minimal working example from test_image.py.
    """
    response = client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )

    # gpt-image-1-mini returns base64, not a URL
    b64 = response.data[0].b64_json
    image_bytes = base64.b64decode(b64)
    return image_bytes


def generate_audio_bytes(text: str) -> bytes:
    """Generate an mp3 audio file from text and return it as raw bytes.

    This function uses gTTS and writes to an in-memory buffer instead of
    saving to disk, which works well with Streamlit's st.audio.
    """
    tts = gTTS(text)
    buffer = io.BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer.read()

def generate_intro_audio(topic: str) -> bytes:
    """Generate an intro audio clip similar to the original notebook.

    The intro explains that the bot is thinking about the user's topic.
    """
    text = (
        "Beep Boop. Hello. I am a bot made for ImagineThat. "
        f"You are interested in the future of {topic}. Beep Boop."
    )
    try:
        return generate_audio_bytes(text)
    except Exception:
        return None


def generate_ideas_with_media(topic: str, num_ideas: int = 1) -> List[Dict[str, object]]:
    """High-level pipeline that returns ideas with images and audio.

    This function:
    1. Calls the chat model to get future ideas.
    2. Parses the result into idea + description pairs.
    3. Keeps only `num_ideas` items (for testing you can set num_ideas=1).
    4. For each idea:
       - Generates an image with gpt-image-1-mini.
       - Generates an audio clip with gTTS.

    Args:
        topic: The user-provided topic string.
        num_ideas: How many ideas to keep and process.

    Returns:
        List of dicts, each with:
        {
            "idea": str,
            "description": str,
            "image": bytes or None,
            "audio": bytes or None,
        }
    """
    # Step 1: ask the chat model for ideas (raw text reply).
    raw_reply = call_chat_for_ideas(topic)

    # Step 2: parse the reply into structured ideas.
    structured_ideas = parse_ideas_reply(raw_reply)

    # Only keep the first `num_ideas` items (for testing: num_ideas=1).
    structured_ideas = structured_ideas[:num_ideas]

    results: List[Dict[str, object]] = []

    # Step 3: for each idea, generate image and audio.
    for item in structured_ideas:
        idea = item["idea"]
        description = item["description"]

        # Combined text used for image and voice text.
        text_string = f"{idea}: {description}"

        # Generate image bytes (this may raise if something is wrong).
        image_bytes = generate_image_bytes(text_string)

        # Generate audio bytes with a "Beep Boop" style intro.
        voice_text = (
            "Beep Boop. Beep Boop. Here is an idea. Consider "
            + text_string
        )
        audio_bytes = generate_audio_bytes(voice_text)

        results.append(
            {
                "idea": idea,
                "description": description,
                "image": image_bytes,
                "audio": audio_bytes,
            }
        )

    return results

