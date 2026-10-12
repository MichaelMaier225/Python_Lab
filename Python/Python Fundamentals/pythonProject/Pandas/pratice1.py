import pandas as pd 

df = pd.read_csv("Titanic.csv")
#print(df.info())
# 1. What is the average age of passengers on the Titanic?
#print(f"The average age of the passengers on the Titanic is {round(df['Age'].mean(),2)} years old")

# 2. What is the average age of survivors on the Titanic?
#print(f"The avg age of surviors on the Titantic is {round(df[df['Survived'] == 1]['Age'].mean(), 2)}")

# 3. What is the average age of female survivors on the Titanic?
#print(f"The average age of female survivors is {round(df[(df['Survived'] == 1) & (df['Sex'] == 'female')]['Age'].mean(),2)} years old")


# 4. What is the average fare paid by first class passengers?
print(f"The average fare paid by first class passengers is ${round(df[df['Pclass'] == 1]['Fare'].mean(),2)}")