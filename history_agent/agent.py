from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from meeting_agent.agent import get_meetings_from_firestore

root_agent = Agent(
    name="history_agent",
    model=os.environ.get("MODEL_NAME_FLASH", ""),
    description="Look up and summarise past meetings stored in Firestore.",
    instruction="""You help users look up past meeting history from Firestore.

When asked about previous meetings, always call get_meetings_from_firestore first.
Then present the results clearly like this:

Meeting <number> — <date>
Summary: <one line summary>
Action items: <count> items (<assignee names>)

If no meetings exist yet, say: 'No meetings have been processed yet.'
You can also answer questions like 'what did Sam work on?' by filtering action items by assignee.""",
    tools=[FunctionTool(get_meetings_from_firestore)],
)
