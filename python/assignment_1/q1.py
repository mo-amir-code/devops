import re

ip=input()
email=input()

p=ip.split('.')
if len(p)!=4 or any(not x.isdigit() or not 0<=int(x)<=255 for x in p):
    print("Invalid IP")
else:
    print("Valid IPv4")

if "@gmail.com" not in email:
    print("Invalid Email")
elif not re.match(r'^[a-z0-9._%+-]+@gmail\.com$',email):
    print("Invalid Email")
else:
    print("Valid Gmail")