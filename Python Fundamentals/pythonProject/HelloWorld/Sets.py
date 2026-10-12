utensils = {"fork","spoon","knife"}
dishes = {"plate","bowl","cup","knife"}

utensils.add("napkin")
utensils.remove("fork")
#utensils.clear()
#dishes.update(utensils)
dinner_table = utensils.union(dishes)

for x in dinner_table:
    print(x)

#Differene is the variables that doesn't match up
#print(dishes.difference(utensils))
#print(utensils.difference(dishes))

#Intersection is the varaibles that are alike
#print(dishes.intersection(utensils))
#print(utensils.intersection(dishes))
