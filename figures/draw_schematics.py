"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)


def architecture(out):
    d=Drawing((0,0,8.8,5.1))
    for name,x,y,label in [
        ('up',2.0,3.8,'Upstream queue verifier\n'+r'$\mathcal{H},\rho,\Pi$'),
        ('prod',6.5,3.8,'Certificate producer\nFlow + prefix theorem'),
        ('oracle',2.0,2.2,'Independent DP oracle\nBounded tests'),
        ('cert',6.5,2.2,'JSON certificate\nMatrix / core / path'),
        ('check',6.5,.6,'Standalone checker\nStrict replay')]:
        d.box(name,x,y,3.5,.75,label,size=8.5)
    d.frame(4.55,1.63,3.95,2.88)
    d.text(6.5,4.78,'Untrusted production side',8.5)
    d.edge('up','prod','e','w');d.edge('prod','cert')
    d.edge('cert','check')
    d.arrow(d.point('up','w'),d.point('check','w'),dashed=True,
            via=[(.12,3.8),(.12,.6)])
    d.arrow(d.point('oracle','n'),(5.7,3.425),dashed=True,
            via=[(2.0,2.95),(5.7,2.95)])
    d.arrow(d.point('oracle','s'),(5.7,.975),dashed=True,
            via=[(2.0,1.35),(5.7,1.35)])
    d.save(out,'architecture')


def transfer(out):
    d=Drawing((0,0,8.8,2.9))
    left=[[1,1,0,0],[1,0,1,0],[1,0,0,1],[1,0,0,0]]
    right=[[0,1,0,1],[1,0,1,0],[1,0,0,1],[1,0,0,0]]
    for cx,values,title in [(2.0,left,r'$X,\ h=(4,1,1,1)$'),
                             (6.8,right,r"$X',\ h'=(3,1,1,2)$")]:
        d.text(cx,2.6,title,8.5)
        for i,row in enumerate(values):
            for j,value in enumerate(row):
                d.text(cx-.63+j*.42,1.95-i*.42,str(value),9)
        d.line([(cx-.87,2.2),(cx-1.0,2.2),(cx-1.0,.45),(cx-.87,.45)])
        d.line([(cx+.87,2.2),(cx+1.0,2.2),(cx+1.0,.45),(cx+.87,.45)])
    d.arrow((3.2,1.35),(5.6,1.35));d.text(4.4,1.68,'Row 1',8.5)
    d.save(out,'transfer')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    architecture(a.output);transfer(a.output)


