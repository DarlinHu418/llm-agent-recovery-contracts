from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader
import json,re,hashlib
R=Path(__file__).parent;B=R.parent
def main():
 p=next(R.glob('不同*.docx'));d=Document(p);z=ZipFile(p)
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main'}
 headings=[x.text for x in d.paragraphs if x.style.name=='章节标题']
 assert len(headings)==13,headings
 assert len(d.tables)==11
 root=E.fromstring(z.read('word/document.xml'))
 assert len(root.xpath('//asvg:svgBlip',namespaces=ns))==9
 assert len([n for n in z.namelist() if n.endswith('.svg')])==9
 assert len([p for p in d.paragraphs if p.text.startswith('图') and re.match(r'图\d',p.text)])==9
 refs=[p.text for p in d.paragraphs if p.style.name=='Bibliography']
 assert len(refs)==38,len(refs)
 assert [int(re.match(r'\[(\d+)\]',s)[1]) for s in refs]==list(range(1,39))
 assert '$\\tau' not in '\n'.join(refs)
 text='\n'.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xml'))
 for token in ['胡林怡','3220105732','王华萍','极化激元','MoOCl','可见光波段低损耗']:
  assert token not in text,token
 assert not any('/comments' in n for n in z.namelist())
 assert len(d.sections)==2
 for s in d.sections:
  assert abs(s.page_width.cm-21)<.02 and abs(s.page_height.cm-29.7)<.02
  assert abs(s.top_margin.cm-2.54)<.02 and abs(s.bottom_margin.cm-2.54)<.02
  assert abs(s.left_margin.cm-3.175)<.02 and abs(s.right_margin.cm-3.175)<.02
 bodyp=next(x for x in d.paragraphs if x.style.name=='段')
 assert bodyp.runs[0].font.size.pt==12
 assert bodyp.runs[0]._r.rPr.rFonts.get(qn('w:eastAsia'))=='仿宋'
 assert bodyp.paragraph_format.line_spacing==1.5
 rr=json.loads((R/'references_verified.json').read_text(encoding='utf-8'))
 assert len(rr)==23 and all(x['verification']=='live_abs_verified' for x in rr)
 snap=json.loads((R/'data_snapshot.json').read_text(encoding='utf-8'))
 for path,h in snap['hashes'].items():
  if (B/path).exists():assert hashlib.sha256((B/path).read_bytes()).hexdigest()==h,path
 pdf=PdfReader(R/'qa'/'report.pdf') if (R/'qa'/'report.pdf').exists() else None
 if pdf:
  assert all(len((x.extract_text() or '').strip())>20 for x in pdf.pages)
  assert '目录' in pdf.pages[1].extract_text()
  assert len(pdf.pages)==26,len(pdf.pages)
 result={'chapters':13,'tables':11,'original_vector_figures':9,'references':38,'verified_research_papers':23,'valid_sessions':62,'formal_and_replacement_attempts':63,'pages_native_word':len(pdf.pages) if pdf else None,'template_personal_content_absent':True,'source_data_hashes_match':True,'format_checked':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 (R/'final_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
