import os,hashlib,shutil

d=input("directory: ")
m=int(input("min size bytes: ") or 0)
a=input("d=delete m=move n=none: ")

h={}
for r,_,f in os.walk(d):
    for x in f:
        p=os.path.join(r,x)
        if os.path.getsize(p)<m: continue
        s=hashlib.sha256(open(p,'rb').read()).hexdigest()
        h.setdefault(s,[]).append(p)

rep=open("duplicate report.txt","w")

for k,v in h.items():
    if len(v)>1:
        print("\nchecksum:",k)
        rep.write(f"\n{k}\n")
        for i,p in enumerate(v):
            print(i,p)
            rep.write(p+"\n")
        for p in v[1:]:
            if a=="d": os.remove(p)
            if a=="m":
                os.makedirs("duplicates",exist_ok=True)
                shutil.move(p,"duplicates/"+os.path.basename(p))

rep.close()