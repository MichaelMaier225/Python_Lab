age = int(input("How old are you?: "))

if age >= 100:
    print("You are over a century old!")
elif age >= 50:
    print("You are really young and beautiful!")
elif age >= 18:
    print("You are an adult!")
elif age <0:
    print("You haven't been born yet!")
else:
    print("You are a child!")

