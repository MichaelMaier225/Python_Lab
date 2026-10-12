import random
import os

people = ["Michael", "Dylan", "Kevin", "Ethan"]

while True:
    receivers = people[:]
    random.shuffle(receivers)
    if all(p != r for p, r in zip(people, receivers)):
        break

pairs = dict(zip(people, receivers))

for person in people:
    os.system("cls" if os.name == "nt" else "clear")
    input(f"{person}, press Enter...")
    print()
    print("You are buying a gift for:")
    print(pairs[person])
    input("\nPress Enter to hide your match")

os.system("cls" if os.name == "nt" else "clear")
print("Done. Everyone has their assignment.")
