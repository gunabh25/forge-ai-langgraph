import sys
import json
import logging
logging.basicConfig(level=logging.INFO)

from app.settings import settings
# Override for testing
settings.ENABLE_FEW_SHOT = True
settings.ENABLE_UML_REVIEW = True

from agents.uml_generator.agent import UMLGeneratorAgent
from app.state import ForgeState
from langchain_google_genai import ChatGoogleGenerativeAI
from unittest.mock import MagicMock

# Mock LLM to avoid real calls or use a cheap one if available
# We'll just run it with the real LLM for a small test if API key is present
agent = UMLGeneratorAgent()

# We only want to test prompt building actually to avoid API costs
summary = """
Actors: Customer
Business Capabilities: Order Management, Payment
"""
plan = """
{
  "actors": ["Customer"],
  "external_systems": [],
  "major_components": ["Order Management", "Payment"],
  "major_data_stores": [],
  "business_flow": [],
  "explicitly_excluded": [],
  "diagram_scope": "Shows core flow"
}
"""

sys_prompt, user_prompt = agent.prompt_builder.build_prompt(
    diagram_type="component",
    architecture_summary=summary,
    diagram_plan=plan
)
print("--- SYSTEM PROMPT ---")
print(sys_prompt[:200] + "...")
print("--- USER PROMPT ---")
print(user_prompt)

