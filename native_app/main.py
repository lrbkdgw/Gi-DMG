"""Gi DMG - native desktop edition.

This is deliberately a native Tk GUI: it does not embed, load, or render the
legacy HTML application.  The JSON model is kept portable so configurations
can be moved between Windows builds.
"""
from __future__ import annotations
import copy, csv, json, math, os, sys, time, uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

VERSION = "2.1.9-native"
ELEMENTS = ("火", "水", "雷", "冰", "草", "风", "岩", "物理")
ELEMENT_COLORS = {"火":"#d75a3a", "水":"#2a7fbe", "雷":"#7d55c7", "冰":"#3a9db8", "草":"#5a9a3a", "风":"#2b9b7f", "岩":"#b88a2d", "物理":"#6a5f57"}
REACTIONS = ("无", "蒸发", "融化", "超载", "感电", "绽放", "超导", "扩散", "月感电", "月绽放", "月结晶")


def uid(): return uuid.uuid4().hex[:10]
def app_dir():
    # In a frozen build this points next to the EXE; in source mode next to main.py.
    return Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent

def data_dir():
    p = app_dir() / "date"
    p.mkdir(exist_ok=True)
    return p

def new_state(name="未命名配置"):
    return {"name": name, "settings": {"timeline": True, "damage_share": True, "rotation": 20, "history": 20},
            "characters": [], "weapons": [], "artifacts": [], "baselines": [], "updated": time.time()}

def default_character():
    return {"id": uid(), "name":"新角色", "element":"火", "level":90, "base_atk":300, "weapon_atk":608,
            "crit":5, "crit_dmg":50, "mastery":0, "bonus":0, "resistance":10,
            "talents":[{"name":"元素战技", "kind":"E", "mult":200, "hits":1, "reaction":"无"},
                       {"name":"元素爆发", "kind":"Q", "mult":400, "hits":1, "reaction":"无"}]}

class Store:
    def __init__(self): self.root=data_dir()
    def files(self): return sorted(self.root.glob("*.json"))
    def load(self, path):
        try:
            d=json.loads(path.read_text(encoding="utf-8")); return d if isinstance(d,dict) else new_state(path.stem)
        except Exception as e: messagebox.showerror("配置读取失败", str(e)); return None
    def save(self, state, path=None):
        path = Path(path) if path else self.root/(safe_name(state["name"])+".json")
        state["updated"] = time.time()
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

def safe_name(s):
    return "".join(c for c in s.strip() if c not in '<>:/\\|?*"')[:80] or "未命名配置"

def damage(c, t):
    """Native implementation of the calculator's common damage path."""
    level=c.get("level",90); atk=c.get("base_atk",0)+c.get("weapon_atk",0)
    level_factor = 0.85 + level / 300
    base = atk * float(t.get("mult",0)) / 100 * max(0.1, level_factor)
    reaction=t.get("reaction","无")
    mastery=float(c.get("mastery",0)); react=1.0
    if reaction in ("蒸发", "融化"): react = (2.0 if reaction=="蒸发" else 1.5) * (1 + 2.78*mastery/(mastery+1400) if mastery else 1)
    elif reaction in ("超载", "感电", "绽放", "超导", "扩散", "月感电", "月绽放", "月结晶"):
        react = 1 + 16*mastery/(mastery+2000) if mastery else 1
    bonus=1+float(c.get("bonus",0))/100
    defense=max(.1, 100/(100+max(0,level-90)))
    resist=max(0, 1-float(c.get("resistance",10))/100)
    crit=1+float(c.get("crit_dmg",50))/100 * min(1,max(0,float(c.get("crit",5))/100))
    return base*react*bonus*defense*resist*crit*int(t.get("hits",1) or 1)

def total_damage(state):
    rows=[]
    for c in state.get("characters",[]):
        for t in c.get("talents",[]): rows.append((c["name"], t.get("name","伤害"), damage(c,t)))
    return sum(x[2] for x in rows), rows

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Gi DMG 原神伤害计算器 · 原生版"); self.geometry("1440x900"); self.minsize(1100,700)
        self.configure(bg="#f3f5f8"); self.store=Store(); self.state=None; self.path=None; self.style=ttk.Style(self)
        try: self.style.theme_use("clam")
        except tk.TclError: pass
        self.style.configure("TButton", padding=(10,6)); self.style.configure("Treeview", rowheight=30, font=("Segoe UI",10))
        self.style.configure("Treeview.Heading", font=("Segoe UI",10,"bold")); self.protocol("WM_DELETE_WINDOW", self.close)
        self.show_manager()

    def clear(self):
        for x in self.winfo_children(): x.destroy()
    def heading(self, parent, text, size=18): return tk.Label(parent,text=text,bg=parent.cget("bg"),fg="#263241",font=("Microsoft YaHei UI",size,"bold"))
    def show_manager(self):
        self.clear(); self.state=None; self.configure(bg="#eef1f5")
        wrap=tk.Frame(self,bg="#eef1f5"); wrap.pack(fill="both",expand=True,padx=70,pady=55)
        self.heading(wrap,"Gi DMG",30).pack(anchor="w"); tk.Label(wrap,text="原生桌面版  ·  配置管理",bg=wrap.cget("bg"),fg="#657181",font=("Microsoft YaHei UI",12)).pack(anchor="w",pady=(0,28))
        card=tk.Frame(wrap,bg="white",highlightbackground="#e0e5eb",highlightthickness=1); card.pack(fill="both",expand=True)
        tk.Label(card,text="选择配置",bg="white",fg="#263241",font=("Microsoft YaHei UI",16,"bold")).pack(anchor="w",padx=28,pady=(25,10))
        box=tk.Frame(card,bg="white"); box.pack(fill="both",expand=True,padx=28)
        self.cfg_list=tk.Listbox(box,bg="#f7f9fb",fg="#374151",relief="flat",highlightthickness=0,font=("Microsoft YaHei UI",11),selectbackground="#dbe8ff")
        self.cfg_list.pack(side="left",fill="both",expand=True); scroll=ttk.Scrollbar(box,command=self.cfg_list.yview); scroll.pack(side="right",fill="y"); self.cfg_list.config(yscrollcommand=scroll.set)
        files=self.store.files()
        for f in files: self.cfg_list.insert("end", f.stem)
        actions=tk.Frame(card,bg="white"); actions.pack(fill="x",padx=28,pady=22)
        ttk.Button(actions,text="新建配置",command=self.new_config).pack(side="left"); ttk.Button(actions,text="打开选中配置",command=self.open_selected).pack(side="left",padx=8)
        ttk.Button(actions,text="导入 JSON",command=self.import_config).pack(side="left"); ttk.Button(actions,text="删除配置",command=self.delete_config).pack(side="right")
        tk.Label(card,text=f"数据目录：{data_dir()}    |    v{VERSION}",bg="white",fg="#8b96a4",font=("Segoe UI",9)).pack(anchor="w",padx=28,pady=(0,20))
    def new_config(self):
        n=simpledialog.askstring("新建配置","配置名称：",parent=self,initialvalue="新配置")
        if n: self.state=new_state(n); self.state["characters"]=[default_character()]; self.path=self.store.save(self.state); self.show_main()
    def open_selected(self):
        sel=self.cfg_list.curselection()
        if not sel: return messagebox.showinfo("提示","请先选择配置")
        self.path=self.store.files()[sel[0]]; self.state=self.store.load(self.path)
        if self.state: self.show_main()
    def delete_config(self):
        sel=self.cfg_list.curselection()
        if sel and messagebox.askyesno("删除配置","确认删除选中的配置？"): self.store.files()[sel[0]].unlink(); self.show_manager()
    def import_config(self):
        p=filedialog.askopenfilename(filetypes=[("JSON 配置","*.json")])
        if p:
            d=self.store.load(Path(p))
            if d: self.path=self.store.save(d); self.state=d; self.show_main()

    def show_main(self):
        self.clear(); self.configure(bg="#f3f5f8")
        self.left=tk.Frame(self,bg="#ffffff",width=235); self.left.pack(side="left",fill="y"); self.left.pack_propagate(False)
        tk.Label(self.left,text="◈  Gi DMG",bg="white",fg="#263241",font=("Segoe UI",18,"bold")).pack(anchor="w",padx=22,pady=24)
        self.navbuttons=[]
        for label, cmd in [("角色与伤害",self.page_characters),("武器库",self.page_weapons),("圣遗物库",self.page_artifacts),("快速拉表",self.page_quick),("计算公式",self.page_formula)]:
            b=tk.Button(self.left,text="  "+label,anchor="w",relief="flat",bd=0,bg="white",activebackground="#edf3ff",fg="#556171",font=("Microsoft YaHei UI",11),command=cmd); b.pack(fill="x",padx=12,pady=2,ipady=9); self.navbuttons.append(b)
        tk.Frame(self.left,bg="#e8ebef",height=1).pack(fill="x",padx=18,pady=16)
        ttk.Button(self.left,text="设置",command=self.page_settings).pack(fill="x",padx=20,pady=4); ttk.Button(self.left,text="保存并退出",command=self.save_exit).pack(fill="x",padx=20,pady=4)
        self.center=tk.Frame(self,bg="#f3f5f8"); self.center.pack(side="left",fill="both",expand=True)
        self.right=tk.Frame(self,bg="white",width=310); self.right.pack(side="right",fill="y"); self.right.pack_propagate(False)
        self.island=tk.Frame(self.center,bg="#273445"); self.island.pack(fill="x",padx=18,pady=(14,8)); self.island.bind("<Button-1>",lambda e:self.show_actions())
        self.island_label=tk.Label(self.island,text=f"  {self.state['name']}  ·  已保存",bg="#273445",fg="white",font=("Microsoft YaHei UI",11,"bold")); self.island_label.pack(pady=10)
        self.page_characters()
    def save(self):
        if self.state: self.path=self.store.save(self.state,self.path)
    def save_exit(self): self.save(); self.show_manager()
    def show_actions(self):
        m=tk.Menu(self,tearoff=0); m.add_command(label="保存并退出",command=self.save_exit); m.add_command(label="不保存并退出",command=self.show_manager); m.add_command(label="快速拉表",command=self.page_quick); m.add_command(label="设置",command=self.page_settings); m.tk_popup(self.winfo_pointerx(),self.winfo_pointery())
    def page_base(self,title,subtitle=""):
        for x in self.center.winfo_children():
            if x is not self.island: x.destroy()
        top=tk.Frame(self.center,bg="#f3f5f8"); top.pack(fill="x",padx=28,pady=(16,10)); self.heading(top,title,21).pack(anchor="w"); tk.Label(top,text=subtitle,bg=top.cget("bg"),fg="#718096",font=("Microsoft YaHei UI",10)).pack(anchor="w",pady=(3,0)); return top
    def page_characters(self):
        self.page_base("角色与伤害","编辑角色面板、技能倍率和反应；计算结果实时更新")
        pane=tk.Frame(self.center,bg="#f3f5f8"); pane.pack(fill="both",expand=True,padx=28,pady=5)
        left=tk.Frame(pane,bg="white"); left.pack(side="left",fill="y",padx=(0,12)); tk.Label(left,text="队伍",bg="white",font=("Microsoft YaHei UI",11,"bold")).pack(anchor="w",padx=14,pady=14)
        self.charlist=tk.Listbox(left,width=22,bg="white",relief="flat",highlightthickness=0,selectbackground="#dbe8ff",font=("Microsoft YaHei UI",10)); self.charlist.pack(fill="both",expand=True,padx=8); self.charlist.bind("<<ListboxSelect>>",lambda e:self.edit_character())
        for c in self.state["characters"]: self.charlist.insert("end",f"{c['name']}  ·  {c['element']}")
        ttk.Button(left,text="＋ 添加角色",command=self.add_character).pack(fill="x",padx=12,pady=12)
        self.editor=tk.Frame(pane,bg="white"); self.editor.pack(side="left",fill="both",expand=True); self.edit_character()
        self.update_results()
    def add_character(self): self.state["characters"].append(default_character()); self.page_characters()
    def edit_character(self):
        for x in self.editor.winfo_children(): x.destroy()
        idx=self.charlist.curselection();
        if not idx: return
        c=self.state["characters"][idx[0]]; self.current_char=c
        head=tk.Frame(self.editor,bg="white"); head.pack(fill="x",padx=20,pady=18); tk.Label(head,text=c["name"],bg="white",font=("Microsoft YaHei UI",15,"bold")).pack(side="left"); ttk.Button(head,text="删除角色",command=lambda:self.delete_char(idx[0])).pack(side="right")
        form=tk.Frame(self.editor,bg="white"); form.pack(fill="x",padx=20); self.vars={}
        fields=[("名称","name",c["name"]),("元素","element",c["element"]),("等级","level",c["level"]),("基础攻击","base_atk",c["base_atk"]),("武器攻击","weapon_atk",c["weapon_atk"]),("暴击率 %","crit",c["crit"]),("暴击伤害 %","crit_dmg",c["crit_dmg"]),("元素精通","mastery",c["mastery"]),("伤害加成 %","bonus",c["bonus"]),("抗性 %","resistance",c["resistance"])]
        for i,(lab,key,val) in enumerate(fields):
            r,cx=divmod(i,2); tk.Label(form,text=lab,bg="white",fg="#596575").grid(row=r,column=cx*2,sticky="w",padx=(0,8),pady=5); v=tk.StringVar(value=str(val)); self.vars[key]=v
            ent=ttk.Combobox(form,textvariable=v,values=ELEMENTS,state="readonly" if key=="element" else "normal",width=20) if key=="element" else ttk.Entry(form,textvariable=v,width=23); ent.grid(row=r,column=cx*2+1,sticky="ew",padx=(0,24),pady=5)
        ttk.Button(self.editor,text="应用面板",command=self.apply_character).pack(anchor="e",padx=20,pady=12)
        tk.Label(self.editor,text="技能伤害来源",bg="white",fg="#263241",font=("Microsoft YaHei UI",11,"bold")).pack(anchor="w",padx=20,pady=(8,5)); self.talent_tree=ttk.Treeview(self.editor,columns=("name","mult","hits","reaction","result"),show="headings",height=8); self.talent_tree.pack(fill="x",padx=20)
        for h,w in zip(("技能","倍率 %","段数","反应","预计伤害"),(180,90,80,120,140)): self.talent_tree.heading(h,text=h); self.talent_tree.column(h,width=w)
        for t in c["talents"]: self.talent_tree.insert("","end",values=(t.get("name"),t.get("mult"),t.get("hits",1),t.get("reaction","无"),f"{damage(c,t):,.0f}"))
        ttk.Button(self.editor,text="添加技能",command=self.add_talent).pack(anchor="e",padx=20,pady=8)
    def apply_character(self):
        c=self.current_char
        for k,v in self.vars.items():
            try: c[k]=int(float(v.get())) if k not in ("name","element") else v.get()
            except ValueError: pass
        self.save(); self.page_characters()
    def delete_char(self,i):
        if messagebox.askyesno("删除角色","确认删除该角色？"): self.state["characters"].pop(i); self.page_characters()
    def add_talent(self):
        n=simpledialog.askstring("添加技能","技能名称：",parent=self,initialvalue="新技能")
        if n: self.current_char["talents"].append({"name":n,"kind":"E","mult":100,"hits":1,"reaction":"无"}); self.edit_character()
    def update_results(self):
        for x in self.right.winfo_children(): x.destroy()
        tk.Label(self.right,text="计算结果",bg="white",fg="#263241",font=("Microsoft YaHei UI",14,"bold")).pack(anchor="w",padx=18,pady=18)
        total,rows=total_damage(self.state); tk.Label(self.right,text=f"{total:,.0f}",bg="white",fg="#0b57d0",font=("Segoe UI",28,"bold")).pack(anchor="w",padx=18); tk.Label(self.right,text="队伍总伤害（单轮）",bg="white",fg="#7b8794").pack(anchor="w",padx=18,pady=(0,15))
        for n,s,d in rows: tk.Label(self.right,text=f"{n}  /  {s}\n{d:,.0f}",justify="left",anchor="w",bg="#f7f9fb",fg="#45515f",padx=10,pady=7).pack(fill="x",padx=14,pady=3)
    def page_weapons(self): self.library_page("武器库","weapons","武器")
    def page_artifacts(self): self.library_page("圣遗物库","artifacts","圣遗物")
    def library_page(self,title,key,label):
        self.page_base(title,f"管理自定义{label}，数据保存于当前配置"); body=tk.Frame(self.center,bg="white"); body.pack(fill="both",expand=True,padx=28,pady=12); tree=ttk.Treeview(body,columns=("name","detail"),show="headings"); tree.heading("name",text="名称"); tree.heading("detail",text="详情"); tree.pack(fill="both",expand=True,padx=18,pady=18)
        for x in self.state[key]: tree.insert("","end",values=(x.get("name","未命名"),json.dumps(x,ensure_ascii=False)[:120]))
        bar=tk.Frame(body,bg="white"); bar.pack(fill="x",padx=18,pady=(0,18)); ttk.Button(bar,text=f"添加{label}",command=lambda:self.add_library(key,label)).pack(side="left"); ttk.Button(bar,text="导入 JSON",command=lambda:self.import_library(key)).pack(side="left",padx=8); ttk.Button(bar,text="导出 JSON",command=lambda:self.export_library(key)).pack(side="left")
    def add_library(self,key,label):
        n=simpledialog.askstring(f"添加{label}",f"{label}名称：",parent=self)
        if n: self.state[key].append({"id":uid(),"name":n,"effects":[]}); self.save(); (self.page_weapons if key=="weapons" else self.page_artifacts)()
    def import_library(self,key):
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")]);
        if p:
            try: self.state[key]=json.loads(Path(p).read_text(encoding="utf-8")); self.save(); self.show_main()
            except Exception as e: messagebox.showerror("导入失败",str(e))
    def export_library(self,key):
        p=filedialog.asksaveasfilename(defaultextension=".json");
        if p: Path(p).write_text(json.dumps(self.state[key],ensure_ascii=False,indent=2),encoding="utf-8")
    def page_quick(self):
        self.page_base("快速拉表","按当前角色、技能和配置生成伤害明细"); total,rows=total_damage(self.state); tree=ttk.Treeview(self.center,columns=("char","skill","dmg"),show="headings"); tree.pack(fill="both",expand=True,padx=28,pady=10)
        for h in ("角色","伤害来源","单轮伤害"): tree.heading({"角色":"char","伤害来源":"skill","单轮伤害":"dmg"}[h],text=h)
        for n,s,d in rows: tree.insert("","end",values=(n,s,f"{d:,.2f}"))
        ttk.Button(self.center,text="导出 CSV",command=lambda:self.export_csv(rows)).pack(anchor="e",padx=28,pady=12)
    def export_csv(self,rows):
        p=filedialog.asksaveasfilename(defaultextension=".csv");
        if p:
            with open(p,"w",newline="",encoding="utf-8-sig") as f: csv.writer(f).writerows([["角色","来源","伤害"],*rows])
    def page_formula(self):
        self.page_base("计算公式总览","原生计算核心使用的通用公式"); t=tk.Text(self.center,bg="white",fg="#344054",relief="flat",font=("Consolas",11),wrap="word"); t.pack(fill="both",expand=True,padx=28,pady=12); t.insert("end", "普通伤害\n基础伤害 = 计入属性 × 倍率%\n最终伤害 = 基础伤害 × 反应区 × 伤害加成区 × 暴击区 × 防御区 × 抗性区\n\n增幅反应\n反应区 = 基础倍率 × (1 + 2.78 × 精通 / (精通 + 1400) + 反应加成)\n\n剧变反应\n伤害 = 等级系数 × 反应倍率 × (1 + 16 × 精通 / (精通 + 2000) + 反应加成) × 抗性区\n\n本版本为独立原生 GUI；配置、武器库和圣遗物库均为 JSON，可在 date 文件夹备份。")
    def page_settings(self):
        self.page_base("设置","当前配置的计算与历史记录选项"); f=tk.Frame(self.center,bg="white"); f.pack(fill="both",expand=True,padx=28,pady=12); s=self.state["settings"]
        for i,(lab,key) in enumerate((("启用时序计算","timeline"),("显示伤害占比","damage_share"))):
            v=tk.BooleanVar(value=s.get(key,True)); ttk.Checkbutton(f,text=lab,variable=v,command=lambda k=key,x=v:s.update({k:x.get()})).pack(anchor="w",padx=24,pady=12)
        tk.Label(f,text="循环时长（秒）",bg="white").pack(anchor="w",padx=24,pady=(20,3)); v=tk.IntVar(value=s.get("rotation",20)); ttk.Spinbox(f,from_=1,to=300,textvariable=v,width=10,command=lambda:s.update(rotation=v.get())).pack(anchor="w",padx=24); ttk.Button(f,text="保存设置",command=lambda:(self.save(),messagebox.showinfo("已保存","设置已保存"))).pack(anchor="w",padx=24,pady=24)
    def close(self):
        if self.state: self.save()
        self.destroy()

if __name__ == "__main__": App().mainloop()
