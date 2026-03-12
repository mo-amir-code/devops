ip=input()
email=input()

print("\n\nWithout regex:")

p=ip.split('.')
print("Valid IPv4" if len(p)==4 and all(x.isdigit() and 0<=int(x)<=255 for x in p) else "Invalid IP")

u="@gmail.com"
a="abcdefghijklmnopqrstuvwxyz0123456789._%+-"
print("Valid Gmail" if email.endswith(u) and all(c in a for c in email[:-10]) and email[:-10] else "Invalid Email")


print("\n\nWith regex:")

import re

print("Valid IPv4" if re.match(r'^((25[0-5]|2[0-4]\d|1\d\d|\d\d|\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|\d\d|\d)$',ip) else "Invalid IP")

print("Valid Gmail" if re.match(r'^[a-z0-9._%+-]+@gmail\.com$',email) else "Invalid Email")