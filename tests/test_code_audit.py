import json,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
CLI=Path(__file__).resolve().parents[1]/'insider4'
class CodeAuditTests(unittest.TestCase):
 def fixture(self,p):
  (p/'app.py').write_text('''import os\nimport unused_module\ndef risky(value):\n    unused = 1\n    for item in value:\n        os.system("echo " + item)\n        Path("x").read_text()\n    try:\n        return value\n        print("dead")\n    except Exception:\n        pass\n''')
  (p/'copy.py').write_text('''def duplicate_a(x):\n    total = 0\n    total += x\n    total += 2\n    total += 3\n    total += 4\n    return total\n\ndef duplicate_b(x):\n    total = 0\n    total += x\n    total += 2\n    total += 3\n    total += 4\n    return total\n''')
 def run_audit(self,p,*extra):return subprocess.run([str(CLI),'code-audit',*extra],cwd=p,text=True,capture_output=True)
 def test_outputs_schema_rules_stability_and_sheets(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p);r=self.run_audit(p);self.assertEqual(r.returncode,0,r.stderr);out=p/'reports';self.assertTrue(all((out/f'code-audit.{x}').exists() for x in ('json','md','xlsx')));data=json.loads((out/'code-audit.json').read_text());required={'id','severity','confidence','classification','category','file','line_start','line_end','explanation','evidence','recommended_action','manual_review_required','automated_testing_required','benchmarking_required'};self.assertTrue(all(required<=set(x) for x in data['findings']));self.assertTrue(any(x['classification']=='confirmed' for x in data['findings']));self.assertTrue(any(x['benchmarking_required'] for x in data['performance_risks']));ids=[x['id'] for x in data['findings']];self.assertEqual(self.run_audit(p).returncode,0);self.assertEqual(ids,[x['id'] for x in json.loads((out/'code-audit.json').read_text())['findings']])
   with zipfile.ZipFile(out/'code-audit.xlsx') as z:
    root=ET.fromstring(z.read('xl/workbook.xml'));ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};self.assertEqual([x.attrib['name'] for x in root.findall('.//x:sheet',ns)],['Summary','Findings','Duplicates','Complexity','Performance Risks','Recommendations'])
 def test_exclusions_and_report_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p);(p/'node_modules').mkdir();(p/'node_modules/x.py').write_text('eval(secret)');(p/'.env').write_text('PASSWORD=secret');self.assertEqual(self.run_audit(p).returncode,0);data=(p/'reports/code-audit.json').read_text();self.assertNotIn('node_modules/x.py',data);self.assertNotIn('PASSWORD=secret',data);dr=subprocess.run([str(CLI),'design-audit',str(p)],text=True,capture_output=True);self.assertEqual(dr.returncode,0,dr.stderr);design=(p/'reports/design-audit.json').read_text();self.assertNotIn('code-audit.json',design)
 def test_invalid_path(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.run_audit(Path(d),str(Path(d)/'missing'));self.assertNotEqual(r.returncode,0);self.assertIn('Project directory not found',r.stderr)
if __name__=='__main__':unittest.main()
