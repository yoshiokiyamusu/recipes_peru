

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
class Recipe(BaseModel):
    name: str = Field(description="Name of the recipe")
    description: str = Field(description="Brief description of the recipe, use no more than 20 words")
    prep_time: str = Field(description="Estimated preparation time of the recipe")

class RecipeComplexity(BaseModel):
    name: str = Field(description="Name of the recipe")
    level: str = Field(description="Difficulty level scale, for example: '3 of 10'")

class Response(BaseModel):
    """A single recipe response"""
    ingredients: List[str] = Field(description="List of main ingredients")
    recipes: List[Recipe] = Field(description="List of 3 recipe suggestions")
    complexity: List[RecipeComplexity] = Field(description="List of complexity levels mapped to each recipe name")

# Initialize the structured model once when the file is imported
model = init_chat_model("gemini-2.5-flash", model_provider="google_genai", google_api_key=GOOGLE_YK_API_KEY, temperature=0.7)
structured_model = model.with_structured_output(Response)

system_prompt = """
You are a helpful chef. Take the ingredients that the user provides and suggest 3 peruvian recipes based using those ingredients.
"""

# Define the function that Flask will call
def get_recipes(user_ingredients: str) -> dict: #returns a standard Python dictionary object
    """
    Takes user ingredients, queries the LangChain agent, 
    and returns a standard Python dictionary of the structured response.
    """
    messagesx = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_ingredients}
    ]
    
    # Invoke the model
    response = structured_model.invoke(messagesx)
    
    # .model_dump() converts the Pydantic object into a native Python dictionary 
    # which Flask can easily store in a session or pass to HTML templates.
    return response.model_dump()