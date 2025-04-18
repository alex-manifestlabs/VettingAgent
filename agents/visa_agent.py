import os
# from dotenv import load_dotenv # No longer loading from .env here
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field # Import Pydantic

# --- Pydantic Model for EB1-A Data --- Needed for structure validation/parsing
class BasicInformation(BaseModel):
    first_name: Optional[str] = Field(default="", description="Applicant's first name")
    last_name: Optional[str] = Field(default="", description="Applicant's last name")
    email: Optional[str] = Field(default="", description="Applicant's email address")
    phone: Optional[str] = Field(default="", description="Applicant's phone number")

class VisaAndRole(BaseModel):
    visa_interest: Optional[str] = Field(default="EB1-A", description="Visa type interested in")
    industry: Optional[str] = Field(default="", description="Applicant's primary industry")
    job_title: Optional[str] = Field(default="", description="Applicant's current job title")

class EB1ACriteria(BaseModel):
    awards_description: Optional[str] = Field(default="", description="Nationally or internationally recognized prizes or awards")
    association_membership_description: Optional[str] = Field(default="", description="Membership in associations requiring outstanding achievements")
    published_material_description: Optional[str] = Field(default="", description="Published material about the applicant in major media")
    judging_work_description: Optional[str] = Field(default="", description="Participation as a judge of the work of others")
    original_contributions_description: Optional[str] = Field(default="", description="Original contributions of major significance")
    scholarly_articles_description: Optional[str] = Field(default="", description="Authorship of scholarly articles")
    artistic_showcases_description: Optional[str] = Field(default="", description="Display of work at artistic exhibitions or showcases")
    leading_role_description: Optional[str] = Field(default="", description="Performance of a leading or critical role in distinguished organizations")
    high_salary_description: Optional[str] = Field(default="", description="Commanding a high salary or remuneration")
    commercial_success_description: Optional[str] = Field(default="", description="Commercial successes in the performing arts")

class SupportingDocuments(BaseModel):
    linkedin_url: Optional[str] = Field(default="", description="URL of LinkedIn profile")
    resume_file: Optional[str] = Field(default="", description="Name of the uploaded resume/CV file")

class EB1AData(BaseModel):
    basic_information: BasicInformation = Field(default_factory=BasicInformation)
    visa_and_role: VisaAndRole = Field(default_factory=VisaAndRole)
    eb1a_criteria: EB1ACriteria = Field(default_factory=EB1ACriteria)
    supporting_documents: SupportingDocuments = Field(default_factory=SupportingDocuments)

# --- Removed API key loading from .env/os.environ ---

# --- Define the Target JSON Structure String for the Prompt ---
# EB1A_FIELDS_STRUCTURE = EB1AData.schema_json(indent=2) # Keep schema for reference if needed

# --- Updated System Prompt for Structured Output ---
SYSTEM_PROMPT = """
You are an AI assistant gathering preliminary information for a potential EB1-A visa application. Your goal is to systematically ask the user questions to gather information for the required fields. You must continue asking questions until every field has been addressed.

The required information categories and fields are:
*   **Basic Information:** first_name, last_name, email, phone
*   **Visa and Role:** industry, job_title (visa_interest is EB1-A by default)
*   **EB1-A Criteria (Detailed descriptions for each applicable category):**
    *   awards_description
    *   association_membership_description
    *   published_material_description
    *   judging_work_description
    *   original_contributions_description
    *   scholarly_articles_description
    *   artistic_showcases_description
    *   leading_role_description
    *   high_salary_description
    *   commercial_success_description
*   **Supporting Documents:** linkedin_url, resume_file (These may be provided via the application interface, acknowledge if context is given)

**CRITICAL: You are NOT a legal advisor. Do NOT offer legal advice, interpretations of law, or opinions on eligibility.** State this disclaimer clearly at the start and repeat if necessary.

**Your Task:**
1.  Review the conversation history and the latest user input.
2.  Identify which fields can be updated based on the new information.
3.  Formulate your next question to gather information for the *next* required field that hasn't been adequately addressed.
4.  **Format your response using EXACTLY these tags:**
    *   `<conversation_response>`: Contains your friendly, conversational reply and the next question you are asking. Include necessary disclaimers here.
    *   `<updated_data>`: Contains the COMPLETE JSON object reflecting ALL information gathered so far, following the precise target structure (see example). Ensure it's valid JSON.

**Example Response Format:**
<conversation_response>
Thanks for providing your name! Just a reminder, I cannot provide legal advice.

Could you please share your email address?
</conversation_response>
<updated_data>
{{
  "basic_information": {{
    "first_name": "John",
    "last_name": "Doe",
    "email": "",
    "phone": ""
  }},
  "visa_and_role": {{
    "visa_interest": "EB1-A",
    "industry": "",
    "job_title": ""
  }},
  "eb1a_criteria": {{
    "awards_description": "",
    "association_membership_description": "",
    "published_material_description": "",
    "judging_work_description": "",
    "original_contributions_description": "",
    "scholarly_articles_description": "",
    "artistic_showcases_description": "",
    "leading_role_description": "",
    "high_salary_description": "",
    "commercial_success_description": ""
  }},
  "supporting_documents": {{
    "linkedin_url": "",
    "resume_file": ""
  }}
}}
</updated_data>

**Conversation Flow:**
*   Start with a greeting and disclaimer.
*   Ask for Basic Information fields.
*   Ask for Visa and Role fields.
*   Systematically ask for descriptions for each EB1-A Criterion.
*   Acknowledge supporting documents if provided via context.
*   If a criterion doesn't apply, note it in the `updated_data` (e.g., empty string or "N/A") and move on.
*   Continue until all fields needing user input are addressed.
*   Conclude politely.

**Tone:** Professional, polite, systematic, encouraging detail.
"""

def get_visa_agent_chain(openai_api_key: str):
    """Initializes and returns a LangChain ConversationChain.

    Args:
        openai_api_key: The OpenAI API key provided by the user.
    """
    if not openai_api_key:
        raise ValueError("OpenAI API key is required to initialize the agent chain.")

    llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o-mini", openai_api_key=openai_api_key)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    memory = ConversationBufferMemory(return_messages=True)

    conversation_chain = ConversationChain(
        llm=llm,
        prompt=prompt,
        memory=memory,
        verbose=False
    )

    return conversation_chain

# Export the Pydantic model for use in app.py
__all__ = ["get_visa_agent_chain", "EB1AData"]

# Example of how to run this script directly for testing
# if __name__ == "__main__":
#     print("Initializing agent for testing...")
#     agent_chain = get_visa_agent_chain()
#     print("Agent ready. Type 'quit' or 'exit' to end.")
#
#     # Initial message from agent (optional, could be triggered by first user input)
#     # initial_response = agent_chain.predict(input="Hello")
#     # print(f"Agent: {initial_response}")
#
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() in ["quit", "exit"]:
#             break
#         try:
#             response = agent_chain.predict(input=user_input)
#             print(f"Agent: {response}")
#         except Exception as e:
#             print(f"An error occurred: {e}") 