import csv

f=input("csv file: ")
d=list(csv.reader(open(f)))

w=[max(len(r[i]) for r in d) for i in range(len(d[0]))]

b="+"+"+".join("-"*(x+2) for x in w)+"+"

print(b)
for r in d:
    print("|"+"|".join(" "+r[i].ljust(w[i])+" " for i in range(len(r)))+"|")
    print(b)