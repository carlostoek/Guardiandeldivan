import json
from datetime import datetime

ADMIN_INBOX = "admin_inbox.json"


def send_message_to_admin(user_id: str, text: str) -> None:
    """Send a message from a user to the administrator.

    The message is appended to a JSON file so the administrator can
    review it later. This function creates the file if it does not
    exist and preserves previous messages.
    """
    entry = {
        "user_id": user_id,
        "message": text,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    try:
        with open(ADMIN_INBOX, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []

    data.append(entry)

    with open(ADMIN_INBOX, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Send a message to the admin")
    parser.add_argument("user_id", help="Identifier for the user")
    parser.add_argument("message", help="Message to send")
    args = parser.parse_args()

    send_message_to_admin(args.user_id, args.message)
    print("Message sent.")
