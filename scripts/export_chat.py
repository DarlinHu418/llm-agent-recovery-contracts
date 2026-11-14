"""Export user and public assistant messages, never reasoning or system instructions."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,re
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rollout',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 raw=a.rollout.read_bytes();messages=[];excluded=Counter();bad=[]
 for line_no,line in enumerate(raw.splitlines(),1):
  try:r=json.loads(line)
  except json.JSONDecodeError:bad.append(line_no);continue
  q=r.get('payload',{})
  if r.get('type')!='response_item' or q.get('type')!='message':continue
  role=q.get('role');phase=q.get('phase')
  if role not in ['user','assistant']:excluded[role or 'unknown']+=1;continue
  if role=='assistant' and phase not in ['final','final_answer','commentary']:excluded['nonpublic_assistant']+=1;continue
  text='\n'.join(x.get('text','') for x in q.get('content',[]) if x.get('type') in ['input_text','output_text','text'])
  if role=='user' and text.lstrip().startswith('<environment_context>'):excluded['environment_only']+=1;continue
  if text.startswith('# AGENTS.md instructions') and '<environment_context>' in text:text=text.split('<environment_context>',1)[0].rstrip()
  if not text.strip():continue
  text=re.sub(r'C:[\\/]Users[\\/]16421','<USER_HOME>',text,flags=re.I)
  if 'github.com/login/device' in text:text=re.sub(r'\b[A-Z0-9]{4}-[A-Z0-9]{4}\b','<DEVICE_LOGIN_CODE_REDACTED>',text)
  assert not re.search(r'\bsk-[A-Za-z0-9_-]{24,}\b',text),'Potential credential: stop and inspect privately'
  messages.append({'role':role,'phase':phase,'timestamp':r.get('timestamp'),'text':text,'source_line':line_no})
 assert messages,'No supported visible messages found; do not synthesize missing text'
 counts=Counter(x['role'] for x in messages)
 lines=['# 完整AI协作聊天记录','','本文件逐条导出本课题当前聊天的用户消息及助手可见进度与最终回答，按原始顺序保留，不用总结补写。旧回答反映当时判断，最终研究结论以最终课程报告为准。','','范围：2026年11月9日起本聊天，至下列导出截点；不涵盖其他聊天，发布后的未来发言无法包含。排除系统/开发者指令、内部推理、工具协议及机器注入的环境包。实验公开工具动作另见各会话public_events.jsonl。本机用户目录替换为<USER_HOME>，登录验证码替换为<DEVICE_LOGIN_CODE_REDACTED>；用户自写偏好保留，机器环境后缀去除。含标签的用户消息用代码围栏展示。','',f'导出截点 UTC：{messages[-1]["timestamp"]}；用户消息 {counts["user"]} 条，助手消息 {counts["assistant"]} 条。','']
 for i,x in enumerate(messages,1):
  lines.extend([f'## {i:03d} '+('用户' if x['role']=='user' else '助手')+' '+str(x['timestamp'])+(' '+x['phase'] if x['phase'] else ''),''])
  text=x['text']
  if x['role']=='user' and ('<INSTRUCTIONS>' in text or text.lstrip().startswith('<send_user_message_question_reply>')):text='````text\n'+text+'\n````'
  lines.extend([text,''])
 a.output.mkdir(parents=True,exist_ok=True);(a.output/'完整AI协作聊天记录.md').write_text('\n'.join(lines),encoding='utf-8')
 meta={'source_snapshot_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),'exported_messages':len(messages),'counts':dict(counts),'excluded_message_categories':dict(excluded),'malformed_lines':bad,'first_message_utc':messages[0]['timestamp'],'cutoff_utc':messages[-1]['timestamp'],'message_index':[{'index':i,**{k:v for k,v in x.items() if k!='text'},'exported_text_sha256':hashlib.sha256(x['text'].encode()).hexdigest()} for i,x in enumerate(messages,1)]}
 (a.output/'export_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'messages':len(messages),'counts':dict(counts),'cutoff':messages[-1]['timestamp']}))
if __name__=='__main__':main()
