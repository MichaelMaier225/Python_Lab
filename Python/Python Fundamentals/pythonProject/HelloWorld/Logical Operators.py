temp = int(input("What is the temperature outside?: "))

if (temp>=65 and temp <=100):
    print("The temperature is good today!")
    print("Go outside!")
elif (temp < 65 or temp >100):
    print("The temperature is bad today!")
    print("Stay inside!")
