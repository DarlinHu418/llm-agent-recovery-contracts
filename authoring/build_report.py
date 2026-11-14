from pathlib import Path
from copy import deepcopy
import json,hashlib,re
from lxml import etree
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.part import Part
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from manuscript import SECTIONS
R=Path(__file__).parent
TITLE='不同工具契约下 LLM Agent 非幂等操作失败恢复的决策边界研究'
SHORT='LLM Agent 非幂等操作失败恢复的决策边界'

def setfont(run,size=12,east='仿宋',bold=None):
    run.font.name='Times New Roman';run.font.size=Pt(size);run.font.color.rgb=RGBColor(0,0,0)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'),east)
    if bold is not None:run.bold=bold

def field(par,code):
    r=par.add_run();begin=OxmlElement('w:fldChar');begin.set(qn('w:fldCharType'),'begin');r._r.append(begin)
    x=OxmlElement('w:instrText');x.set(qn('xml:space'),'preserve');x.text=' '+code+' ';r._r.append(x)
    sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    par.add_run(' ')
    r=par.add_run();end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end');r._r.append(end)

def roman_front_page(par):
    par.clear();par.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=par.add_run();b=OxmlElement('w:fldChar');b.set(qn('w:fldCharType'),'begin');r._r.append(b)
    t=OxmlElement('w:instrText');t.set(qn('xml:space'),'preserve');t.text=' = ';r._r.append(t)
    field(par,'PAGE')
    r=par.add_run();t=OxmlElement('w:instrText');t.set(qn('xml:space'),'preserve');t.text=' - 1 \\* ROMAN ';r._r.append(t)
    s=OxmlElement('w:fldChar');s.set(qn('w:fldCharType'),'separate');r._r.append(s);par.add_run('I')
    r=par.add_run();e=OxmlElement('w:fldChar');e.set(qn('w:fldCharType'),'end');r._r.append(e)

def pageprops(section,number=None):
    section.start_type=WD_SECTION_START.NEW_PAGE
    section.different_first_page_header_footer=False
    for obj in [section.header,section.even_page_header,section.footer,section.even_page_footer,section.first_page_header,section.first_page_footer]:obj.is_linked_to_previous=False
    for obj in [section.header,section.even_page_header,section.footer,section.even_page_footer,section.first_page_header,section.first_page_footer]:
        for par in obj.paragraphs:par.clear()
    for old in list(section._sectPr.findall(qn('w:pgNumType'))):section._sectPr.remove(old)
    if number:
        for obj,text,align in [(section.header,SHORT,WD_ALIGN_PARAGRAPH.RIGHT),(section.even_page_header,'浙江大学课程大作业研究报告',WD_ALIGN_PARAGRAPH.LEFT),(section.first_page_header,SHORT,WD_ALIGN_PARAGRAPH.RIGHT)]:
            par=obj.paragraphs[0];par.alignment=align;setfont(par.add_run(text),9,'仿宋')
            pr=par._p.get_or_add_pPr();b=OxmlElement('w:pBdr');bottom=OxmlElement('w:bottom');bottom.set(qn('w:val'),'single');bottom.set(qn('w:sz'),'4');bottom.set(qn('w:color'),'000000');b.append(bottom);pr.append(b)
        for obj in [section.footer,section.even_page_footer,section.first_page_footer]:
            par=obj.paragraphs[0];par.alignment=WD_ALIGN_PARAGRAPH.CENTER;field(par,'PAGE')
        n=OxmlElement('w:pgNumType');n.set(qn('w:fmt'),number);n.set(qn('w:start'),'1');section._sectPr.append(n)

def references():
    records=json.loads((R/'references_verified.json').read_text(encoding='utf-8'));refs=[]
    formal={7:'正式记录 PVLDB 18(12):4874–4886, 2025. DOI:10.14778/3750601.3750611',11:'正式记录 ICSE 2026:2938–2950. DOI:10.1145/3744916.3764546',15:'正式记录 ICML 2025, PMLR 267:63897–63911. https://proceedings.mlr.press/v267/wang25bx.html',19:'正式记录 Findings of NAACL 2025:1160–1183. DOI:10.18653/v1/2025.findings-naacl.65',22:'另有NeurIPS 2023正式记录；此处固定所读arXiv版本'}
    for i,r in enumerate(records,1):
        authors=r.get('live_authors',r.get('authors_read_version',[]));names='; '.join(authors[:3])+('; et al.' if len(authors)>3 else '')
        title=r.get('live_title',r['title']).replace('$\\tau^2$','τ²').replace('$\\tau$','τ');year=(r.get('first_posted') or '2026')[:4]
        refs.append(f'[{i}] {names}. {title}[EB/OL]. {year}. arXiv:{r["version"]}. {r["url"]}'+(' '+formal[i] if i in formal else ' 预印本。'))
    other=[
      'LEE C, PARK S J, KEJRIWAL A, et al. Implementing Linearizability at Large Scale and Low Latency[C]. SOSP, 2015. DOI:10.1145/2815400.2815416. https://web.stanford.edu/~ouster/cgi-bin/papers/rifl.pdf',
      'AWS. Making Retries Safe with Idempotent APIs[EB/OL]. Amazon Builders’ Library. https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/',
      'STRIPE. Idempotent Requests[EB/OL]. API v1与v2规则须区分. https://docs.stripe.com/api/idempotent_requests',
      'AWS. Amazon DynamoDB Transactions How It Works[EB/OL]. https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html',
      'AWS. BatchWriteItem API Reference[EB/OL]. https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_BatchWriteItem.html',
      'AWS. Transactional Outbox Pattern[EB/OL]. https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html',
      'RESEND. Idempotency Keys[EB/OL]. https://resend.com/docs/dashboard/emails/idempotency-keys',
      'TEMPORAL. Activity Definition[EB/OL]. https://docs.temporal.io/activity-definition',
      'LANGCHAIN. Functional API Overview[EB/OL]. https://docs.langchain.com/oss/python/langgraph/functional-api',
      'MODEL CONTEXT PROTOCOL. Schema Reference ToolAnnotations[EB/OL]. 2025-11-25. https://modelcontextprotocol.io/specification/2025-11-25/schema',
      'GOPNAL SWAMY S. IdempotencyBench[CP/OL]. 固定代码版本5e97e4b27d1c068b60fc083689e590c08e39e40f. https://github.com/gssanjana4/idempotencybench',
      'GORILLA TEAM. BFCL V3 Multi-Turn and Multi-Step Function Calling Evaluation[EB/OL]. 2024. https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html',
      '海洋数据挖掘技术课程教学材料[Z]. 第2讲 让重复迟到失败都变得无害；第3讲 AI智能体也是分布式系统. 用户提供课程文件，任课教师及年份未由文件书目页核实。',
      'AWS. Handle Duplicate Records in Amazon Kinesis Data Streams[EB/OL]. https://docs.aws.amazon.com/streams/latest/dev/kinesis-record-processor-duplicates.html',
      'GARCIA-MOLINA H, SALEM K. Sagas[C]. SIGMOD, 1987:249–259. https://sigmodrecord.org/1987/12/09/sagas/']
    refs += [f'[{i}] {x}' for i,x in enumerate(other,24)]
    return refs

def main():
    source=R/'reference_undergraduate.docx';doc=Document(source);source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    cover=[deepcopy(p._p) for p in doc.paragraphs[:17]];cover_sect=deepcopy(doc.sections[0]._sectPr)
    body=doc._element.body
    for c in list(body):body.remove(c)
    body.append(cover_sect)
    for el in cover:
        for sect in el.xpath('.//w:sectPr'):sect.getparent().remove(sect)
        body.insert(len(body)-1,el)
    pars=doc.paragraphs
    for i,tx in [(3,'课 程 大 作 业 研 究 报 告'),(5,'海洋数据挖掘技术'),(8,'不同工具契约下 LLM Agent\n非幂等操作失败恢复的决策边界研究')]:
        pars[i].clear();pars[i].alignment=WD_ALIGN_PARAGRAPH.CENTER;setfont(pars[i].add_run(tx),24 if i!=8 else 16,'黑体',True)
    pars[8].style=doc.styles['Title'];pars[8].paragraph_format.line_spacing=1.3
    pars[8].paragraph_format.space_before=Pt(0);pars[8].paragraph_format.space_after=Pt(0)
    for i,label in [(10,'姓名与学号'),(12,'指导教师'),(14,'年级与专业'),(16,'所在学院')]:
        pars[i].clear();setfont(pars[i].add_run(label+'\t'),16,'华文仿宋',True);run=pars[i].add_run('                              ');setfont(run,16,'华文仿宋');run.underline=True
    doc.settings.odd_and_even_pages_header_footer=True;front=doc.sections[0];pageprops(front,'decimal')
    front.different_first_page_header_footer=True
    for obj in [front.first_page_header,front.first_page_footer]:
        obj.is_linked_to_previous=False
        for par in obj.paragraphs:
            par.clear();par.style=doc.styles['Normal']
            for border in par._p.xpath('./w:pPr/w:pBdr'):border.getparent().remove(border)
    for obj in [front.footer,front.even_page_footer]:roman_front_page(obj.paragraphs[0])
    title=doc.add_paragraph('目录');title.paragraph_format.page_break_before=True;title.alignment=WD_ALIGN_PARAGRAPH.CENTER;setfont(title.runs[0],16,'黑体',True)
    field(doc.add_paragraph(),'TOC \\t "章节标题,1" \\h \\z')
    section=doc.add_section(WD_SECTION_START.NEW_PAGE);pageprops(section,'decimal')
    if '章节标题' not in doc.styles:
        style=doc.styles.add_style('章节标题',WD_STYLE_TYPE.PARAGRAPH);style.base_style=doc.styles['Heading 2']
        lvl=OxmlElement('w:outlineLvl');lvl.set(qn('w:val'),'0');style.element.get_or_add_pPr().append(lvl)
    style=doc.styles['章节标题'];style.font.color.rgb=RGBColor(0,0,0);style.paragraph_format.first_line_indent=Pt(0);style.paragraph_format.keep_with_next=True;style.paragraph_format.space_before=Pt(14);style.paragraph_format.space_after=Pt(9)
    for n in ['Title','Heading 1','Heading 2','Heading 3']:doc.styles[n].font.color.rgb=RGBColor(0,0,0)
    if 'Table Grid' not in doc.styles:doc.styles.add_style('Table Grid',WD_STYLE_TYPE.TABLE)
    md=['# '+TITLE+'\n'];table_counter=0;figure_counter=0
    def paragraph(text,refs=False):
        par=doc.add_paragraph(style='Bibliography' if refs else '段')
        par.paragraph_format.line_spacing=1.15 if refs else 1.5;par.paragraph_format.space_after=Pt(4 if refs else 0)
        if not refs:par.paragraph_format.first_line_indent=Pt(24)
        par.paragraph_format.widow_control=True
        if not refs:
            for part in re.split(r'(\[[0-9]+(?:[–,\-][0-9]+)*\])',text):
                if not part:continue
                run=par.add_run(part);setfont(run,12,'仿宋');run.font.superscript=bool(re.fullmatch(r'\[[0-9]+(?:[–,\-][0-9]+)*\]',part))
        else:
            setfont(par.add_run(text),12,'宋体');par.alignment=WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.keep_with_next=False;par.paragraph_format.keep_together=True;par.paragraph_format.line_spacing=1.1;par.paragraph_format.space_after=Pt(3)
        md.append(text+'\n');return par
    def caption(text):
        par=doc.add_paragraph();par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1.2;par.paragraph_format.space_after=Pt(8)
        par.paragraph_format.keep_together=True
        setfont(par.add_run(text),10.5,'宋体');return par
    for idx,sec in enumerate(SECTIONS):
        h=doc.add_paragraph(sec['title'],style='章节标题');h.paragraph_format.page_break_before=idx in [12]
        md.append('## '+sec['title']+'\n')
        for block in sec['blocks']:
            typ=block['type']
            if typ=='p':paragraph(block['text'])
            elif typ=='table':
                table_counter+=1;cap=caption(block['title']);cap.paragraph_format.keep_with_next=True
                t=doc.add_table(rows=1,cols=len(block['headers']));t.style='Table Grid';t.autofit=False
                borders=OxmlElement('w:tblBorders')
                for edge in ['top','left','bottom','right','insideH','insideV']:
                    el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'B7B7B7');borders.append(el)
                t._tbl.tblPr.append(borders)
                for j,w in enumerate(block['widths']):t.columns[j].width=Cm(w)
                for n,values in enumerate([block['headers']]+block['rows']):
                    row=t.rows[0] if n==0 else t.add_row()
                    row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
                    for j,tx in enumerate(values):
                        cell=row.cells[j];cell.width=Cm(block['widths'][j]);par=cell.paragraphs[0];par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.line_spacing=1.12;par.paragraph_format.space_before=Pt(4);par.paragraph_format.space_after=Pt(4)
                        par.alignment=WD_ALIGN_PARAGRAPH.LEFT
                        margins=OxmlElement('w:tcMar')
                        for side,value in [('left','75'),('right','75'),('top','20'),('bottom','20')]:
                            m=OxmlElement('w:'+side);m.set(qn('w:w'),value);m.set(qn('w:type'),'dxa');margins.append(m)
                        cell._tc.get_or_add_tcPr().append(margins)
                        setfont(par.add_run(str(tx)),10.5,'宋体',n==0)
                        if len(block['rows'])<=5 and n<len(block['rows']):par.paragraph_format.keep_with_next=True
                        if n==0:
                            par.paragraph_format.keep_with_next=True;shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'F1F1F1');cell._tc.get_or_add_tcPr().append(shade)
                t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
                blank=doc.add_paragraph();blank.paragraph_format.line_spacing=Pt(2);blank.paragraph_format.space_after=Pt(5)
                md.append(block['title']+'\n| '+' | '.join(block['headers'])+' |\n|'+ '|'.join(['---']*len(block['headers']))+'|\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in block['rows']))
            elif typ=='figure':
                figure_counter+=1;png=R/'figures'/(block['file']+'.png');svg=R/'figures'/(block['file']+'.svg')
                par=doc.add_paragraph();par.alignment=WD_ALIGN_PARAGRAPH.CENTER;par.paragraph_format.first_line_indent=Pt(0);par.paragraph_format.keep_with_next=True;par.paragraph_format.space_after=Pt(3)
                inline=par.add_run().add_picture(str(png),width=Cm(14.6))
                partname=doc.part.package.next_partname('/word/media/vector%d.svg');svgpart=Part(partname,'image/svg+xml',svg.read_bytes(),doc.part.package);rid=doc.part.relate_to(svgpart,RT.IMAGE)
                blip=inline._inline.xpath('.//a:blip')[0];extlst=OxmlElement('a:extLst');ext=OxmlElement('a:ext');ext.set('uri','{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
                svgblip=etree.Element('{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip',nsmap={'asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main'});svgblip.set(qn('r:embed'),rid);ext.append(svgblip);extlst.append(ext);blip.append(extlst)
                caption(block['caption']);md.append('!['+block['caption']+'](figures/'+block['file']+'.svg)\n')
            elif typ=='references':
                for ref in references():paragraph(ref,True)
    doc.core_properties.title=TITLE;doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.core_properties.subject='课程大作业研究总结';doc.core_properties.comments=''
    # Remove old unrelated content parts while retaining only used cover graphics and new report media.
    used=set()
    for el in doc._element.iter():
        for k,v in el.attrib.items():
            if k.startswith('{'+ 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'+'}'):used.add(v)
    keep_types={'styles','stylesWithEffects','settings','webSettings','fontTable','theme','numbering','footnotes','endnotes'}
    for rid,rel in list(doc.part.rels.items()):
        kind=rel.reltype.rsplit('/',1)[-1]
        if kind in {'footnotes','endnotes'}:
            root=etree.fromstring(rel.target_part.blob)
            for entry in list(root):
                if int(entry.get(qn('w:id'),'1'))>0:root.remove(entry)
            rel.target_part._blob=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
        if kind in keep_types:continue
        if rid not in used:del doc.part.rels[rid]
    for rid,rel in list(doc.part.package.rels.items()):
        if rel.reltype.endswith('custom-properties'):del doc.part.package.rels[rid]
    out=R/'不同工具契约下LLM_Agent非幂等操作失败恢复的决策边界研究.docx';doc.save(out)
    (R/'研究总结与报告.md').write_text('\n'.join(md),encoding='utf-8')
    (R/'artifact_build.json').write_text(json.dumps({'output':out.name,'source_template_sha256':source_hash,'chapters':len(SECTIONS),'figures':figure_counter,'tables':table_counter,'references':len(references()),'source_document_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==source_hash},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'chapters':len(SECTIONS),'figures':figure_counter,'tables':table_counter,'references':len(references()),'docx':out.name},ensure_ascii=False))
if __name__=='__main__':main()
