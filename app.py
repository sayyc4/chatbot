# app.py
# Streamlit UI for an architecture-themed assistant.
# This file only defines the page layout and basic chat flow.
# streamlit run app.py



import datetime
import time
import textwrap

import streamlit as st
from helper import *


# -----------------------------------------------------------------------------
# Page configuration.

st.set_page_config(
    page_title="ImagineThat Architecture Assistant",
    page_icon="🏟",
    layout="centered",
)

# -----------------------------------------------------------------------------
# Constants for the UI.

INSTRUCTIONS = textwrap.dedent(
    """
    You are an assistant that helps users imagine the future of architecture.
    """
)

# Architecture-themed suggestion buttons.
SUGGESTIONS = {
    "🏛️ Convention Center": ("Convention Center"),
    "🏟️ Arena": ( "Arena"),
    "🏞 Urban Park": ("Urban Park"),
}

# Minimum time between two assistant responses (simple rate limiting).
MIN_TIME_BETWEEN_REQUESTS = datetime.timedelta(seconds=2)


# -----------------------------------------------------------------------------
# Helper functions for session state and layout.

def init_session_state() -> None:
    """Initialize session state variables if they are missing."""
    if "messages" not in st.session_state:
        # Each message is a dict with keys: "role" and "content".
        st.session_state.messages = []

    if "initial_question" not in st.session_state:
        st.session_state.initial_question = None

    if "selected_suggestion" not in st.session_state:
        st.session_state.selected_suggestion = None

    if "prev_question_timestamp" not in st.session_state:
        # Use an old timestamp so the first question is never rate-limited.
        st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)


def clear_conversation() -> None:
    """Clear chat history and initial inputs."""
    st.session_state.messages = []
    st.session_state.initial_question = None
    st.session_state.selected_suggestion = None


def show_header() -> None:
    """Draw the page header with an architecture-themed icon."""
    # Decorative symbol at the top.
    st.markdown(
        "<div style='font-size: 3rem; line-height: 1; text-align: center;'>🏟</div>",
        unsafe_allow_html=True,
    )

    # Title row with restart button.
    title_row = st.container()
    with title_row:
        st.title("ImagineThat Architecture Assistant", anchor=False)
        # Small subtitle as helper text.
        st.caption(
            "Ask about the future of what you are curious about."
        )

    # Restart button aligned to the right.
    cols = st.columns([1, 1, 1, 1])
    with cols[-1]:
        st.button("Restart", on_click=clear_conversation)


def show_initial_view() -> None:
    """Show the initial view before any question is asked.

    This view displays:
    - A chat input for the first question.
    - A row of example question pills.
    """
    st.session_state.messages = []

    with st.container():
        # First question input.
        st.chat_input(
            "Ask about the future of a building or space...",
            key="initial_question",
        )

        # Example questions as pills.
        selected = st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=list(SUGGESTIONS.keys()),
            key="selected_suggestion",
        )

    # Stop execution after drawing the initial UI.
    st.stop()


def add_message(role: str, content: str) -> None:
    """Append a new message to the chat history."""
    st.session_state.messages.append(
        {"role": role, "content": content}
    )


def draw_chat_history() -> None:
    """Render all previous messages as chat bubbles."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# -----------------------------------------------------------------------------
# Main app.

def main() -> None:
    """Main entry point for the Streamlit application."""
    init_session_state()
    show_header()

    # Check interaction flags.
    user_just_asked_initial_question = (
        "initial_question" in st.session_state
        and st.session_state.initial_question
    )
    user_just_clicked_suggestion = (
        "selected_suggestion" in st.session_state
        and st.session_state.selected_suggestion
    )
    user_first_interaction = (
        user_just_asked_initial_question or user_just_clicked_suggestion
    )
    has_message_history = (
        "messages" in st.session_state
        and len(st.session_state.messages) > 0
    )

    # If there is no history and no interaction yet, show the initial view.
    if not user_first_interaction and not has_message_history:
        show_initial_view()

    # Decide what the new user message should be.
    user_message = st.chat_input("Ask a follow-up about architecture...")

    if not user_message:
        # Use initial question if present.
        if user_just_asked_initial_question:
            user_message = st.session_state.initial_question

        # Or use selected suggestion if present.
        if user_just_clicked_suggestion:
            label = st.session_state.selected_suggestion
            if label in SUGGESTIONS:
                user_message = SUGGESTIONS[label]

    # Draw existing chat history first.
    draw_chat_history()

    if user_message:
        # Escape dollar signs to avoid accidental LaTeX in Markdown.
        user_message = user_message.replace("$", r"\$")

        # Display user message bubble.
        with st.chat_message("user"):
            st.markdown(user_message)

        # Rate limiting based on the last question time.
        now = datetime.datetime.now()
        time_diff = now - st.session_state.prev_question_timestamp
        st.session_state.prev_question_timestamp = now

        if time_diff < MIN_TIME_BETWEEN_REQUESTS:
            time.sleep(time_diff.total_seconds())

        # Assistant response block.
        with st.chat_message("assistant"):
            with st.spinner("Thinking about future buildings..."):
                # Optional: play an intro audio before listing ideas.
                # This uses a helper function from helper.py.
                intro_audio = generate_intro_audio(user_message)
                if intro_audio is not None:
                    st.audio(intro_audio, format="audio/mp3")

                # Call the main pipeline to get ideas with images and audio.
                ideas = generate_ideas_with_media(user_message)

                # Render each idea as a small "card".
                for item in ideas:
                    st.subheader(item["idea"])
                    st.write(item["description"])

                    # Show generated image if available.
                    if item.get("image") is not None:
                        st.image(item["image"])

                    # Play generated audio if available.
                    if item.get("audio") is not None:
                        st.audio(item["audio"], format="audio/mp3")

                # Build a plain-text summary for the chat history.
                history_text = "\n\n".join(
                    f"{idx + 1}. {item['idea']}: {item['description']}"
                    for idx, item in enumerate(ideas)
                )

        # Update history after both messages are shown.
        add_message("user", user_message)
        add_message("assistant", history_text)



if __name__ == "__main__":
    main()
