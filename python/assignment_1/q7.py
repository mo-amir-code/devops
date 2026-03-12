sizes=["nano","micro","small","medium","large","xlarge","2xlarge","4xlarge","8xlarge","16xlarge","32xlarge"]

def table(data):
    w=[max(len(str(r[i])) for r in data) for i in range(len(data[0]))]
    b="+"+"+".join("-"*(x+2) for x in w)+"+"
    print(b)
    for r in data:
        print("|"+"|".join(" "+str(r[i]).ljust(w[i])+" " for i in range(len(r)))+"|")
        print(b)

ec2=input("Current EC2: ")
cpu=int(input("CPU: ").replace("%",""))

t,s=ec2.split(".")
i=sizes.index(s)

if cpu<20:
    status="Underutilized"
    r=t+"."+sizes[i-1] if i>0 else ec2
elif cpu>80:
    status="Overutilized"
    r=t+"."+sizes[i+1] if i<len(sizes)-1 else ec2
else:
    status="Optimized"
    r="t3."+s

data=[
["serial no.","current ec2","current CPU","status","recommended ec2"],
[1,ec2,str(cpu)+"%",status,r]
]

table(data)