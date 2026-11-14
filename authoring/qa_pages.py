from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
R=Path(__file__).parent;Q=R/'qa';Q.mkdir(exist_ok=True)
pdf=pdfium.PdfDocument(str(Q/'report.pdf'));texts=[]
for i,page in enumerate(pdf):
 im=page.render(scale=1.67).to_pil().convert('RGB');im.save(Q/f'page-{i+1}.png')
 text=page.get_textpage().get_text_range();texts.append(f'\n=== PAGE {i+1} ===\n'+text)
(Q/'page_text.txt').write_text('\n'.join(texts),encoding='utf-8')
for start in range(0,len(pdf),9):
 out=Image.new('RGB',(3*350,3*520),'#D5D5D5');dr=ImageDraw.Draw(out)
 for j in range(start,min(start+9,len(pdf))):
  im=Image.open(Q/f'page-{j+1}.png');im.thumbnail((340,490));x=(j-start)%3*350;y=(j-start)//3*520;out.paste(im,(x,y+22));dr.text((x+5,y+4),str(j+1),fill='black')
 out.save(Q/f'contact-{start//9+1}.jpg',quality=90)
figs=list((R/'figures').glob('*.png'));out=Image.new('RGB',(1100,9*270),'white')
dr=ImageDraw.Draw(out)
for i,p in enumerate(sorted(figs)):
 im=Image.open(p).convert('RGB');im.thumbnail((1000,245));out.paste(im,(50,i*270+20));dr.text((5,i*270+2),p.stem,fill='black')
out.save(Q/'figure_contact.jpg',quality=93)
print('Rendered',len(pdf),'pages; text and contact sheets saved')
