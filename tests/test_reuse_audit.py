import json,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
CLI=Path(__file__).resolve().parents[1]/'insider4'
class ReuseAuditTests(unittest.TestCase):
 def fixture(self,p):
  (p/'a.py').write_text('''DEFAULT_TIMEOUT = 30\ndef save_report(path, data):\n    path.parent.mkdir(exist_ok=True)\n    payload = str(data)\n    path.write_text(payload)\n    print("saved", path)\n    return path\n\ndef local_workflow(path, data):\n    try:\n        path.parent.mkdir(exist_ok=True)\n        payload = str(data)\n        path.write_text(payload)\n        print("saved", path)\n        return path\n    except ValueError:\n        return None\n''')
  (p/'b.py').write_text('''DEFAULT_TIMEOUT = 30\ndef write_report(target, content):\n    target.parent.mkdir(exist_ok=True)\n    payload = str(content)\n    target.write_text(payload)\n    print("saved", target)\n    return target\n\ndef remote_workflow(target, content):\n    target.parent.mkdir(exist_ok=True)\n    payload = str(content)\n    target.write_text(payload)\n    print("saved", target)\n    raise RuntimeError("remote failed")\n''')
  (p/'c.py').write_text('''def save_report(path, data):\n    path.parent.mkdir(exist_ok=True)\n    payload = str(data)\n    path.write_text(payload)\n    print("saved", path)\n    return path\n''')
 def run_audit(self,p,*args):return subprocess.run([str(CLI),'reuse-audit',*args],cwd=p,text=True,capture_output=True)
 def test_reports_schema_actions_stability_and_sheets(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p);r=self.run_audit(p);self.assertEqual(r.returncode,0,r.stderr);out=p/'reports';self.assertTrue(all((out/f'reuse-audit.{x}').exists() for x in ('json','md','xlsx')));data=json.loads((out/'reuse-audit.json').read_text());self.assertTrue(data['shared_candidates']);required={'id','confidence','risk','classification','recommended_action','duplication_type','similarity','locations','shared_behavior','important_differences','dependencies','side_effects','proposed_abstraction','maintainability_benefit','behavior_breakage_risk','required_tests','workflow_impact'};self.assertTrue(all(required<=set(x) for x in data['shared_candidates']));self.assertTrue({'extract','review','keep separate'} <= {x['recommended_action'] for x in data['shared_candidates']});ids=[x['id'] for x in data['shared_candidates']];self.assertEqual(self.run_audit(p).returncode,0);self.assertEqual(ids,[x['id'] for x in json.loads((out/'reuse-audit.json').read_text())['shared_candidates']])
   with zipfile.ZipFile(out/'reuse-audit.xlsx') as z:
    root=ET.fromstring(z.read('xl/workbook.xml'));ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};self.assertEqual([x.attrib['name'] for x in root.findall('.//x:sheet',ns)],['Summary','Duplicate Groups','Shared Candidates','Behavior Differences','Workflow Risks','Recommendations'])
 def test_exclusions_and_all_commands(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);self.fixture(p);(p/'node_modules').mkdir();(p/'node_modules/x.py').write_text('def copied():\n return "secret"\n');(p/'.env').write_text('PASSWORD=secret');self.assertEqual(self.run_audit(p).returncode,0);raw=(p/'reports/reuse-audit.json').read_text();self.assertNotIn('node_modules/x.py',raw);self.assertNotIn('PASSWORD=secret',raw)
   for cmd in ('design-audit','code-audit'):
    r=subprocess.run([str(CLI),cmd,str(p)],text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
   reuse=(p/'reports/reuse-audit.json').read_text();self.assertNotIn('design-audit.json',reuse);self.assertNotIn('code-audit.json',reuse)
 def test_invalid_path(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.run_audit(Path(d),str(Path(d)/'missing'));self.assertNotEqual(r.returncode,0);self.assertIn('Project directory not found',r.stderr)
if __name__=='__main__':unittest.main()
