import json,sys
ex=sys.argv[1]; d=json.load(open(f'receipts/audit-{ex}.json'))
if d.get('status')!='success': sys.exit(f'{ex}: audit {d.get("status")}')
r=d['result']; a=json.loads(r[r.index('['):r.rindex(']')+1])
json.dump(a,open(f'evidence/audit-{ex}.json','w'),ensure_ascii=False,indent=1); print(ex,len(a))
