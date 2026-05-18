from dotenv import load_dotenv
import os
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

from modules.virustotal_module import VirustotalModule
from modules.phoneinfoga_module import PhoneInfogaModule

vt = VirustotalModule()
print("VT:", vt.check_health())

pi = PhoneInfogaModule()
print("PI:", pi.check_health())
