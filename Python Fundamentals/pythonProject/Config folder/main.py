from config import name, age, games

print(f"Name: {name}")
print(f"Age: {age}")
print("Favorite Games:")

counter = 0

while counter < len(games):
    print(f"{counter + 1}: {games[counter]}")
    counter += 1
    