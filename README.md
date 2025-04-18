# EB1-A AI Vetter Agent

This Streamlit application uses a LangChain agent to interactively gather preliminary information for a potential EB1-A visa application. It features a chat interface and a sidebar that displays the collected information in real-time as a JSON object.

**Disclaimer:** This tool does **not** provide legal advice. It is intended for informational purposes and initial data collection only. Always consult a qualified immigration attorney for actual legal advice.

## Features

*   Conversational AI agent to guide the user through required EB1-A information fields.
*   Support for PDF resume uploads (text extraction).
*   Input for LinkedIn profile URL.
*   Real-time display of collected data in a structured JSON format in the sidebar.
*   Strict instructions for the agent to avoid giving legal advice.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    Ensure you have Python 3.8+.
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Requires `langchain>=0.2.0`, `langchain-openai>=0.1.0`, `pydantic>=2.0.0` and other libraries as specified in `requirements.txt`.*

4.  **Set up environment variables:**
    Create a `.env` file in the root directory and add your OpenAI API key:
    ```dotenv
    OPENAI_API_KEY='your_openai_api_key_here'
    ```

## Running the Application

```bash
streamlit run app.py
```

This will launch the Streamlit application in your web browser. The agent will start the conversation. Respond to its questions, and observe the "Collected Information Status" section in the sidebar update as you provide information.

## Agent Behavior Notes

*   The agent (`agents/visa_agent.py`) is instructed to ask questions systematically to fill a predefined structure.
*   It formats its internal responses with specific XML-like tags (`<conversation_response>` and `<updated_data>`) which the Streamlit app (`app.py`) parses to update the chat and the sidebar JSON display.
*   The prompt emphasizes the "not legal advice" constraint and focuses the agent solely on data gathering. 