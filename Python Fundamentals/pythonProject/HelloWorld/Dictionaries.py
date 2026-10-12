capitals = {'USA':'Washington DC',
            'India':'New Dehli',
            'China':'Beijing',
            'Russia':'Moscow'}

capitals.update({'Germany':'Berlin'})
#capitals.update({'USA':'Las Vegas'})
#capitals.pop('China')
#capitals.clear()

#print(capitals['Russia'])
#print(capitals.get('Germany'))
#print(capitals.keys())
#print(capitals.values())
#print(capitals.items())

for k,v in capitals.items():
    if k != 'USA':  
        print(k, v)