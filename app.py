import streamlit as st
import os
from dotenv import load_dotenv
import json
import re # Import regex for parsing
from typing import Optional

# Ensure utils and agents are importable
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the chain function and the Pydantic model
from agents.visa_agent import get_visa_agent_chain, EB1AData
from utils.pdf_utils import extract_text_from_pdf
from utils.linkedin_utils import parse_linkedin_profile

# --- Function to Parse Agent Response --- #
def parse_agent_response(response_text: str) -> tuple[str, Optional[dict]]:
    """Parses the agent's response to extract conversational part and updated data.

    Args:
        response_text: The raw string response from the agent.

    Returns:
        A tuple containing: (conversational_response, updated_data_dict)
        updated_data_dict is None if parsing fails or tag is missing.
    """
    convo_match = re.search(r"<conversation_response>(.*?)</conversation_response>", response_text, re.DOTALL)
    data_match = re.search(r"<updated_data>(.*?)</updated_data>", response_text, re.DOTALL)

    convo_response = convo_match.group(1).strip() if convo_match else response_text # Fallback
    updated_data_dict = None

    if data_match:
        json_str = data_match.group(1).strip()
        try:
            updated_data_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from agent: {e}\nJSON string: {json_str}")
            # Keep convo_response, but data is None

    return convo_response, updated_data_dict

# --- Page Config ---
st.set_page_config(page_title="EB1-A Info Gatherer", layout="wide")

# --- Load API Key ---
load_dotenv()
if not os.getenv("OPENAI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    st.error("⚠️ OpenAI API Key not found. Please set it in your .env file or environment variables.")
    st.stop()

# --- Title and Disclaimer ---
st.title("🤖 EB1-A Preliminary Information Gatherer")
st.warning("**Disclaimer:** This is an AI assistant to help collect initial information potentially relevant to an EB1-A visa. It does **NOT** provide legal advice. Information gathered here is for preliminary review purposes only. Always consult a qualified immigration attorney for legal advice.")

# --- Session State Initialization ---
if "agent_chain" not in st.session_state:
    st.session_state.agent_chain = get_visa_agent_chain()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize collected_data using the Pydantic model for structure
if "collected_data" not in st.session_state:
    # Create an instance of the model with default values and convert to dict
    st.session_state.collected_data = EB1AData().dict()

if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False

if "linkedin_processed" not in st.session_state:
    st.session_state.linkedin_processed = False

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Documents")
    uploaded_file = st.file_uploader("Upload Resume/CV (PDF Only)", type=["pdf"])

    st.header("LinkedIn Profile")
    linkedin_url = st.text_input("Enter LinkedIn Profile URL (Optional)")
    submit_linkedin = st.button("Submit LinkedIn URL")

    st.divider() # Add a visual separator

    st.header("Collected Information Status")
    # Display the collected data dictionary as JSON
    st.json(st.session_state.collected_data, expanded=True) # Start expanded

# --- Handle PDF Upload ---
if uploaded_file is not None and not st.session_state.pdf_processed:
    with st.spinner("Processing PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_file)
        if extracted_text:
            pdf_context_message = f"(System note: The user has uploaded a PDF named '{uploaded_file.name}'. Its extracted text content begins: \n\n{extracted_text[:1500]} ... [truncated])"
            st.chat_message("system").markdown(f"✅ PDF '{uploaded_file.name}' processed. The agent will consider its content.")
            st.session_state.pending_pdf_context = pdf_context_message
            st.session_state.pdf_processed = True
            # Update collected_data state directly - Agent will incorporate later
            st.session_state.collected_data['supporting_documents']["resume_file"] = uploaded_file.name
            st.rerun()
        else:
            st.error("Could not extract text from the uploaded PDF.")
            st.session_state.pdf_processed = True # Mark as processed even if failed

# --- Handle LinkedIn URL ---
if submit_linkedin and linkedin_url and not st.session_state.linkedin_processed:
    with st.spinner("Processing LinkedIn URL..."):
        parse_linkedin_profile(linkedin_url) # Placeholder function
        linkedin_context_message = f"(System note: User provided LinkedIn URL: {linkedin_url}. You cannot access external URLs, but acknowledge receipt and ask the user to highlight relevant info from it if needed.)"
        st.chat_message("system").markdown(f"✅ LinkedIn URL received: {linkedin_url}. The agent will acknowledge it.")
        st.session_state.pending_linkedin_context = linkedin_context_message
        st.session_state.linkedin_processed = True
        # Update collected_data state directly - Agent will incorporate later
        st.session_state.collected_data['supporting_documents']["linkedin_url"] = linkedin_url
        st.rerun()

# --- Agent Initiation ---
if not st.session_state.messages:
    st.chat_message("system").markdown("Initiating conversation with agent...")
    try:
        initial_input = "Hello, please start the conversation by introducing yourself and asking the first question based on your instructions."
        with st.spinner("Agent is starting..."):
            raw_response = st.session_state.agent_chain.predict(input=initial_input)

        # Parse the initial response
        convo_response, updated_data = parse_agent_response(raw_response)

        # Add agent's first conversational message to state
        st.session_state.messages.append({"role": "assistant", "content": convo_response})

        # Update collected data if provided in the initial response
        if updated_data:
            st.session_state.collected_data = updated_data

        st.rerun()
    except Exception as e:
        st.error(f"Error initiating conversation: {e}")
        st.stop()

# --- Display Existing Chat Messages ---
# Skip the initial system message if it exists from parsing errors
for message in st.session_state.messages:
    if message["role"] != "system": # Avoid displaying parsing error messages if any
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Handle New User Input ---
if prompt := st.chat_input("Your response:"):
    # Display user message
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Construct input for the agent, including any pending context
    agent_input = prompt
    if st.session_state.get("pending_pdf_context"):
        agent_input = st.session_state.pop("pending_pdf_context") + "\n\nUser's message: " + agent_input
    if st.session_state.get("pending_linkedin_context"):
        agent_input = st.session_state.pop("pending_linkedin_context") + "\n\nUser's message: " + agent_input

    # Get agent response
    with st.spinner("Assistant is thinking..."):
        try:
            raw_response = st.session_state.agent_chain.predict(input=agent_input)

            # Parse the response
            convo_response, updated_data = parse_agent_response(raw_response)

            # Display assistant's conversational response
            st.chat_message("assistant").markdown(convo_response)
            st.session_state.messages.append({"role": "assistant", "content": convo_response})

            # Update collected data state if valid data was received
            if updated_data:
                st.session_state.collected_data = updated_data
                st.rerun() # Rerun to update sidebar immediately
            else:
                # If parsing failed or no data tag, add a note for debugging? Maybe not needed.
                print("Agent response did not contain valid <updated_data> JSON.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            # Log error but try to continue if possible
            st.session_state.messages.append({"role": "system", "content": f"Error: {e}"}) 