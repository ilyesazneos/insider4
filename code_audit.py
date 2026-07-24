#!/usr/bin/env python3
"""Conservative static code audit. Findings are not runtime performance proof."""
import ast,collections,datetime,difflib,hashlib,json,re,sys,tokenize,io
from pathlib import Path
from audit_common import iter_text_files,md,write_xlsx
LIMITS={'function_lines':60,'complexity':12,'nesting':4,'duplicate_lines':6}
LIMITATIONS=['Static analysis cannot prove runtime performance; performance risks require profiling or benchmarks.','Dynamic imports, reflection, framework callbacks, templates, and dependency injection may cause unused-code false positives.','Validation and error handling may occur in callers or frameworks.','Similarity, complexity, and test-coverage rules are conservative heuristics.']
def stable(rule,path,start,evidence):return 'CA-'+hashlib.sha256(f'{rule}|{path}|{start}|{" ".join(evidence.split())}'.encode()).hexdigest()[:12].upper()
def audit(root):
 root=Path(root).expanduser().resolve()
 if not root.is_dir():raise ValueError(f'Project directory not found: {root}')
 out=root/'reports';out.mkdir(exist_ok=True); findings=[];complexity=[];perf=[];blocks=[];languages=collections.Counter();stats={}
 def add(rule,severity,confidence,classification,category,path,start,end,explanation,evidence,action,review=True,test=False,bench=False):
  row={'id':stable(rule,path,start,evidence),'severity':severity,'confidence':confidence,'classification':classification,'category':category,'file':path,'line_start':start,'line_end':end,'explanation':explanation,'evidence':evidence[:500],'recommended_action':action,'manual_review_required':review,'automated_testing_required':test,'benchmarking_required':bench,'rule':rule};findings.append(row);return row
 def nesting(node,depth=0):return max([depth]+[nesting(c,depth+1 if isinstance(c,(ast.If,ast.For,ast.While,ast.Try,ast.With,ast.Match)) else depth) for c in ast.iter_child_nodes(node)])
 for p,text,stats in iter_text_files(root):
  rel=p.relative_to(root).as_posix();ext=p.suffix.lower();languages[ext or '[none]']+=1;lines=text.splitlines()
  meaningful=[(i+1,re.sub(r'\s+',' ',x.strip())) for i,x in enumerate(lines) if x.strip() and not x.lstrip().startswith(('#','//'))]
  for i in range(0,max(0,len(meaningful)-LIMITS['duplicate_lines']+1),LIMITS['duplicate_lines']):
   chunk=meaningful[i:i+LIMITS['duplicate_lines']]
   if len(chunk)==LIMITS['duplicate_lines']:blocks.append((hashlib.sha256('\n'.join(x[1] for x in chunk).encode()).hexdigest(),rel,chunk[0][0],chunk[-1][0],'\n'.join(x[1] for x in chunk)))
  for no,line in enumerate(lines,1):
   if re.search(r'(?:https?://[^\s"\']+|\b(?:PORT|TIMEOUT|RETRIES|MAX_SIZE)\s*=\s*["\']?\d+)',line,re.I) and not re.search(r'(?:example\.com|localhost|127\.0\.0\.1)',line,re.I):add('configuration.hard-coded','low','low','heuristic','configuration',rel,no,no,'A configuration-like value is hard-coded.',line.strip(),'Confirm whether this belongs in validated configuration or is an intentional constant.')
  if ext=='.py':
   try:tree=ast.parse(text)
   except SyntaxError as e:add('python.syntax','high','high','confirmed','syntax',rel,e.lineno or 1,e.lineno or 1,'Python file cannot be parsed.',str(e),'Fix the syntax error and add a regression test.',False,True);continue
   imported={a.asname or a.name.split('.')[0]:n.lineno for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names};loaded={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
   for name,no in imported.items():
    if name not in loaded:add('python.unused-import','low','medium','heuristic','unused_code',rel,no,no,f'Import {name!r} appears unused.',lines[no-1].strip(),'Remove it or document dynamic/framework usage.')
   for fn in [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]:
    end=getattr(fn,'end_lineno',fn.lineno);loc=end-fn.lineno+1;branches=sum(isinstance(n,(ast.If,ast.For,ast.While,ast.Try,ast.BoolOp,ast.IfExp,ast.Match,ast.comprehension)) for n in ast.walk(fn));cx=1+branches;nest=nesting(fn)
    complexity.append({'file':rel,'symbol':fn.name,'line_start':fn.lineno,'line_end':end,'lines':loc,'approximate_complexity':cx,'max_nesting':nest,'classification':'heuristic metric'})
    if loc>LIMITS['function_lines']:add('complexity.long-function','medium','high','heuristic','maintainability',rel,fn.lineno,end,f'Function {fn.name!r} is {loc} lines long.',f'{loc} lines; threshold {LIMITS["function_lines"]}.','Extract cohesive helpers and cover behavior with tests.',True,True)
    if cx>LIMITS['complexity']:add('complexity.branches','medium','medium','heuristic','complexity',rel,fn.lineno,end,f'Function {fn.name!r} has high approximate complexity.',f'Approximate complexity {cx}; threshold {LIMITS["complexity"]}.','Simplify branches and test each decision path.',True,True)
    if nest>LIMITS['nesting']:add('complexity.nesting','medium','high','heuristic','excessive_nesting',rel,fn.lineno,end,f'Function {fn.name!r} is deeply nested.',f'Maximum control nesting {nest}.','Use guard clauses or extract helpers.',True,True)
    assigned={n.id:n.lineno for n in ast.walk(fn) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)};used={n.id for n in ast.walk(fn) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
    for name,no in assigned.items():
     if name not in used and not name.startswith('_'):add('python.unused-variable','low','medium','heuristic','unused_code',rel,no,no,f'Variable {name!r} appears unused.',lines[no-1].strip(),'Remove it or use an underscore-prefixed intentional placeholder.')
    fs_calls=collections.Counter(ast.unparse(c) for c in ast.walk(fn) if isinstance(c,ast.Call) and re.search(r'\.(?:exists|stat|read_text|read_bytes|glob|iterdir)\(',ast.unparse(c)))
    for expression,count in fs_calls.items():
     if count>1:add('filesystem.repeated-operation','low','medium','heuristic','maintainability',rel,fn.lineno,end,'The same filesystem expression is repeated in one function.',f'{expression} occurs {count} times.','Cache the result when semantics permit and add a behavior test.',True,True)
    for parent in ast.walk(fn):
     for field in ('body','orelse','finalbody'):
      body=getattr(parent,field,[])
      for i,node in enumerate(body[:-1]):
       if isinstance(node,(ast.Return,ast.Raise,ast.Break,ast.Continue)):
        nxt=body[i+1];add('python.unreachable','medium','high','confirmed','unreachable_code',rel,nxt.lineno,getattr(nxt,'end_lineno',nxt.lineno),'Statement follows unconditional control transfer in the same block.',lines[nxt.lineno-1].strip(),'Remove unreachable code or correct the control flow.',False,True)
   for n in ast.walk(tree):
    if isinstance(n,ast.ExceptHandler) and (n.type is None or isinstance(n.type,ast.Name) and n.type.id in ('Exception','BaseException')):
     swallowed=len(n.body)==1 and isinstance(n.body[0],ast.Pass);add('python.broad-except','medium' if swallowed else 'low','high','heuristic','error_handling',rel,n.lineno,getattr(n,'end_lineno',n.lineno),'Broad exception handler may hide unrelated failures.',lines[n.lineno-1].strip(),'Catch specific exceptions and preserve diagnostic context.',True,True)
    if isinstance(n,(ast.For,ast.While)):
     for c in ast.walk(n):
      if isinstance(c,ast.Call):
       name=ast.unparse(c.func) if hasattr(ast,'unparse') else ''
       if re.search(r'(subprocess|requests|urlopen|\.read_text|\.read_bytes|\.write_text|\.glob|\.stat|\.execute)',name):
        row=add('performance.operation-in-loop','medium','medium','profiling_required','performance',rel,c.lineno,getattr(c,'end_lineno',c.lineno),'Potentially expensive operation occurs inside a loop.',name,'Measure representative workloads; batch, cache, or move invariant work if justified.',True,True,True);perf.append(row)
    if isinstance(n,ast.Call):
     name=ast.unparse(n.func) if hasattr(ast,'unparse') else ''
     if name in ('os.system','os.popen','eval','exec') or any(k.arg=='shell' and isinstance(k.value,ast.Constant) and k.value.value is True for k in n.keywords):add('security.dynamic-shell','high','high','heuristic','security',rel,n.lineno,getattr(n,'end_lineno',n.lineno),'Dynamic shell or code execution can enable command injection.',lines[n.lineno-1].strip(),'Use argument arrays and validate untrusted input.',True,True)
     if re.search(r'(requests\.|urlopen|socket\.create_connection)',name) and not any(k.arg=='timeout' for k in n.keywords):add('network.missing-timeout','medium','medium','heuristic','reliability',rel,n.lineno,getattr(n,'end_lineno',n.lineno),'Network call has no visible timeout.',lines[n.lineno-1].strip(),'Set an explicit bounded timeout and test failure behavior.',True,True)
  else:
   for no,line in enumerate(lines,1):
    if re.search(r'\beval\b|\b(?:sh|bash)\s+-c\s+["\'].*\$',line):add('shell.dynamic-command','high','medium','heuristic','security',rel,no,no,'Shell command construction may evaluate dynamic input.',line.strip(),'Avoid eval and pass validated arguments without reparsing.',True,True)
    if re.search(r'\b(curl|wget)\b',line) and not re.search(r'--max-time|--connect-timeout|-T\s',line):add('network.missing-timeout','medium','low','heuristic','reliability',rel,no,no,'Network command has no visible timeout.',line.strip(),'Set connection and total timeouts.',True,True)
 groups=collections.defaultdict(list)
 for b in blocks:groups[b[0]].append(b)
 duplicates=[]
 for digest,rows in sorted(groups.items()):
  if len(rows)>1:
   first=rows[0]
   for other in rows[1:]:
    if first[1]==other[1] and first[2]==other[2]:continue
    evidence=f'{first[1]}:{first[2]}-{first[3]} matches {other[1]}:{other[2]}-{other[3]}';fid=stable('duplicate.exact',first[1],first[2],evidence);d={'id':fid,'type':'exact','similarity':1.0,'file_a':first[1],'lines_a':f'{first[2]}-{first[3]}','file_b':other[1],'lines_b':f'{other[2]}-{other[3]}','evidence':evidence,'recommended_action':'Review whether a shared helper would reduce maintenance risk.'};duplicates.append(d);add('duplicate.exact','medium','high','confirmed','duplication',first[1],first[2],first[3],'An exact normalized code block appears elsewhere.',evidence,d['recommended_action'],True,True)
 candidates=blocks[:400]
 for i,a in enumerate(candidates):
  for b in candidates[i+1:]:
   if a[0]==b[0] or a[1]==b[1]:continue
   score=difflib.SequenceMatcher(None,a[4],b[4],autojunk=False).ratio()
   if score>=0.9:
    evidence=f'{a[1]}:{a[2]}-{a[3]} resembles {b[1]}:{b[2]}-{b[3]} ({score:.0%})';fid=stable('duplicate.similar',a[1],a[2],evidence);d={'id':fid,'type':'highly_similar','similarity':round(score,3),'file_a':a[1],'lines_a':f'{a[2]}-{a[3]}','file_b':b[1],'lines_b':f'{b[2]}-{b[3]}','evidence':evidence,'recommended_action':'Manually compare intent before extracting shared code.'};duplicates.append(d);add('duplicate.similar','low','medium','heuristic','duplication',a[1],a[2],a[3],'A normalized code block is highly similar to another block.',evidence,d['recommended_action'],True,True)
 test_files=[p for p,_,_ in iter_text_files(root) if 'test' in p.name.lower() or 'tests' in p.parts]
 source_files=[p for p,_,_ in iter_text_files(root) if p.suffix in ('.py','.js','.ts','.sh') and 'test' not in p.name.lower() and 'tests' not in p.parts]
 if source_files and not test_files:add('tests.missing','medium','high','heuristic','testing','.',1,1,'No conventional automated test files were found.',f'{len(source_files)} source files and 0 test files.','Add focused unit and CLI integration tests.',True,True)
 findings.sort(key=lambda r:(r['file'],r['line_start'],r['rule'],r['id']));perf.sort(key=lambda r:r['id']);sev=collections.Counter(r['severity'] for r in findings);conf=collections.Counter(r['confidence'] for r in findings);cat=collections.Counter(r['category'] for r in findings);cls=collections.Counter(r['classification'] for r in findings)
 recommendations=[]
 for category,count in sorted(cat.items(),key=lambda x:(-x[1],x[0])):recommendations.append({'priority':'high' if any(r['severity']=='high' and r['category']==category for r in findings) else 'medium','category':category,'recommendation':f'Address and verify {category.replace("_"," ")} findings.','rationale':f'{count} finding(s).','related_finding_ids':', '.join(r['id'] for r in findings if r['category']==category)})
 now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat();doc={'schema_version':1,'generated_at':now,'project':root.name,'scan':{'root':str(root),**stats,'languages':dict(languages),'thresholds':LIMITS,'limitations':LIMITATIONS},'summary':{'finding_count':len(findings),'by_severity':dict(sev),'by_confidence':dict(conf),'by_category':dict(cat),'confirmed':cls['confirmed'],'heuristic':cls['heuristic'],'profiling_required':cls['profiling_required']},'findings':findings,'duplicates':duplicates,'complexity':complexity,'performance_risks':perf,'recommendations':recommendations}
 (out/'code-audit.json').write_text(json.dumps(doc,indent=2)+'\n');write_md(out/'code-audit.md',doc);write_book(out/'code-audit.xlsx',doc);return doc
def write_md(path,d):
 lines=['# Code Audit','',f'Generated: {d["generated_at"]}','','Static results are classified as confirmed, heuristic, or profiling-required. Static analysis does not prove a performance problem.','','## Summary','',f'- Findings: {d["summary"]["finding_count"]}',f'- Confirmed: {d["summary"]["confirmed"]}',f'- Heuristic: {d["summary"]["heuristic"]}',f'- Profiling required: {d["summary"]["profiling_required"]}','','## Findings','','| ID | Severity | Confidence | Classification | Category | Location | Explanation | Action | Review/Test/Benchmark |','|---|---|---|---|---|---|---|---|---|']
 for r in d['findings']:lines.append('| '+' | '.join(md(x) for x in (r['id'],r['severity'],r['confidence'],r['classification'],r['category'],f'{r["file"]}:{r["line_start"]}-{r["line_end"]}',r['explanation'],r['recommended_action'],f'{r["manual_review_required"]}/{r["automated_testing_required"]}/{r["benchmarking_required"]}'))+' |')
 for title,key in [('Duplicates','duplicates'),('Complexity','complexity'),('Performance Risks','performance_risks'),('Recommendations','recommendations')]:lines+=['',f'## {title}','',f'{len(d[key])} item(s).']
 lines+=['','## Limitations','']+['- '+x for x in d['scan']['limitations']];path.write_text('\n'.join(lines)+'\n')
def write_book(path,d):
 fh=['ID','Severity','Confidence','Classification','Category','File','Line Start','Line End','Explanation','Evidence','Recommended Action','Manual Review','Automated Testing','Benchmarking'];fk=['id','severity','confidence','classification','category','file','line_start','line_end','explanation','evidence','recommended_action','manual_review_required','automated_testing_required','benchmarking_required']
 sheets=[('Summary',['Metric','Value'],[['Generated',d['generated_at']],['Findings',d['summary']['finding_count']],['Confirmed',d['summary']['confirmed']],['Heuristic',d['summary']['heuristic']],['Profiling required',d['summary']['profiling_required']]]),('Findings',fh,[[r[k] for k in fk] for r in d['findings']]),('Duplicates',['ID','Type','Similarity','File A','Lines A','File B','Lines B','Evidence','Recommended Action'],[[r[k] for k in ('id','type','similarity','file_a','lines_a','file_b','lines_b','evidence','recommended_action')] for r in d['duplicates']]),('Complexity',['File','Symbol','Line Start','Line End','Lines','Approximate Complexity','Max Nesting','Classification'],[[r[k] for k in ('file','symbol','line_start','line_end','lines','approximate_complexity','max_nesting','classification')] for r in d['complexity']]),('Performance Risks',fh,[[r[k] for k in fk] for r in d['performance_risks']]),('Recommendations',['Priority','Category','Recommendation','Rationale','Related Finding IDs'],[[r[k] for k in ('priority','category','recommendation','rationale','related_finding_ids')] for r in d['recommendations']])];write_xlsx(path,sheets)
if __name__=='__main__':
 try:d=audit(sys.argv[1] if len(sys.argv)>1 else '.')
 except ValueError as e:print(f'[insider4] Error: {e}',file=sys.stderr);raise SystemExit(1)
 print(f'[insider4] Code audit complete: {d["scan"]["root"]}');print(f'[insider4] Findings: {d["summary"]["finding_count"]}')
