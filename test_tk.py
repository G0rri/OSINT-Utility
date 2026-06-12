import tkinter as tk
import customtkinter as ctk
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

from modules.virustotal_module import VirustotalModule

app = ctk.CTk()
vt = VirustotalModule()
status, msg = vt.check_health()

if status == "ok":
    emoji = " 🟢"
else:
    emoji = " 🔴"

print(f"Status is {status}, Emoji is {emoji}")
