import json,glob,os,re,collections
env2tr=json.load(open('env2tr.json'))
rel=json.load(open('s/rel.json')); unm=json.load(open('s/unm.json'))
projs={}
for f in glob.glob('s/*.json'):
    n=os.path.basename(f)[:-5]
    if n in('rel','unm'):continue
    projs[n]=json.load(open(f))
B={'bbduk':'bbtools'}
def trpaths(envs):
    out=[]
    for e in envs:
        for t in env2tr.get(e,[]):
            p='src/metasmith_libraries/transforms/'+t
            if '_disabled' in p: continue
            if p not in out: out.append(p)
    out.sort(key=lambda p:(('/logistics/' in p) or p.split('/')[-1].startswith('build')))
    return out
rows=[];used=set()
for line in open('spec.txt'):
    line=line.rstrip('\n')
    if not line or line.startswith('#'):continue
    tool,dom,keys,envs,extra,xn,notes=line.split('|')
    keys=[k for k in keys.split(',') if k]; envs=[e for e in envs.split(',') if e]
    extras=[x for x in extra.split(';') if x.strip()]
    groups=set(); ev=[]
    std_ev=None; res_ev=None
    for k in keys:
        used.add(k)
        for f in rel.get(k,{}).get('rel',[]):
            if f.startswith(('docs/','tests/')): continue
            if f.startswith('src/'):
                groups.add('std')
                if std_ev is None and f.startswith('src/metasmith_libraries/transforms') : std_ev=f
                elif std_ev is None and 'resources' in f and 'data_types' not in f: std_ev=std_ev
            elif f.startswith('research/'):
                groups.add('r:'+f.split('/')[1])
                if res_ev is None and '/library/' in f or (res_ev is None and 'drivers' in f): res_ev=f
            else: groups.add('build')
        for br,fs in unm.get(k,{}).items():
            groups.add('u:'+br)
        for p,d in projs.items():
            if k in d:
                groups.add('p:'+p)
    trs=trpaths(envs)
    if trs and std_ev is None: std_ev=trs[0]
    if trs: groups.add('std')
    # std-only filter: if tool has std transform, and no census std group, ok
    refs=[]
    if trs: refs.append('metasmith@release:'+trs[0])
    elif std_ev: refs.append('metasmith@release:'+std_ev)
    elif res_ev: refs.append('metasmith@release:'+res_ev)
    # other projects
    for k in keys:
        for p,d in projs.items():
            if k in d:
                fs=[f for f in list(d[k].values())[0] if '_metadata' not in f and 'lib/transforms' not in f]
                fs.sort(key=lambda f:(0 if f.endswith(('.py','.sh','.sbatch','.R')) else 1, len(f)))
                if fs: refs.append(f'{p}:{fs[0]}'); break
        if len(refs)>=2: break
    for x in extras:
        x=x.strip()
        if x.startswith(('src/','research/')): x='metasmith@release:'+x
        x=x.replace('journal:journal:','journal:')
        if x=='nothing': continue
        refs.append(x)
    # dedupe preserve
    seen=[];[seen.append(r) for r in refs if r not in seen]
    refs=seen[:3]
    n=max(1,len(groups)+int(xn))
    if not refs: continue
    OV={'prodigal-gv':['viromics/prodigal_gv.py'],'dbcan':['functionalAnnotation/dbcan.py'],'vogdb':['functionalAnnotation/vogdb.py'],'dramv':['functionalAnnotation/dramv.py','viromics/dramv_distill_votu.py'],'lcastar':['metagenomics/taxonomy/lcastar_contig_taxonomy.py'],'pilercr':['functionalAnnotation/bakta_noncoding.py'],'krona':['metagenomics/taxonomy/metabuli.py']}
    if tool in OV: trs=['src/metasmith_libraries/transforms/'+x for x in OV[tool]]
    shown=trs[:4]
    st='; '.join(shown)+(f' (+{len(trs)-4} more)' if len(trs)>4 else '')
    rows.append((tool,dom,'; '.join(refs),n,st,notes))
# flag unmapped census keys
allk=set(rel)|set(unm)|{k for d in projs.values() for k in d}
print('unused census keys:',sorted(allk-used))
with open('/home/tony/agentic_workspace/projects/metasmith/aggregate/docs/aggregate/harvest.tsv','w') as f:
    f.write('tool\tdomain\tevidence\tn_sources\tstd_transform\tnotes\n')
    for r in sorted(rows,key=lambda r:(r[1],r[0])):
        f.write('\t'.join(str(x).replace('\t',' ') for x in r)+'\n')
print(len(rows))
