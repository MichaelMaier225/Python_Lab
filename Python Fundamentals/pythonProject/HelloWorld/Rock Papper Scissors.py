import random

choices = ["Rock","Paper","Scissors"]

computer = random.choice(choices)
player = None

while player not in choices:
    player = input("Rock, Paper, or Scissors?: ")


if player == computer:
    print("Player: ", player)
    print("Computer: ",computer)
    print("Tie!")
elif player == "Rock":
    if computer == "Paper":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You lose!")
    if computer == "Scissors":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You win!")

elif player == "Scissors":
    if computer == "Rock":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You lose!")
    if computer == "Paper":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You win!")

elif player == "Paper":
    if computer == "Rock":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You win!")
    if computer == "Scissors":
        print("Player: ", player)
        print("Computer: ", computer)
        print("You lose!")