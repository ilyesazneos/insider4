"""Shared, dependency-free infrastructure for INSIDER4 audit commands."""
import fnmatch, os, zipfile
from pathlib import Path
from xml.sax.saxutils import escape
EXCLUDED_DIRS={'.git','.hg','.svn','.venv','venv','env','virtualenv','node_modules','vendor','vendors','third_party','dist','build','target','out','.next','.nuxt','.vite','.turbo','coverage','htmlcov','.cache','cache','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','generated','gen','tmp','temp','logs','log','backups','backup','uploads','upload','media','storage','.idea','.vscode','reports'}
EXCLUDED_GLOBS={'.env','.env.*','*.pem','*.key','*.crt','*.cer','*.p12','*.pfx','*credentials*','*secret*','*.pyc','*.pyo','*.class','*.o','*.so','*.dll','*.dylib','*.min.js','*.min.css','*.map','*.lock','*.log','*.tmp','*.bak','*.backup','*.old','*.orig','*.sqlite*','*.db','*.dump','*.zip','*.tar*','*.tgz','*.7z','*.rar','*.gz','*.png','*.jpg','*.jpeg','*.gif','*.webp','*.ico','*.pdf','*.mp3','*.wav','*.mp4','*.mov','*.webm'}
def iter_text_files(root,max_bytes=2*1024*1024):
 root=Path(root).resolve(); stats={'scanned_files':0,'excluded_files':0,'excluded_dirs':0,'binary_files':0,'oversized_files':0}
 for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
  base=Path(base);keep=[]
  for name in sorted(dirs):
   p=base/name
   if name.lower() in EXCLUDED_DIRS or (name.startswith('.') and name!='.github') or p.is_symlink():stats['excluded_dirs']+=1
   else:keep.append(name)
  dirs[:]=keep
  for name in sorted(files):
   p=base/name;low=name.lower()
   if p.is_symlink() or any(fnmatch.fnmatch(low,g) for g in EXCLUDED_GLOBS):stats['excluded_files']+=1;continue
   try:
    if p.stat().st_size>max_bytes:stats['oversized_files']+=1;continue
    raw=p.read_bytes()
    if b'\0' in raw[:8192]:stats['binary_files']+=1;continue
    text=raw.decode('utf-8')
   except (OSError,UnicodeDecodeError):stats['binary_files']+=1;continue
   stats['scanned_files']+=1;yield p,text,stats
def md(v):return str(v).replace('|','\\|').replace('\n',' ')
def write_xlsx(path,sheets):
 def col(n):
  s=''
  while n:n,r=divmod(n-1,26);s=chr(65+r)+s
  return s
 def sheet(headers,rows):
  xml=[]
  for rn,row in enumerate([headers]+rows,1):
   cells=[]
   for cn,v in enumerate(row,1):
    clean=''.join(c for c in str(v) if c in '\t\n\r' or ord(c)>=32);style=' s="1"' if rn==1 else ''
    cells.append(f'<c r="{col(cn)}{rn}" t="inlineStr"{style}><is><t xml:space="preserve">{escape(clean)}</t></is></c>')
   xml.append(f'<row r="{rn}">{"".join(cells)}</row>')
  return '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(xml)+'</sheetData></worksheet>'
 types='<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))+'</Types>'
 wb='<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i,(n,_,_) in enumerate(sheets,1))+'</sheets></workbook>'
 rels='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'</Relationships>';pkg='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',pkg);z.writestr('xl/workbook.xml',wb);z.writestr('xl/_rels/workbook.xml.rels',rels)
  for i,(_,h,r) in enumerate(sheets,1):z.writestr(f'xl/worksheets/sheet{i}.xml',sheet(h,r))
