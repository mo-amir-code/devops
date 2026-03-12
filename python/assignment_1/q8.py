import json,csv

d=json.load(open("sales.json"))
rows=[]
spend={}

for o in d["orders"]:
    cid=o["customer"]["id"]
    cname=o["customer"]["name"]
    cc=o["shipping_address"].split(",")[-1].strip()
    for i in o["items"]:
        price=i["price"]
        q=i["quantity"]
        total=price*q
        disc=0.1*total if total>100 else 0
        ship=5*q
        final=total-disc+ship

        r=[o["order_id"],cname,i["name"],price,q,total,disc,ship,final,o["shipping_address"],cc]
        rows.append(r)

        spend[cid]=spend.get(cid,0)+final

rows.sort(key=lambda x:spend[[k for k,v in spend.items() if v>=0][0]],reverse=True)

h=["Order ID","Customer Name","Product Name","Product Price","Quantity Purchased","Total Value","Discount","Shipping Cost","Final Total","Shipping Address","Country Code"]

with open("sales_output.csv","w",newline="") as f:
    w=csv.writer(f)
    w.writerow(h)
    w.writerows(rows)