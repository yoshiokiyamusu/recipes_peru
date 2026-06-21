import os
from dotenv import load_dotenv
from pathlib import Path

from langchain_core.messages import BaseMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field 
from typing import List

load_dotenv()

# Define the path to your .env file
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path) # Load the specific .env file
else:
    load_dotenv() # for Render's environment variables settings

GOOGLE_YK_API_KEY = os.getenv('GOOGLE_GEMINI_KEY')


# Define the structured Pydantic data models
class PhrasalVerb(BaseModel):
    wrong_meaning: str = Field(description="Wrong meaning of the phrasal verb. Make sure to provide an incorrect meaning that challenges the user but not the correct one.")
    
class Response(BaseModel):
    """A single response, Here I determine the quant"""   
    meaning: List[PhrasalVerb] = Field(description="List of 2 meaning suggestions")
    
# Initialize the structured model once when the file is imported
model = init_chat_model("gemini-2.5-flash", model_provider="google_genai", google_api_key=GOOGLE_YK_API_KEY, temperature=0.7)
structured_model = model.with_structured_output(Response)

system_prompt = """
You are an English teacher. Take the phrasal verb that the user provides and suggest 2 wrong meanings to trick and challenges the user.
"""


# Define the function that Flask will call
def get_ia_wrong_options(phrasal_verb_name: str) -> dict: #returns a standard Python dictionary object
    """
    Takes user phrasal_verb_name, queries the LangChain agent, 
    and returns a standard Python dictionary of the structured response.
    """
    messagesx = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": phrasal_verb_name}
    ]
    
    # Invoke the model
    response = structured_model.invoke(messagesx)
    
    # .model_dump() converts the Pydantic object into a native Python dictionary 
    # which Flask can easily store in a session or pass to HTML templates.
    return response.model_dump()

# Define the structured Pydantic data models
class PhrasalVerbSentence(BaseModel):
    grammar_check: str = Field(description="Is my sentence grammatically correct? Reply: Yes or No")
    grammar_feedback: str = Field(description="If the sentence is not grammatically correct, provide a corrected version of the sentence.")
    local_naturalness: str = Field(description="Does my sentence sound natural to a native US English speaker? Reply How a more natural version of the sentence would be.")

structured_model_2 = model.with_structured_output(PhrasalVerbSentence)

system_prompt_2 = """
You are an English teacher. Take the phrasal verb that the user provides and provide feedback on the sentence the user wrote.
"""

def get_ia_sentence_feedback(phrasal_verb_name: str, user_choice: str, user_sentence: str) -> dict: #returns a standard Python dictionary object
    """
    Takes user phrasal_verb_name, queries the LangChain agent, 
    and returns a standard Python dictionary of the structured response.
    """
    # 1. Combine the variables into a clean prompt string
    concat = f"Phrasal Verb: {phrasal_verb_name}\n  Meaning of the phrasal verb: {user_choice}\n User Sentence: {user_sentence}"
    
    # 2. Build the message history (FIXED: added 'concat' to content)
    messagesx_2 = [
        {"role": "system", "content": system_prompt_2},
        {"role": "user", "content": concat}
    ]
    
    # Invoke the model
    response_2 = structured_model_2.invoke(messagesx_2)
    
    # .model_dump() converts the Pydantic object into a native Python dictionary 
    # which Flask can easily store in a session or pass to HTML templates.
    return response_2.model_dump()