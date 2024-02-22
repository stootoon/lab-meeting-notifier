import os
import pandas as pd
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from argparse import ArgumentParser

# Create a parser that will read the rota file, with default "lab-meeting-rota.csv"
# And a channel, defaulting to "#sinatest"
parser = ArgumentParser()
parser.add_argument('--rota_file', type=str, default="lab-meeting-rota.csv")
parser.add_argument('--channel', type=str, default="#sinatest")
args = parser.parse_args()

# Your Slack bot token
assert "SLACK_BOT_TOKEN" in os.environ, "Did not find environment variable SLACK_BOT_TOKEN."
slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

def send_message(message, channel="#sinatest"):
    print(f"Attempting to post:")
    print("--------------------")
    print(f"{message}")
    print("--------------------")
    print(f"to {channel}.")
    try:
        response = client.chat_postMessage(
            channel=channel,  # Channel ID or name
            text=message
        )
    except SlackApiError as e:
        print(f"Error posting message: {e}")

def get_userid_by_first_name(first_name):
    try:
        # Call the users.list method using the WebClient
        for page in client.users_list(limit=200):
            users = page["members"]
            for user in users:
                # Some users might not have a 'real_name' field (like bots)
                if 'real_name' in user and first_name in user['real_name'].split():
                    print(f"Found user: {user['real_name']} with ID: {user['id']}")
                    # You can also check 'user['name']' for the username
                    print(f"Slack Username: @{user['name']}")
                    return user['id']
    except SlackApiError as e:
        print(f"Error fetching users: {e}")

    print(f"User {first_name} not found.")
    return None

def get_slack_name(first_name):
    uid = get_userid_by_first_name(first_name)
    if uid is not None:
        return f"<@{uid}>"
    else:
        return first_name
        
def create_message(next_rota):
    meeting_place = next_rota["Location"] if pd.notna(next_rota["Location"]) else "Somewhere?"
    meeting_time  = next_rota["Time"].strftime("%H:%M")
    meeting_date  = next_rota["Date"].strftime("%A %d %B")
    meeting_type  = next_rota["Type"] if pd.notna(next_rota["Type"]) else "Regular Roundup"
    speaker = get_slack_name(next_rota["Speaker"] if pd.notna(next_rota["Speaker"]) else "Someone?")
    scribe  = get_slack_name(next_rota["Scribe"] if pd.notna(next_rota["Scribe"]) else "Someone?")

    
    # Is the date today?
    is_today = next_rota["Date"].date() == pd.Timestamp.today().date()
    is_tomorrow = next_rota["Date"].date() == pd.Timestamp.today().date() + pd.Timedelta(days=1)
    date_string = "*today*" if is_today else "*tomorrow*" if is_tomorrow else f"on *{meeting_date}*"
    
    if meeting_type.lower() == "no lm":
        message = f"Dear <!channel>, a reminder that there is *no lab meeting* {date_string}"
        if next_rota["Comments"]:
            message += f" because {next_rota['Comments']}.\n"
        else:
            message += ".\n"
    elif meeting_type.lower() == "journal club":
        message = f"Dear <!channel>, a reminder that the lab meeting {date_string} will be a *Journal Club*.\n"
        message += f"{speaker} will be leading the discussion.\n"
        if scribe:
            message += f"{scribe} will be the scribe.\n"
        message += f"We will meet in *{meeting_place}* at *{meeting_time}*.\n"
        message += f"Please prepare a *very short* roundup slide.\n"    
        message += "See you then!"
    elif meeting_type.lower() == "project presentation":
        message = f"Dear <!channel>, a reminder that the lab meeting {date_string} will be a *Project Presentation*.\n"
        message += f"{speaker} will be presenting their work.\n"
        message += f"We will meet in *{meeting_place}* at *{meeting_time}*.\n"
        message += "Please prepare a *very short* roundup slide.\n"
        message += "See you then!"
    elif meeting_type.lower() == "regular roundup":
        message = f"Dear <!channel>, a reminder that the lab meeting {date_string} will be a *regular roundup*.\n"
        message += f"We will meet in *{meeting_place}* at *{meeting_time}*.\n"
        message += f"Please *prepare your slides*.\n"
        message += "See you then!"
    else:
        message = f"Don't know what to say for {next_rota}."

    return message

assert os.path.exists(args.rota_file), f"Could not find rota file {args.rota_file}."
print(f"Reading rota from {args.rota_file}.")
rota = pd.read_csv(args.rota_file)
# Convert the date to a datetime object
rota["Date"] = pd.to_datetime(rota["Date"], format="%d.%m.%Y")
# The meeting time is in a string format %H:%M. We want to add this to the date to make a datetime object
rota["Time"] = pd.to_datetime(rota["Time"], format="%H:%M").dt.time
# Combine the date and time into a single datetime object
rota["Date"] = pd.to_datetime(rota["Date"].astype(str) + " " + rota["Time"].astype(str))

N = 0
rotas = rota[rota["Date"] > pd.Timestamp.today() - pd.Timedelta(days=N*7)]
# Read the first row into a dictionary
next_rota = rotas.iloc[0].to_dict()
print(f"{next_rota=}")
msg = create_message(next_rota)
send_message(msg)
