from pathlib import Path
import sys,json
R=Path(__file__).parent;sys.path.insert(0,str(R/'.deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,FancyBboxPatch,Polygon,Patch
from matplotlib.lines import Line2D
from matplotlib.font_manager import FontProperties
F=FontProperties(fname='C:/Windows/Fonts/msyh.ttc',size=10)
plt.rcParams.update({'font.family':F.get_name(),'svg.fonttype':'none','pdf.fonttype':42,'axes.unicode_minus':False})
C={'blue':'#3274A1','green':'#228675','purple':'#7963A5','orange':'#D18B35','red':'#B85D60','gray':'#7C8792','light':'#EEF1F4'}
OUT=R/'figures';OUT.mkdir(exist_ok=True)
manifest=[]
def canvas(size=(9,3)):
    fig,ax=plt.subplots(figsize=size);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');fig.subplots_adjust(left=.02,right=.98,top=.98,bottom=.26);return fig,ax
def node(ax,x,y,color,shape='circle',r=.055):
    if shape=='diamond':patch=Polygon([(x-r,y),(x,y+r),(x+r,y),(x,y-r)],facecolor=color,edgecolor='white',linewidth=1.3)
    elif shape=='box':patch=FancyBboxPatch((x-r,y-r*.65),2*r,1.3*r,boxstyle='round,pad=0.012',facecolor=color,edgecolor='white')
    else:patch=Circle((x,y),r,facecolor=color,edgecolor='white',linewidth=1.3)
    ax.add_patch(patch)
def arrow(ax,a,b,dash=False,color='#A8B0B7'):
    ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'-|>','lw':1.8,'color':color,'linestyle':'--' if dash else '-'})
def legend(fig,items,ncol=3):
    handles=[Patch(facecolor=color,edgecolor='none',label=label) for label,color in items]
    fig.legend(handles=handles,loc='lower center',ncol=ncol,frameon=False,prop=F,columnspacing=1.5,handlelength=1.2)
def save(fig,name,kind):
    for ext in ['svg','pdf','png']:fig.savefig(OUT/(name+'.'+ext),dpi=240,facecolor='white')
    manifest.append({'name':name,'kind':kind,'text_policy':'Only legend text; titles, node labels, ticks and captions appear outside images.'});plt.close(fig)
def bars(name,values,labels,colors):
    fig,ax=plt.subplots(figsize=(9,3.5));n=len(values[0]);ax.set(xlim=(-.015,1.03),ylim=(-.6,n-.4));ax.axis('off')
    for x in [0,.25,.5,.75,1]:ax.axvline(x,color='#D9DFE4',lw=.8,zorder=0)
    total=.62;h=total/len(values)
    for j,v in enumerate(values):
        yy=[n-1-i-total/2+h*(j+.5) for i in range(n)]
        ax.barh(yy,[1]*n,height=h*.78,color='#F0F2F4',zorder=1)
        ax.barh(yy,v,height=h*.78,color=colors[j],label=labels[j],zorder=2)
    fig.subplots_adjust(left=.035,right=.98,top=.98,bottom=.21)
    legend(fig,list(zip(labels,colors)),len(labels));save(fig,name,'data')
def main():
    data=json.loads((R/'data_snapshot.json').read_text(encoding='utf-8'))
    fig,ax=canvas((9,2.5));xs=[.08,.29,.50,.71,.92];cs=[C[k] for k in ['gray','blue','green','purple','orange']]
    for x,c in zip(xs,cs):node(ax,x,.55,c,'box')
    for x,y in zip(xs,xs[1:]):arrow(ax,(x+.07,.55),(y-.07,.55))
    legend(fig,list(zip(['初始身份漂移假设','评价有效性校准','契约可见性决策','细粒度动作分叉','确定性执行保障'],cs)),3);save(fig,'01_question_evolution','schematic')
    fig,ax=canvas((9,3.4));node(ax,.10,.5,C['gray'],'box');node(ax,.90,.5,C['orange'],'box')
    for y,c in zip([.82,.5,.18],[C['blue'],C['green'],C['purple']]):
        node(ax,.5,y,c,'box');arrow(ax,(.17,.5),(.43,y));arrow(ax,(.57,y),(.83,.5))
        for x in [.34,.66]:node(ax,x,y,c,r=.018)
    legend(fig,[('固定授权与模拟工具',C['gray']),('阶段一 32会话',C['blue']),('阶段二 18会话',C['green']),('阶段三 12有效会话',C['purple']),('独立账本与轨迹核验',C['orange'])],3);save(fig,'02_three_stage_design','schematic')
    fig,ax=canvas((9,3.4));node(ax,.5,.85,C['gray'],'diamond')
    for x,n in [(.18,0),(.5,1),(.82,2)]:
        arrow(ax,(.5,.77),(x,.56))
        for j in range(2):
            patch=FancyBboxPatch((x-.09+j*.10,.31),.075,.14,boxstyle='round,pad=.008',facecolor=C['blue'] if j<n else 'white',edgecolor=C['gray'],linewidth=1.5);ax.add_patch(patch)
    arrow(ax,(.18,.29),(.43,.29),dash=True,color=C['orange'])
    legend(fig,[('相同超时观测',C['gray']),('效果已提交',C['blue']),('效果尚未提交', '#FFFFFF'),('在途请求仍可能晚提交',C['orange'])],2);save(fig,'03_hidden_commit_states','schematic')
    fig,ax=canvas((9,3.9));node(ax,.5,.88,C['gray'],'diamond');node(ax,.20,.51,C['green'],'box');node(ax,.75,.51,C['gray'],'diamond');node(ax,.57,.12,C['blue'],'box');node(ax,.91,.12,C['orange'],'box')
    arrow(ax,(.45,.82),(.23,.58));arrow(ax,(.55,.82),(.72,.58),True);arrow(ax,(.72,.44),(.59,.19));arrow(ax,(.78,.44),(.89,.19),True)
    legend(fig,[('契约判定节点',C['gray']),('原批次同键续做',C['green']),('终结证据后仅补未执行项',C['blue']),('保留未决',C['orange'])],2);save(fig,'04_safe_action_tree','schematic')
    one=data['stage1'];order=[one['main']['content_receipt'],one['main']['authorization_receipt'],one['followup']['content_receipt'],one['followup']['authorization_receipt']]
    vals=[[g[k]/g['valid'] for g in order] for k in ['native_accept','native_claim_aware_accept','authorized_resolved_exact']]
    bars('05_evaluation_reversal',vals,['内容评价 E0','E0加完成声明','授权效果评价 E1'],[C['blue'],C['gray'],C['orange']])
    two=data['stage2']['groups'];v=[g for g in two if g['visible']];hidden=[g for g in two if not g['visible']]
    policy=[g['policy_correct']/g['valid'] for g in v]+[sum(g['policy_correct'] for g in hidden)/9]
    completed=[g['completed_with_evidence']/g['valid'] for g in v]+[sum(g['completed_with_evidence'] for g in hidden)/9]
    bars('06_contract_visibility',[policy,completed],['符合信息与契约的决策','有证据的任务完成'],[C['blue'],C['orange']])
    fig,ax=plt.subplots(figsize=(9,3.2));ax.axis('off');ax.set(xlim=(0,1),ylim=(-.6,3.6));left=[0]*4
    for action,color,label in [('original_replay',C['green'],'原批次同键恢复'),('residual_request',C['blue'],'查询后补做'),('hold',C['orange'],'保留未决')]:
        value=[g['actions'].get(action,0)/g['valid'] for g in data['stage3']['profiles']];ax.barh([3,2,1,0],value,left=left,height=.52,color=color);left=[a+b for a,b in zip(left,value)]
    fig.subplots_adjust(left=.035,right=.98,top=.98,bottom=.22);legend(fig,[('原批次同键恢复',C['green']),('查询后补做',C['blue']),('保留未决',C['orange'])],3);save(fig,'07_action_divergence','data')
    b=data['stage3']['baselines'];total=data['stage3']['valid'];modelcorrect=sum(g['boundary_correct'] for g in data['stage3']['profiles'])/total
    bars('08_agent_rule_comparison',[[modelcorrect]+[x['boundary_correct']/12 for x in b],[1]+[x['safe']/12 for x in b]],['动作边界及最终状态正确','决策在契约下有安全依据'],[C['blue'],C['green']])
    fig,ax=canvas((9,3.0));node(ax,.15,.68,C['blue'],'box');node(ax,.5,.68,C['green'],'box');node(ax,.85,.68,C['orange'],'box');node(ax,.5,.18,C['purple'],'box')
    arrow(ax,(.23,.68),(.42,.68));arrow(ax,(.58,.68),(.77,.68));arrow(ax,(.5,.6),(.5,.27));arrow(ax,(.83,.60),(.58,.20),dash=True)
    legend(fig,[('Agent提出恢复动作',C['blue']),('Workflow检查与准入',C['green']),('工具端防重与实际提交',C['orange']),('持久身份 状态及证据',C['purple'])],2);save(fig,'09_decision_execution_boundary','schematic')
    (R/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('9 original figures exported as SVG PDF PNG')
if __name__=='__main__':main()
