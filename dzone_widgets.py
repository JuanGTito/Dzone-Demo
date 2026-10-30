"""Desplazamiento continuo de página, sin barras visibles ni temporizadores en reposo."""
import tkinter as tk
from tkinter import ttk


class PageScroller(tk.Frame):
    def __init__(self,parent,bg='#f5f7fb'):
        super().__init__(parent,bg=bg)
        self.canvas=tk.Canvas(self,bg=bg,highlightthickness=0,borderwidth=0,yscrollincrement=1)
        self.canvas.pack(fill='both',expand=True)
        self.content=tk.Frame(self.canvas,bg=bg)
        self.content._page_scroller=self
        self.item=self.canvas.create_window((0,0),window=self.content,anchor='nw')
        self.target=0;self.animation=None
        self.content.bind('<Configure>',self.resize)
        self.canvas.bind('<Configure>',self.resize)
        self.bind('<Destroy>',self.cleanup,add='+')

    def resize(self,event=None):
        width=max(1,self.canvas.winfo_width());height=max(self.content.winfo_reqheight(),self.canvas.winfo_height())
        self.canvas.itemconfigure(self.item,width=width,height=height)
        self.canvas.configure(scrollregion=(0,0,width,height))

    def scroll(self,pixels):
        self.resize()
        maximum=max(0,self.content.winfo_height()-self.canvas.winfo_height())
        if maximum<=0:return False
        current=self.canvas.canvasy(0)
        if self.animation is None:self.target=current
        self.target=max(0,min(maximum,self.target+pixels))
        if self.animation is None:self.animate()
        return True

    def animate(self):
        self.animation=None
        current=self.canvas.canvasy(0);distance=self.target-current
        total=max(1,self.content.winfo_height())
        if abs(distance)<=2:
            self.canvas.yview_moveto(self.target/total);return
        self.canvas.yview_moveto((current+distance*.4)/total)
        self.animation=self.after(16,self.animate)

    def reset(self):
        if self.animation is not None:self.after_cancel(self.animation);self.animation=None
        self.target=0;self.canvas.yview_moveto(0)

    def cleanup(self,event):
        if event.widget==self and self.animation is not None:
            self.after_cancel(self.animation);self.animation=None


class WheelRouter:
    def __init__(self,root):
        self.root=root
        root.bind_all('<MouseWheel>',self.route)
        # Evitar que el scroll nativo de la tabla se sume al de la página.
        root.bind_class('Treeview','<MouseWheel>',self.route)
        root.bind_class('Text','<MouseWheel>',self.route)
        root.bind_all('<Button-4>',self.route);root.bind_all('<Button-5>',self.route)
        root.bind_all('<Next>',lambda event:self.page(event,1))
        root.bind_all('<Prior>',lambda event:self.page(event,-1))

    def find(self,widget):
        while widget is not None:
            if hasattr(widget,'_page_scroller'):return widget._page_scroller
            widget=getattr(widget,'master',None)
        return None

    def route(self,event):
        widget=event.widget
        try:
            delta=-1 if getattr(event,'num',None)==4 else 1 if getattr(event,'num',None)==5 else -event.delta/120
            if not delta:return
            if isinstance(widget,tk.Text):
                first,last=widget.yview()
                if (delta>0 and last<1) or (delta<0 and first>0):
                    widget.yview_scroll((1 if delta>0 else -1)*max(1,round(abs(delta)*3)),'units');return 'break'
            if isinstance(widget,ttk.Treeview) and event.state&1:
                widget.xview_scroll((1 if delta>0 else -1)*max(1,round(abs(delta)*3)),'units');return 'break'
            page=self.find(widget)
            if page is not None:page.scroll(delta*96);return 'break'
        except (tk.TclError,AttributeError):return

    def page(self,event,direction):
        if isinstance(event.widget,tk.Text):return
        page=self.find(event.widget)
        if page is not None:page.scroll(direction*page.canvas.winfo_height()*.85);return 'break'
