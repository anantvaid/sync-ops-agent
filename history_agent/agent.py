from google.adk.agents import Agent
from google.adk.tools import FunctionTool
import os
from google.cloud import firestore

db = firestore.Client()

def get_meetings_from_firestore(limit: int = 10) -> dict:
    """Retrieves the most recent meeting summaries from Firestore.
    Use this when the user asks about past meetings or history.
    Args:
        limit: number of meetings to return (default 10, max 50)
    """
    try:
        limit = min(limit, 50)
        docs = (
            db.collection("meetings")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        meetings = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            meetings.append(data)

        return {"meetings": meetings, "count": len(meetings)}
    except Exception as e:
        logger.error(f"Firestore read failed: {e}")
        return {"meetings": [], "count": 0, "error": str(e)}

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
