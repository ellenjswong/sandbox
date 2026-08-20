import os
import json
import re
import requests
from twilio.rest import Client

# Fetch credentials from GitHub Secrets
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.environ.get("FROM_WHATSAPP")
TO_WHATSAPP = os.environ.get("TO_WHATSAPP")

# Target settings
TARGET_TEAMS = ["Dragon Hybrids", "FCRCC Saggin Dragons"]
TARGET_URL = "https://concord2026.pages.dev/"
STATE_FILE = "sent_notifications.json"

def load_sent_alerts():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading state file: {e}")
    return set()

def save_sent_alerts(sent_set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(sent_set), f)

def check_advancements():
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, FROM_WHATSAPP, TO_WHATSAPP]):
        print("Missing required Twilio environment variables.")
        return

    sent_alerts = load_sent_alerts()

    try:
        response = requests.get(TARGET_URL, timeout=10)
        response.raise_for_status()
        content = response.text

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        for team in TARGET_TEAMS:
            # Case-insensitive regex check for Team Name AND ("Semi" OR "Final")
            # Ensures the alert only triggers if the team is listed near/in an advancement context
            team_pattern = re.escape(team)
            advancement_pattern = rf"{team_pattern}.*?(semi|final)|(semi|final).*?{team_pattern}"
            
            match = re.search(advancement_pattern, content, re.IGNORECASE | re.DOTALL)

            if match:
                race_stage = match.group(1) or match.group(2)
                stage_name = race_stage.upper()
                
                # Unique key per team per stage to allow 1 notification for Semi and 1 for Final
                alert_key = f"{team}_{stage_name}_notified"

                if alert_key not in sent_alerts:
                    message_body = (
                        f"🏁 ADVANCEMENT ALERT ({stage_name})!\n\n"
                        f"Team: {team}\n"
                        f"Your {stage_name} advancement is posted on the board!\n\n"
                        f"Check schedule: {TARGET_URL}"
                    )

                    message = client.messages.create(
                        body=message_body,
                        from_=FROM_WHATSAPP,
                        to=TO_WHATSAPP
                    )
                    
                    print(f"Sent WhatsApp alert for {team} [{stage_name}]. Message SID: {message.sid}")
                    sent_alerts.add(alert_key)
                else:
                    print(f"Already notified for {team} [{stage_name}]. Skipping.")

    except Exception as e:
        print(f"Error checking site: {e}")

    # Save state to prevent duplicate alerts in future GitHub Action runs
    save_sent_alerts(sent_alerts)

if __name__ == "__main__":
    check_advancements()
