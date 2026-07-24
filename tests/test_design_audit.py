import json, subprocess, tempfile, unittest, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
CLI=Path(__file__).resolve().parents[1]/'insider4'
class AuditTests(unittest.TestCase):
 def test_reports_inventory_exclusions_and_sheets(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'src').mkdir();(p/'src/ui.py').write_text('COLOR="#ff0000"\nprint("Success: saved")\nprint("Warning: careful")\nprint("Error: invalid")\nprint("✓ ready")\nanswer=input("Are you sure? [y/n]")\nprint("====")\n');(p/'README.md').write_text('# Title\n\n## Section\n');(p/'node_modules').mkdir();(p/'node_modules/x.js').write_text('print("Error: dependency")');(p/'.env').write_text('PASSWORD=secret');(p/'bin.dat').write_bytes(b'\0Error')
   r=subprocess.run([str(CLI),'design-audit'],cwd=p,text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
   out=p/'reports';self.assertTrue(all((out/f'design-audit.{x}').is_file() for x in ('json','md','xlsx')))
   data=json.loads((out/'design-audit.json').read_text());cats={x['category'] for x in data['inventory']};self.assertTrue({'colors_and_ansi','symbols_and_icons','headings_and_separators','spacing_patterns','messages','interactive_prompts'}<=cats);self.assertNotIn('dependency',json.dumps(data));self.assertNotIn('PASSWORD',json.dumps(data))
   with zipfile.ZipFile(out/'design-audit.xlsx') as z:
    root=ET.fromstring(z.read('xl/workbook.xml'));ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};self.assertEqual([x.attrib['name'] for x in root.findall('.//x:sheet',ns)],['Inventory','Inconsistencies','Design Tokens','Recommendations'])
 def test_explicit_and_missing_paths(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);r=subprocess.run([str(CLI),'design-audit',str(p)],text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr);r=subprocess.run([str(CLI),'design-audit',str(p/'missing')],text=True,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertIn('Project directory not found',r.stderr)
if __name__=='__main__':unittest.main()
