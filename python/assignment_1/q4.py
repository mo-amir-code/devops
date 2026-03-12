import subprocess,logging

logging.basicConfig(filename="update log.txt",level=logging.ERROR)

def check_updates():
    subprocess.run(["sudo","apt","update"],stdout=subprocess.DEVNULL)
    r=subprocess.run(["apt","list","--upgradable"],capture_output=True,text=True)
    p=r.stdout.splitlines()[1:]
    for i,x in enumerate(p): print(i,x)
    return p

def install_all():
    subprocess.run(["sudo","apt","upgrade","-y"])

def install_one(pkg):
    try:
        name=pkg.split("/")[0]
        subprocess.run(["sudo","apt","install","-y",name],check=True)
    except Exception as e:
        logging.error(str(e))
        print("ALERT: update failed for",name)

pkgs=check_updates()
c=input("a=all or index: ")

if c=="a":
    install_all()
else:
    install_one(pkgs[int(c)])