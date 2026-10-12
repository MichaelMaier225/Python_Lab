import time
import random
import os
import itertools
from colorama import init, Fore, Style
import string

init()

# Clear terminal
os.system('cls' if os.name == 'nt' else 'clear')

# Custom Banner: MaierTrace
print(Fore.RED + Style.BRIGHT + r"""
.___  ___.      ___       __   _______ .______      .___________..______           ___        ______  _______ 
|   \/   |     /   \     |  | |   ____||   _  \     |           ||   _  \         /   \      /      ||   ____|
|  \  /  |    /  ^  \    |  | |  |__   |  |_)  |    `---|  |----`|  |_)  |       /  ^  \    |  ,----'|  |__   
|  |\/|  |   /  /_\  \   |  | |   __|  |      /         |  |     |      /       /  /_\  \   |  |     |   __|  
|  |  |  |  /  _____  \  |  | |  |____ |  |\  \----.    |  |     |  |\  \----. /  _____  \  |  `----.|  |____ 
|__|  |__| /__/     \__\ |__| |_______|| _| `._____|    |__|     | _| `._____|/__/     \__\  \______||_______|
                                                                                                             
""" + Style.RESET_ALL)

# Configuration
charset = string.ascii_lowercase + string.digits
password_length = 4
target_password = ''.join(random.choices(charset, k=password_length))
attempts = 0
visual_interval = 500

# Fake visuals
ips = [f"172.16.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(40)]
users = ["root", "sysadmin", "operator", "guest"]
files = ["log_exfiltrator.py", "sys_stealer.exe", "vault_breach.sh", "payload.dll"]
ai_msgs = [
    "[✓] AI Routine: Signal spoofing enabled",
    "[✓] Neural Overclock: Bypassed heuristic firewall",
    "[✓] Quantum thread initiated on target socket"
]
systems = ["AI-Grid", "BlackICE", "NeuralHub", "CoreVault", "EchoNode"]

# Visual pulse progress bar
def pulse_bar():
    for i in range(0, 31, 3):
        bar = "=" * i + "-" * (30 - i)
        sys = random.choice(systems)
        print(Fore.MAGENTA + f"[{bar}] Probing {sys}..." + Fore.RESET, end='\r')
        time.sleep(0.02)
    print()

# Brute-force engine
cracked = False
for guess_tuple in itertools.product(charset, repeat=password_length):
    guess = ''.join(guess_tuple)
    attempts += 1

    # Display fake hacking logic every few thousand guesses
    if attempts % visual_interval == 0:
        ip = random.choice(ips)
        user = random.choice(users)
        print(Fore.YELLOW + f"\n[*] Attempt #{attempts:,} | Target: {user}@{ip}" + Fore.RESET)

        fake_logic = [
            f"[~] Injecting dictionary module...",
            f"[~] Evaluating entropy of: '{guess}'",
            f"[~] Replaying keylog buffer...",
            f"[~] Performing handshake spoof...",
            f"[~] Decrypting challenge token...",
            f"[~] Reading /etc/shadow replicas...",
            f"[~] Disabling honeypot tracking..."
        ]
        for line in random.sample(fake_logic, 3):
            print(Fore.BLUE + line + Fore.RESET)
            time.sleep(0.08)

        print(Fore.MAGENTA + f"[>] Trying password: '{guess}'" + Fore.RESET)
        pulse_bar()

    if guess == target_password:
        print(Fore.GREEN + "\n[ACCESS GRANTED]" + Fore.RESET)
        file = random.choice(files)
        print(Fore.CYAN + f"[+] Injecting {file} to target memory..." + Fore.RESET)
        time.sleep(0.3)
        print(Fore.CYAN + "[+] Operation complete." + Fore.RESET)
        print(Fore.MAGENTA + random.choice(ai_msgs) + Fore.RESET)
        print(Fore.GREEN + Style.BRIGHT + f"\n✔ SUCCESS: Password cracked in {attempts:,} attempts → '{target_password}'" + Style.RESET_ALL)
        cracked = True
        break

# Fallback if somehow not cracked (shouldn't happen)
if not cracked:
    print(Fore.RED + "\n✘ Failed to crack password within simulation limits." + Fore.RESET)
    print(Fore.YELLOW + f"The password was: {target_password}" + Fore.RESET)
