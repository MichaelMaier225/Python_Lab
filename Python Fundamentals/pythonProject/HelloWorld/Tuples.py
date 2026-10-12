student = ("Michael",19,"male")

print(student.count("Michael"))
print(student.index("male"))

for x in student:
    print(x)

if "Michael" in student:
    print("Michael is here!")