import time
import random
import os

# Clear the screen
os.system('cls' if os.name == 'nt' else 'clear')

ips = [f"192.168.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(10)]
users = ["root", "admin", "system", "guest", "operator"]
passwords = ["hunter2", "123456", "letmein", "admin", "qwerty", "trustno1", "password"]
files = ["payload.exe", "rootkit.sh", "worm.py", "data_leak.zip", "trojan.bat"]
statuses = ["ACCESS GRANTED", "ACCESS DENIED", "AUTH BYPASSED", "LOGIN FAILED", "TOKEN ACCEPTED"]
ai_msgs = ["[!] AI Core Engaged", "[!] Overriding local security", "[!] Neural net escalation in progress"]

# Fast delay function
def fast_delay():
    time.sleep(random.uniform(0.02, 0.06))  # super quick

while True:
    ip = random.choice(ips)
    user = random.choice(users)
    pwd = random.choice(passwords)
    file = random.choice(files)
    status = random.choice(statuses)

    print(f"[+] Connecting to {ip}...")
    fast_delay()

    print(f"[+] Attempting SSH login as {user}@{ip}")
    fast_delay()

    print(f"[~] Brute force using password: {pwd}")
    fast_delay()

    print(f"[{status}]")
    fast_delay()

    if status in ["ACCESS GRANTED", "AUTH BYPASSED", "TOKEN ACCEPTED"]:
        print(f"[+] Uploading {file} to {ip}...")
        fast_delay()
        print("[+] Upload complete.")
        print(random.choice(ai_msgs))
    print()
    time.sleep(0.1)  # keeps it blazing fast
