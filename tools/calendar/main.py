import sys
from pathlib import Path

# 1. Add Project Root to Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from tools.sdk.base_tool import BaseTool

# 2. Initialize Tool
tool = BaseTool(__file__)

# --- CONFIGURATION ---
# REPLACE THIS with your specific Calendar ID (often your email address)
# You can find this in Google Calendar Settings > Integrate Calendar > Calendar ID
CAL_ID = "en.usa%23holiday%40group.v.calendar.google.com" # Example: US Holidays
TIMEZONE = "America/New_York"

# Construct the cleaned-up URL for a widget
# mode=AGENDA: Shows a list of events (fits better in small box)
# showNav=0, etc: Hides the header/footer junk
CAL_URL = (
    f"https://calendar.google.com/calendar/embed?"
    f"src={CAL_ID}&ctz={TIMEZONE}"
    "&mode=AGENDA&showNav=0&showDate=0&showPrint=0&showTabs=0&showCalendars=0&showTitle=0"
    "&bgcolor=%23ffffff"
)

# 3. Define Widget
def widget_html():
    return f"""
    <!DOCTYPE html>
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; }}
        iframe {{ border: 0; width: 100%; height: 100%; }}
    </style>
    <iframe src="{CAL_URL}"></iframe>
    """

tool.add_widget_route(widget_html)

if __name__ == "__main__":
    tool.run()