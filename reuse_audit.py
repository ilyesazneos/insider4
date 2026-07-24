#!/usr/bin/env python3
"""Conservative reuse audit; reports candidates but never refactors code."""
import ast,collections,datetime,difflib,hashlib,json,re,sys
from pathlib import Path
from audit_common import iter_text_files,md,write_xlsx
LIMITS={'minimum_lines':4,'near_similarity':0.78,'extract_similarity':0.92,'maximum_comparisons':50000}
LIMITATIONS=['Similarity does not prove shared responsibility or developer intent.','Dynamic dispatch, frameworks, templates, and external callers may hide behavioral dependencies.','Small duplication can be clearer than an abstraction.','Recommendations require the listed regression tests before refactoring.']
def sid(kind,locations,shared):
 key=kind+'|'+'|'.join(sorted(f'{x["file"]}:{x["line_start"]}-{x["line_end"]}' for x in locations))+'|'+' '.join(shared.split())
 return 'RA-'+hashlib.sha256(key.encode()).hexdigest()[:12].upper()
def norm(text,literals=False):
 text=re.sub(r'(?m)^\s*(#|//).*?$','',text);text=re.sub(r'\s+',' ',text).strip()
 if literals:text=re.sub(r'(["\']).*?\1|\b\d+(?:\.\d+)?\b','LITERAL',text)
 return text
def audit(root):
 root=Path(root).expanduser().resolve()
 if not root.is_dir():raise ValueError(f'Project directory not found: {root}')
 out=root/'reports';out.mkdir(exist_ok=True);units=[];constants=collections.defaultdict(list);languages=collections.Counter();stats={}
 def operations(text):
  pats={'validation':r'\b(?:validate|invalid|raise|assert|isinstance|exists)\b','formatting':r'\b(?:format|json\.dumps|join|escape|render|markdown)\b','error_handling':r'\b(?:except|catch|fail|stderr|return\s+1|raise)\b','filesystem':r'\b(?:Path|open|read_text|write_text|read_bytes|write_bytes|mkdir|stat|glob|os\.walk)\b','subprocess':r'\b(?:subprocess|os\.system|exec|spawn|curl|wget|ssh)\b','reporting':r'\b(?:report|xlsx|json|markdown|worksheet|write_xlsx)\b'}
  return sorted(k for k,p in pats.items() if re.search(p,text,re.I))
 def sidefx(text):return sorted(k for k,p in {'filesystem_write':r'write_text|write_bytes|open\([^\n]*["\'](?:w|a)','subprocess':r'subprocess|os\.system|\bexec\b','network':r'requests\.|urlopen|socket|curl|wget|ssh','stdout':r'\bprint\s*\(|\becho\b','environment':r'os\.environ|export\s+','exit':r'raise SystemExit|sys\.exit|\bexit\b'}.items() if re.search(p,text,re.I))
 def addunit(rel,name,start,end,text,kind,params='',returns=False,errors=()):units.append({'file':rel,'symbol':name,'line_start':start,'line_end':end,'kind':kind,'text':text,'normalized':norm(text),'structural':norm(text,True),'operations':operations(text),'side_effects':sidefx(text),'dependencies':sorted(set(re.findall(r'\b([A-Za-z_]\w*)\s*\(',text))-{name}),'params':params,'returns':returns,'errors':sorted(set(errors))})
 for p,text,stats in iter_text_files(root):
  rel=p.relative_to(root).as_posix();ext=p.suffix.lower();languages[ext or '[none]']+=1;lines=text.splitlines()
  for no,line in enumerate(lines,1):
   m=re.match(r'\s*([A-Z][A-Z0-9_]{2,})\s*=\s*(.+)',line)
   if m and not re.search(r'(?:KEY|TOKEN|PASSWORD|SECRET)',m.group(1),re.I):constants[norm(m.group(2),True)].append({'file':rel,'line_start':no,'line_end':no,'name':m.group(1),'value':m.group(2)[:120]})
  meaningful=[(i+1,x) for i,x in enumerate(lines) if x.strip() and not x.lstrip().startswith(('#','//'))]
  for pos in range(0,max(0,len(meaningful)-5),6):
   chunk=meaningful[pos:pos+6]
   if len(chunk)==6:addunit(rel,f'block_{chunk[0][0]}',chunk[0][0],chunk[-1][0],'\n'.join(x[1] for x in chunk),'code_block')
  if ext=='.py':
   try:tree=ast.parse(text)
   except SyntaxError:continue
   for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
     end=getattr(n,'end_lineno',n.lineno);body='\n'.join(lines[n.lineno-1:end]);errors=[ast.unparse(x.type) if x.type else 'bare' for x in ast.walk(n) if isinstance(x,ast.ExceptHandler)];addunit(rel,n.name,n.lineno,end,body,'function',','.join(a.arg for a in n.args.args),any(isinstance(x,ast.Return) for x in ast.walk(n)),errors)
  else:
   starts=[]
   for i,line in enumerate(lines):
    m=re.match(r'\s*(?:function\s+)?([A-Za-z_]\w*)\s*(?:\(.*?\))?\s*\{\s*$',line)
    if m:starts.append((i,m.group(1)))
   for i,name in starts:
    depth=0;end=i
    for j in range(i,len(lines)):
     depth+=lines[j].count('{')-lines[j].count('}');end=j
     if j>i and depth<=0:break
    addunit(rel,name,i+1,end+1,'\n'.join(lines[i:end+1]),'function')
 groups=[];seen=set();comparisons=0
 for i,a in enumerate(units):
  if a['line_end']-a['line_start']+1<LIMITS['minimum_lines']:continue
  for b in units[i+1:]:
   if comparisons>=LIMITS['maximum_comparisons']:break
   comparisons+=1
   if a['file']==b['file'] and a['line_start']==b['line_start']:continue
   length_ratio=min(len(a['structural']),len(b['structural']))/max(1,max(len(a['structural']),len(b['structural'])))
   if length_ratio<.55:continue
   exact=a['normalized']==b['normalized'];score=1.0 if exact else difflib.SequenceMatcher(None,a['structural'],b['structural'],autojunk=False).ratio()
   shared_ops=sorted(set(a['operations'])&set(b['operations']));responsibility=bool(shared_ops) and len(shared_ops)>=min(2,max(len(a['operations']),len(b['operations'])))
   if score<LIMITS['near_similarity'] and not (responsibility and score>=.62):continue
   locations=[{k:a[k] for k in ('file','line_start','line_end','symbol')},{k:b[k] for k in ('file','line_start','line_end','symbol')}];dtype='exact_code' if exact else ('similar_responsibility' if responsibility and score<.78 else 'near_duplicate')
   differences=[]
   if a['params']!=b['params']:differences.append(f'Parameters differ: {a["params"] or "none"} vs {b["params"] or "none"}.')
   if a['returns']!=b['returns']:differences.append('Return behavior differs.')
   if a['errors']!=b['errors']:differences.append(f'Error handling differs: {a["errors"]} vs {b["errors"]}.')
   onlya=sorted(set(a['operations'])-set(b['operations']));onlyb=sorted(set(b['operations'])-set(a['operations']))
   if onlya or onlyb:differences.append(f'Unique operations: first={onlya}, second={onlyb}.')
   if a['side_effects']!=b['side_effects']:differences.append(f'Side effects differ: {a["side_effects"]} vs {b["side_effects"]}.')
   risk='high' if a['side_effects']!=b['side_effects'] or a['errors']!=b['errors'] else ('medium' if differences else 'low');confidence='high' if exact else ('medium' if score>=.85 else 'low')
   if score>=LIMITS['extract_similarity'] and risk=='low' and len(a['normalized'])>120:action='extract';classification='safe_extraction'
   elif risk=='high' or score<.7:action='keep separate';classification='intentional_or_unsafe'
   else:action='review';classification='manual_review'
   shared=', '.join(shared_ops) or 'similar control and data transformation structure';gid=sid(dtype,locations,shared)
   groups.append({'id':gid,'confidence':confidence,'risk':risk,'classification':classification,'recommended_action':action,'duplication_type':dtype,'similarity':round(score,3),'locations':locations,'shared_behavior':shared,'important_differences':differences or ['No material static difference detected.'],'dependencies':sorted(set(a['dependencies'])|set(b['dependencies'])),'side_effects':sorted(set(a['side_effects'])|set(b['side_effects'])),'proposed_abstraction':f'Shared {shared_ops[0] if shared_ops else "workflow"} helper used by {a["symbol"]} and {b["symbol"]}.','maintainability_benefit':'One tested implementation would reduce synchronized edits and behavioral drift.','behavior_breakage_risk':f'{risk.title()} risk: preserve inputs, ordering, errors, returns, and side effects.','required_tests':[f'Characterization tests for {a["symbol"]} and {b["symbol"]}.','Regression tests for inputs, outputs, errors, ordering, and side effects.'],'workflow_impact':f'Both call paths would delegate shared behavior; workflow-specific wrappers should retain their current contract.','evidence':{'common_operations':shared_ops,'distinct_operations':{'first':onlya,'second':onlyb},'normalized_excerpt':a['normalized'][:240]}})
 # Repeated named constants are review candidates, never automatic extraction.
 for value,locs in constants.items():
  if len(locs)<2:continue
  locations=[{**x,'symbol':x.pop('name')} for x in [dict(y) for y in locs]];gid=sid('constant',locations,value);groups.append({'id':gid,'confidence':'high','risk':'medium','classification':'manual_review','recommended_action':'review','duplication_type':'constant_or_configuration','similarity':1.0,'locations':locations,'shared_behavior':'Repeated constant or configuration value.','important_differences':['Names and surrounding configuration scope may encode different ownership.'],'dependencies':[],'side_effects':[],'proposed_abstraction':'A shared, semantically named constant only if ownership and change cadence match.','maintainability_benefit':'Prevents inconsistent updates when the value represents one concept.','behavior_breakage_risk':'Medium risk: coupling unrelated defaults can cause unintended workflow changes.','required_tests':['Configuration default and override tests for every affected path.'],'workflow_impact':'All consumers would share one value; independent configuration would no longer drift.','evidence':{'common_operations':[],'distinct_operations':{},'normalized_excerpt':value[:240]}})
 # Deduplicate symmetric/overlapping records.
 unique={g['id']:g for g in groups};groups=sorted(unique.values(),key=lambda g:(g['recommended_action'],g['risk'],g['id']))
 differences=[];risks=[]
 for g in groups:
  for diff in g['important_differences']:
   if not diff.startswith('No material'):differences.append({'candidate_id':g['id'],'locations':'; '.join(f'{x["file"]}:{x["line_start"]}-{x["line_end"]}' for x in g['locations']),'difference':diff,'significance':'May change the abstraction contract or require a workflow-specific wrapper.','risk':g['risk']})
  if g['risk']!='low':risks.append({'candidate_id':g['id'],'affected_workflow':', '.join(x['symbol'] for x in g['locations']),'current_behavior':g['shared_behavior'],'extraction_impact':g['workflow_impact'],'breakage_risk':g['behavior_breakage_risk'],'required_tests':'; '.join(g['required_tests']),'risk':g['risk']})
 recs=[{'priority':'high' if g['recommended_action']=='extract' else 'medium','action':g['recommended_action'],'proposed_component':g['proposed_abstraction'],'candidate_ids':g['id'],'benefit':g['maintainability_benefit'],'risk':g['behavior_breakage_risk'],'prerequisite_tests':'; '.join(g['required_tests'])} for g in groups]
 counts=collections.Counter(g['recommended_action'] for g in groups);conf=collections.Counter(g['confidence'] for g in groups);riskc=collections.Counter(g['risk'] for g in groups);types=collections.Counter(g['duplication_type'] for g in groups);now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
 doc={'schema_version':1,'generated_at':now,'project':root.name,'scan':{'root':str(root),**stats,'languages':dict(languages),'thresholds':LIMITS,'limitations':LIMITATIONS,'comparisons':comparisons},'summary':{'duplicate_groups':len(groups),'shared_candidates':len(groups),'safe_extractions':counts['extract'],'manual_reviews':counts['review'],'keep_separate':counts['keep separate'],'by_confidence':dict(conf),'by_risk':dict(riskc),'by_type':dict(types)},'duplicate_groups':groups,'shared_candidates':groups,'behavior_differences':differences,'workflow_risks':risks,'recommendations':recs}
 (out/'reuse-audit.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n');write_md(out/'reuse-audit.md',doc);write_book(out/'reuse-audit.xlsx',doc);return doc
def write_md(path,d):
 lines=['# Reuse Audit','',f'Generated: {d["generated_at"]}','','`extract` means a conservative safe candidate; `review` requires manual contract comparison; `keep separate` means differences or coupling risk outweigh likely benefit. This audit never changes source code.','','## Summary','',f'- Duplicate groups: {d["summary"]["duplicate_groups"]}',f'- Safe extractions: {d["summary"]["safe_extractions"]}',f'- Manual reviews: {d["summary"]["manual_reviews"]}',f'- Keep separate: {d["summary"]["keep_separate"]}','','## Shared Candidates','','| ID | Action | Confidence | Risk | Type | Similarity | Locations | Shared behavior | Differences | Proposed abstraction | Required tests |','|---|---|---|---|---|---|---|---|---|---|---|']
 for g in d['shared_candidates']:lines.append('| '+' | '.join(md(x) for x in (g['id'],g['recommended_action'],g['confidence'],g['risk'],g['duplication_type'],g['similarity'],'; '.join(f'{x["file"]}:{x["line_start"]}-{x["line_end"]}' for x in g['locations']),g['shared_behavior'],'; '.join(g['important_differences']),g['proposed_abstraction'],'; '.join(g['required_tests'])))+' |')
 for title,key in [('Behavior Differences','behavior_differences'),('Workflow Risks','workflow_risks'),('Recommendations','recommendations')]:lines+=['',f'## {title}','',f'{len(d[key])} item(s).']
 lines+=['','## Limitations','']+['- '+x for x in d['scan']['limitations']];path.write_text('\n'.join(lines)+'\n')
def write_book(path,d):
 loc=lambda g:'; '.join(f'{x["file"]}:{x["line_start"]}-{x["line_end"]}' for x in g['locations']);groups=d['duplicate_groups']
 sheets=[('Summary',['Metric','Value'],[['Generated',d['generated_at']],['Groups',len(groups)],['Safe extractions',d['summary']['safe_extractions']],['Manual reviews',d['summary']['manual_reviews']],['Keep separate',d['summary']['keep_separate']]]),('Duplicate Groups',['ID','Type','Similarity','Confidence','Locations','Shared Behavior'],[[g['id'],g['duplication_type'],g['similarity'],g['confidence'],loc(g),g['shared_behavior']] for g in groups]),('Shared Candidates',['ID','Action','Confidence','Risk','Locations','Differences','Dependencies','Side Effects','Proposed Abstraction','Benefit','Required Tests'],[[g['id'],g['recommended_action'],g['confidence'],g['risk'],loc(g),'; '.join(g['important_differences']),', '.join(g['dependencies']),', '.join(g['side_effects']),g['proposed_abstraction'],g['maintainability_benefit'],'; '.join(g['required_tests'])] for g in groups]),('Behavior Differences',['Candidate ID','Locations','Difference','Significance','Risk'],[[x[k] for k in ('candidate_id','locations','difference','significance','risk')] for x in d['behavior_differences']]),('Workflow Risks',['Candidate ID','Affected Workflow','Current Behavior','Extraction Impact','Breakage Risk','Required Tests','Risk'],[[x[k] for k in ('candidate_id','affected_workflow','current_behavior','extraction_impact','breakage_risk','required_tests','risk')] for x in d['workflow_risks']]),('Recommendations',['Priority','Action','Proposed Component','Candidate IDs','Benefit','Risk','Prerequisite Tests'],[[x[k] for k in ('priority','action','proposed_component','candidate_ids','benefit','risk','prerequisite_tests')] for x in d['recommendations']])];write_xlsx(path,sheets)
if __name__=='__main__':
 try:d=audit(sys.argv[1] if len(sys.argv)>1 else '.')
 except ValueError as e:print(f'[insider4] Error: {e}',file=sys.stderr);raise SystemExit(1)
 print(f'[insider4] Reuse audit complete: {d["scan"]["root"]}');print(f'[insider4] Candidates: {d["summary"]["shared_candidates"]}')
