#!/usr/bin/env python3
import collections,datetime,fnmatch,json,os,re,sys,zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from audit_common import md as md_escape
D={'.git','.venv','venv','env','node_modules','vendor','dist','build','target','.next','.nuxt','.cache','cache','__pycache__','.pytest_cache','coverage','generated','tmp','logs','backups','uploads','media','reports','.idea','.vscode'}
G={'.env','.env.*','*.pem','*.key','*.crt','*credentials*','*secret*','*.lock','*.min.js','*.min.css','*.map','*.pyc','*.log','*.db','*.sqlite*','*.zip','*.tar*','*.png','*.jpg','*.gif','*.pdf','*.mp*','design-audit.*'}
C=[('hex',re.compile(r'(?<![\w#])#(?:[\da-fA-F]{3,4}|[\da-fA-F]{6}|[\da-fA-F]{8})(?![\da-fA-F])')),('rgb',re.compile(r'\brgba?\([^)]{3,80}\)',re.I)),('hsl',re.compile(r'\bhsla?\([^)]{3,80}\)',re.I)),('ansi',re.compile(r'(?:\\033|\\e|\\x1b)\[[\d;]*m'))]
MSG=re.compile(r'(?:echo|printf|print|console\.(?:log|warn|error)|fail)\s*(?:\(|\s)\s*[fr]?["\']([^"\'\n]+)',re.I)
PROMPT=re.compile(r'(?:read\s+[^\n]*?-p\s+|input\s*\(|prompt\s*\(|confirm\s*\()["\']([^"\']+)',re.I)
def kind(s):
 s=s.lower()
 if any(x in s for x in ('sure','confirm','continue?','proceed?','[y/n]','yes/no')): return 'confirmation'
 for k,p in [('error',r'error|fail|fatal|invalid|missing|cannot'),('warning',r'warn|caution|deprecated'),('success',r'success|done|complete|saved|created|updated|\bok\b')]:
  if re.search(p,s): return k
def audit(root):
 root=Path(root).expanduser().resolve()
 if not root.is_dir(): raise ValueError(f'Project directory not found: {root}')
 out=root/'reports';out.mkdir(exist_ok=True); inv=[];stats=collections.Counter()
 def add(cat,sub,val,p,n,line=''):
  inv.append({'category':cat,'subtype':sub,'value':' '.join(val.split())[:300],'file':p.relative_to(root).as_posix(),'line':n,'context':line.strip()[:220]})
 for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
  dirs[:]=[x for x in sorted(dirs) if x not in D and not x.startswith('.') and not (Path(base)/x).is_symlink()]
  for name in sorted(files):
   p=Path(base)/name; low=name.lower()
   if p.is_symlink() or any(fnmatch.fnmatch(low,g) for g in G): stats['excluded_files']+=1;continue
   try:
    if p.stat().st_size>2097152: stats['oversized_files']+=1;continue
    raw=p.read_bytes()
    if b'\0' in raw[:8192]: stats['binary_files']+=1;continue
    text=raw.decode()
   except (OSError,UnicodeDecodeError): stats['binary_files']+=1;continue
   stats['scanned_files']+=1;inds=collections.Counter();blanks=[];blank=0
   for n,line in enumerate(text.splitlines(),1):
    if not line.strip():blank+=1;continue
    if blank:blanks.append(blank);blank=0
    lead=line[:len(line)-len(line.lstrip())]
    if lead:inds['tabs' if '\t' in lead else f'{len(lead)} spaces']+=1
    for sub,pat in C:
     for m in pat.finditer(line):add('colors_and_ansi',sub,m.group(),p,n,line)
    icons=''.join(dict.fromkeys(c for c in line if ord(c)>127 and not c.isalnum() and not c.isspace()))
    if icons:add('symbols_and_icons','unicode_symbol',icons,p,n,line)
    for m in re.finditer(r'\b(?:fa|mdi|lucide)-[\w-]+|<[A-Z]\w*Icon\b',line):add('symbols_and_icons','icon_reference',m.group(),p,n,line)
    s=line.strip()
    if p.suffix.lower()=='.md' and re.match(r'^#{1,6}\s',s):a,b=s.split(maxsplit=1);add('headings_and_separators',f'heading_h{len(a)}',b,p,n,line)
    for m in re.finditer(r'(?<!\w)([-=_*#~─━═]{3,})(?!\w)',line):add('headings_and_separators','separator',m.group(1),p,n,line)
    for m in MSG.finditer(line):
     k=kind(m.group(1))
     if k:add('messages',k,m.group(1),p,n,line)
    for m in PROMPT.finditer(line):add('interactive_prompts','confirmation_prompt' if kind(m.group(1))=='confirmation' else 'interactive_prompt',m.group(1),p,n,line)
   for x,c in inds.items():add('spacing_patterns','indentation',f'{x} ({c} lines)',p,0)
   for x,c in collections.Counter(blanks).items():add('spacing_patterns','blank_line_run',f'{x} blank line(s) ({c} occurrences)',p,0)
 inv.sort(key=lambda r:(r['category'],r['subtype'],r['file'],r['line']))
 distinct=lambda cat:{r['value'].lower() for r in inv if r['category']==cat}
 issues=[]
 for area,cat,limit in [('Colors','colors_and_ansi',8),('Icons','symbols_and_icons',6),('Separators','headings_and_separators',12)]:
  vals=distinct(cat)
  if len(vals)>limit:issues.append({'area':area,'severity':'medium','issue':f'Many distinct {area.lower()} are used','evidence':f'{len(vals)} distinct values'})
 tokens=[]
 for i,v in enumerate(sorted(distinct('colors_and_ansi'))[:12],1):tokens.append({'token':f'color-{i:02d}','category':'color/style','value':v,'rationale':'Observed value; rename by semantic purpose.'})
 recs=[{'priority':'high','area':'Messages','recommendation':'Standardize status and confirmation templates.','reason':'Consistent tone and next steps improve comprehension.'},{'priority':'medium','area':'Design system','recommendation':'Document semantic colors, symbols, separators, and spacing.','reason':'Shared tokens reduce interface drift.'}]
 now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat();doc={'schema_version':1,'generated_at':now,'project':root.name,'scan':{'root':str(root),**stats},'summary':{'inventory_items':len(inv),'inconsistencies':len(issues),'design_tokens':len(tokens),'recommendations':len(recs)},'inventory':inv,'inconsistencies':issues,'design_tokens':tokens,'recommendations':recs}
 (out/'design-audit.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n')
 md=['# Design Audit','',f'Generated: {now}','','## Inventory','','| Category | Type | Value | Source |','|---|---|---|---|']+[f'| {r["category"]} | {r["subtype"]} | {md_escape(r["value"])} | {r["file"]}:{r["line"]} |' for r in inv]
 for title,rows,keys in [('Inconsistencies',issues,('area','severity','issue','evidence')),('Design Tokens',tokens,('token','category','value','rationale')),('Recommendations',recs,('priority','area','recommendation','reason'))]:md+=['',f'## {title}','','| '+' | '.join(keys)+' |','|---|---|---|---|']+['| '+' | '.join(md_escape(r[k]) for k in keys)+' |' for r in rows]
 (out/'design-audit.md').write_text('\n'.join(md)+'\n');xlsx(out/'design-audit.xlsx',inv,issues,tokens,recs);return doc
def xlsx(path,inv,issues,tokens,recs):
 sheets=[('Inventory',('category','subtype','value','file','line','context'),inv),('Inconsistencies',('area','severity','issue','evidence'),issues),('Design Tokens',('token','category','value','rationale'),tokens),('Recommendations',('priority','area','recommendation','reason'),recs)]
 def sx(keys,rows):
  lines=[]
  for i,row in enumerate([dict(zip(keys,[k.title() for k in keys]))]+rows,1):lines.append('<row>'+''.join(f'<c t="inlineStr"><is><t>{escape(str(row[k]))}</t></is></c>' for k in keys)+'</row>')
  return '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(lines)+'</sheetData></worksheet>'
 types='<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,5))+'</Types>'
 wb='<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i,(n,_,_) in enumerate(sheets,1))+'</sheets></workbook>';rels='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,5))+'</Relationships>';pkg='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',pkg);z.writestr('xl/workbook.xml',wb);z.writestr('xl/_rels/workbook.xml.rels',rels)
  for i,(_,keys,rows) in enumerate(sheets,1):z.writestr(f'xl/worksheets/sheet{i}.xml',sx(keys,rows))
if __name__=='__main__':
 try:d=audit(sys.argv[1] if len(sys.argv)>1 else '.')
 except ValueError as e:print(f'[insider4] Error: {e}',file=sys.stderr);sys.exit(1)
 print(f'[insider4] Design audit complete: {d["scan"]["root"]}')
