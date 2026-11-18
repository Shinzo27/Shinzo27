
import json, collections
d=json.load(open("data/contributions.json"))
days=d["days"]; mx=max(days.values())
c=collections.Counter()
for v in days.values():
    if v==0: c[0]+=1
    else: c[min(4,1+int((v/mx)**0.45*3.4))]+=1
print("max",mx,"levels",dict(sorted(c.items())), "active", sum(v for k,v in c.items() if k))
