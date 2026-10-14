# from cryptography.fernet import Fernet
# import base64
# import os
# from datetime import datetime

# PASSWORD = "ShriShri2026"

# def generate_key(password):
#     return base64.urlsafe_b64encode(password.ljust(32)[:32].encode())

# key = generate_key(PASSWORD)
# cipher = Fernet(key)

# def log_conversation(user, bot):
#     date = datetime.now().strftime("%Y-%m-%d")
#     time = datetime.now().strftime("%H:%M")

#     os.makedirs("logs", exist_ok=True)
#     file_path = f"logs/{date}.enc"

#     data = f"[{time}] User: {user}\n[{time}] Jarvis: {bot}\n\n"

#     encrypted = cipher.encrypt(data.encode())

#     with open(file_path, "ab") as f:
#         f.write(encrypted + b"\n")

from datetime import datetime

from app.core.config import LOG_DIR


def log_conversation(user: str, bot: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    file_path = LOG_DIR / f"{date}.txt"

    with file_path.open("a", encoding="utf-8") as file:
        file.write(f"[{time}] User: {user}\n")
        file.write(f"[{time}] Jarvis: {bot}\n\n")