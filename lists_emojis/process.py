#! /usr/bin/python3

import json

with open("list3","r",encoding='UTF-8') as fd:
	lines = fd.readlines()

emojis = []
for line in lines:
	text = line.replace(">","<").split("<")
	emojis.append({"emoji":text[10],"desc":text[12].strip().lower().replace(":","")})

with open("emojis.json","w",encoding='UTF-8') as fd:
	fd.write(json.dumps(emojis))

print(emojis[0])
print(emojis[1])
print(emojis[2])
print(emojis[3])
print(emojis[4])
