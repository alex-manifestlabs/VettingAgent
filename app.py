import streamlit as st
import os
# from dotenv import load_dotenv # No longer loading from .env
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
            # Add basic cleaning for potential markdown code block fences
            if json_str.startswith("```json"): json_str = json_str[7:]
            if json_str.endswith("```"): json_str = json_str[:-3]
            json_str = json_str.strip()

            updated_data_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from agent: {e}\nJSON string trying to decode:\n{json_str}")
            # Keep convo_response, but data is None
        except Exception as e:
            print(f"Unexpected error parsing agent data: {e}")

    return convo_response, updated_data_dict

# --- Page Config ---
st.set_page_config(page_title="EB1-A Info Gatherer", layout="wide")

# --- Title and Disclaimer ---
st.title("🤖 EB1-A Preliminary Information Gatherer")
st.warning("**Disclaimer:** This is an AI assistant designed solely to help collect initial information potentially relevant to an EB1-A visa application based on user input. It does **NOT** provide legal advice, assess eligibility, or guarantee accuracy. Information gathered here requires review by a qualified professional. Always consult an immigration attorney for legal advice.")

# --- Session State Initialization ---
# Initialize required keys if they don't exist
if "openai_api_key" not in st.session_state: st.session_state.openai_api_key = None
if "agent_chain" not in st.session_state: st.session_state.agent_chain = None
if "messages" not in st.session_state: st.session_state.messages = []
if "collected_data" not in st.session_state: st.session_state.collected_data = EB1AData().dict()
if "pdf_processed" not in st.session_state: st.session_state.pdf_processed = False
if "linkedin_processed" not in st.session_state: st.session_state.linkedin_processed = False

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    # Get API Key input
    entered_api_key = st.text_input(
        "Enter your OpenAI API Key",
        type="password",
        key="api_key_input", # Use a key to access widget value
        help="Your key is required to run the agent. It is not stored after your session ends."
    )

    # Store the key in session state when entered
    if entered_api_key:
        st.session_state.openai_api_key = entered_api_key
        st.success("API Key entered.", icon="🔑")

    # --- Document Uploads (only if key is present) ---
    if st.session_state.openai_api_key:
        st.divider()
        st.header("Upload Documents")
        uploaded_file = st.file_uploader("Upload Resume/CV (PDF Only)", type=["pdf"])

        st.header("LinkedIn Profile")
        linkedin_url = st.text_input("Enter LinkedIn Profile URL (Optional)")
        submit_linkedin = st.button("Submit LinkedIn URL")

    st.divider()

    st.header("Collected Information Status")
    # Display the collected data dictionary as JSON
    if st.session_state.openai_api_key:
        st.json(st.session_state.collected_data, expanded=True)
    else:
        st.info("Data structure will appear here once API key is entered.")

# --- Main Content Area --- #

# Only proceed if API key is provided
if not st.session_state.openai_api_key:
    st.info("👈 Please enter your OpenAI API Key in the sidebar to start the agent.")
    st.stop() # Stop execution if no key

# --- Initialize Agent Chain (only once after key is provided) --- #
if st.session_state.openai_api_key and st.session_state.agent_chain is None:
    try:
        st.session_state.agent_chain = get_visa_agent_chain(st.session_state.openai_api_key)
        print("Agent chain initialized successfully.")
    except Exception as e:
        st.error(f"Failed to initialize agent chain: {e}")
        st.stop()

# Check if agent chain is initialized before proceeding
if st.session_state.agent_chain is None:
    st.error("Agent chain could not be initialized. Please check your API key and refresh.")
    st.stop()

# --- Handle PDF Upload (if agent is initialized) ---
if uploaded_file is not None and not st.session_state.pdf_processed:
    with st.spinner("Processing PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_file)
        if extracted_text:
            pdf_context_message = f"(System note: The user has uploaded a PDF named '{uploaded_file.name}'. Its extracted text content begins: \n\n{extracted_text[:1500]} ... [truncated])"
            st.chat_message("system").markdown(f"✅ PDF '{uploaded_file.name}' processed. The agent will consider its content.")
            st.session_state.pending_pdf_context = pdf_context_message
            st.session_state.pdf_processed = True
            st.session_state.collected_data['supporting_documents']["resume_file"] = uploaded_file.name
            st.rerun()
        else:
            st.error("Could not extract text from the uploaded PDF.")
            st.session_state.pdf_processed = True # Mark as processed even if failed

# --- Handle LinkedIn URL (if agent is initialized) ---
if submit_linkedin and linkedin_url and not st.session_state.linkedin_processed:
    with st.spinner("Processing LinkedIn URL..."):
        parse_linkedin_profile(linkedin_url)
        linkedin_context_message = f"(System note: User provided LinkedIn URL: {linkedin_url}. You cannot access external URLs, but acknowledge receipt and ask the user to highlight relevant info from it if needed.)"
        st.chat_message("system").markdown(f"✅ LinkedIn URL received: {linkedin_url}. The agent will acknowledge it.")
        st.session_state.pending_linkedin_context = linkedin_context_message
        st.session_state.linkedin_processed = True
        st.session_state.collected_data['supporting_documents']["linkedin_url"] = linkedin_url
        st.rerun()

# --- Agent Initiation (if agent is initialized and no messages yet) ---
if st.session_state.agent_chain and not st.session_state.messages:
    st.chat_message("system").markdown("Initiating conversation with agent...")
    try:
        initial_input = "Hello, please start the conversation by introducing yourself and asking the first question based on your instructions."
        with st.spinner("Agent is starting..."):
            raw_response = st.session_state.agent_chain.predict(input=initial_input)

        convo_response, updated_data = parse_agent_response(raw_response)
        st.session_state.messages.append({"role": "assistant", "content": convo_response})
        if updated_data:
            st.session_state.collected_data = updated_data
        st.rerun()
    except Exception as e:
        st.error(f"Error initiating conversation: {e}")
        st.stop()

# --- Display Existing Chat Messages ---
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# --- Handle New User Input --- #
if prompt := st.chat_input("Your response:"):
    if not st.session_state.agent_chain:
        st.warning("Please ensure the API key is entered and the agent is initialized.")
    else:
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Construct input for the agent
        agent_input = prompt
        if st.session_state.get("pending_pdf_context"):
            agent_input = st.session_state.pop("pending_pdf_context") + "\n\nUser's message: " + agent_input
        if st.session_state.get("pending_linkedin_context"):
            agent_input = st.session_state.pop("pending_linkedin_context") + "\n\nUser's message: " + agent_input

        # Get agent response
        with st.spinner("Assistant is thinking..."):
            try:
                raw_response = st.session_state.agent_chain.predict(input=agent_input)
                convo_response, updated_data = parse_agent_response(raw_response)

                st.chat_message("assistant").markdown(convo_response)
                st.session_state.messages.append({"role": "assistant", "content": convo_response})

                if updated_data:
                    st.session_state.collected_data = updated_data
                    st.rerun()
                else:
                    print("Agent response did not contain valid <updated_data> JSON.")

            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.session_state.messages.append({"role": "system", "content": f"Error: {e}"}) 