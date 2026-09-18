import asyncio,time,statistics,sys,httpx,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
case=json.loads((BASE/"data/public_samples.json").read_text())["cases"][0]["input"]
url=sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8000"
async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        await c.get(url+"/health")
        vals=[]
        failures=0
        for _ in range(20):
            t=time.perf_counter()
            try:
                r=await c.post(url+"/optimize-energy",json=case)
                r.raise_for_status()
            except Exception:
                failures+=1
            vals.append(time.perf_counter()-t)
    q=lambda p: statistics.quantiles(vals,n=100,method="inclusive")[p-1]
    print({"n":len(vals),"failures":failures,"p50_s":statistics.median(vals),
           "p95_s":q(95),"p99_s":q(99),"max_s":max(vals)})
asyncio.run(main())
