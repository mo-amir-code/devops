import os,shutil,time,difflib

vdir="versions"
os.makedirs(vdir,exist_ok=True)

def save_versions(d):
    for f in os.listdir(d):
        p=os.path.join(d,f)
        if os.path.isfile(p):
            t=int(os.path.getmtime(p))
            v=f"{f}_{t}"
            shutil.copy2(p,os.path.join(vdir,v))

def restore(v,d):
    shutil.copy2(os.path.join(vdir,v),os.path.join(d,v.split("_")[0]))

def diff(v1,v2):
    a=open(os.path.join(vdir,v1)).read().splitlines()
    b=open(os.path.join(vdir,v2)).read().splitlines()
    for l in difflib.unified_diff(a,b): print(l)

def keep(n):
    fs=sorted(os.listdir(vdir),key=lambda x:os.path.getmtime(os.path.join(vdir,x)))
    for f in fs[:-n]: os.remove(os.path.join(vdir,f))

d=input("dir: ")
save_versions(d)

print("versions:",os.listdir(vdir))
c=input("r=restore d=diff k=keep n=none: ")

if c=="r":
    restore(input("version: "),d)
elif c=="d":
    diff(input("v1: "),input("v2: "))
elif c=="k":
    keep(int(input("keep last: ")))