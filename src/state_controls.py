"""Painel Tk e texturas de dados em OpenGL; sem reconstruir a malha por horario."""
import tkinter as tk
from tkinter import ttk
import time
import numpy as np
from OpenGL import GL

class StateControls:
    def __init__(self,app):
        self.app=app
        self.weather=app.dataset.metadata["weather"]
        self.root=tk.Tk()
        self.root.title("Sao Paulo | dados meteorologicos")
        self.root.protocol("WM_DELETE_WINDOW",self.root.iconify)
        self.variable=tk.StringVar(value="Temperatura")
        self.day=tk.StringVar(value=self.weather.labels[0][:10])
        self.hour=tk.StringVar(value=self.weather.labels[0][11:])
        self.enabled=tk.BooleanVar(value=app.temperature_overlay)
        self.opacity=tk.IntVar(value=app.temperature_opacity)
        self.playing=False
        self.last_tick=time.monotonic()
        self.index=0
        self.current=None
        self.textures=GL.glGenTextures(2)
        for unit,texture in zip((1,2),self.textures):
            GL.glActiveTexture(GL.GL_TEXTURE0+unit)
            GL.glBindTexture(GL.GL_TEXTURE_2D,int(texture))
            for axis in (GL.GL_TEXTURE_WRAP_S,GL.GL_TEXTURE_WRAP_T):
                GL.glTexParameteri(GL.GL_TEXTURE_2D,axis,GL.GL_CLAMP_TO_EDGE)
            for filt in (GL.GL_TEXTURE_MIN_FILTER,GL.GL_TEXTURE_MAG_FILTER):
                GL.glTexParameteri(GL.GL_TEXTURE_2D,filt,GL.GL_NEAREST if unit==1 else GL.GL_LINEAR)
        clip=app.dataset.metadata["clip"].astype(np.float32)
        GL.glActiveTexture(GL.GL_TEXTURE1)
        GL.glBindTexture(GL.GL_TEXTURE_2D,int(self.textures[0]))
        GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_R32F,clip.shape[1],clip.shape[0],0,GL.GL_RED,GL.GL_FLOAT,clip)
        box=ttk.Frame(self.root,padding=18);box.pack(fill="both",expand=True)
        ttk.Label(box,text="SAO PAULO | ERA5-Land",font=("Arial",15,"bold")).pack(anchor="w")
        for title,var,values in [("Variavel",self.variable,["Temperatura","Precipitacao"]),("Dia (UTC)",self.day,sorted({s[:10] for s in self.weather.labels})),("Hora (UTC)",self.hour,sorted({s[11:] for s in self.weather.labels}))]:
            ttk.Label(box,text=title).pack(anchor="w",pady=(12,2))
            cb=ttk.Combobox(box,textvariable=var,values=values,state="readonly");cb.pack(fill="x")
            cb.bind("<<ComboboxSelected>>",self.select)
        row=ttk.Frame(box);row.pack(pady=12)
        ttk.Button(row,text="< Hora",command=lambda:self.step(-1)).pack(side="left")
        ttk.Button(row,text="Play / Pausa",command=self.play).pack(side="left")
        ttk.Button(row,text="Hora >",command=lambda:self.step(1)).pack(side="left")
        ttk.Checkbutton(box,text="Sobrepor dados",variable=self.enabled,command=self.overlay).pack(anchor="w")
        ttk.Label(box,text="Opacidade (%)").pack(anchor="w",pady=(10,0))
        tk.Scale(box,from_=0,to=100,orient="horizontal",variable=self.opacity,command=lambda v:self.overlay()).pack(fill="x")
        self.status=ttk.Label(box,wraplength=310);self.status.pack(anchor="w",pady=12)
        ttk.Label(box,text="Azul: menor valor | Vermelho: maior valor\nSem dados: somente textura\nTextura Sentinel: alinhamento aproximado",wraplength=310).pack(anchor="w")
        self.update_field()

    def overlay(self):
        self.app.temperature_overlay=self.enabled.get()
        self.app.temperature_opacity=self.opacity.get()

    def select(self,event=None):
        label=self.day.get()+" "+self.hour.get()
        if label in self.weather.labels:
            self.index=self.weather.labels.index(label)
        self.update_field()

    def step(self,delta):
        self.index=max(0,min(len(self.weather.times)-1,self.index+delta))
        self.day.set(self.weather.labels[self.index][:10]);self.hour.set(self.weather.labels[self.index][11:])
        self.update_field()

    def play(self):
        self.playing=not self.playing
        self.last_tick=time.monotonic()

    def update_field(self):
        variable=self.variable.get()
        a=self.weather.frame(variable,self.index)
        valid=np.isfinite(a)
        packed=np.stack((np.where(valid,a,0),valid.astype(np.float32)),axis=-1).astype(np.float32)
        GL.glActiveTexture(GL.GL_TEXTURE2)
        GL.glBindTexture(GL.GL_TEXTURE_2D,int(self.textures[1]))
        GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_RG32F,a.shape[1],a.shape[0],0,GL.GL_RG,GL.GL_FLOAT,packed)
        low,high=self.weather.ranges[variable]
        self.app.render_config["temperature_min"]=low
        self.app.render_config["temperature_max"]=max(high,low+1)
        units="C" if variable=="Temperatura" else "mm na hora encerrada"
        self.app.temperature_label=f"{variable}: {self.weather.labels[self.index]} UTC | {units}"
        note="" if valid.any() else "\nHorario sem dados para esta variavel."
        self.status.config(text=f"{self.weather.labels[self.index]} UTC\nEscala fixa: {low:g} a {high:g} {units}{note}")

    def update(self):
        self.enabled.set(self.app.temperature_overlay)
        self.opacity.set(self.app.temperature_opacity)
        self.root.update()
        if self.playing and time.monotonic()-self.last_tick>=0.6:
            self.last_tick=time.monotonic()
            self.step(1)
            if self.index==len(self.weather.times)-1:self.playing=False

    def bind(self):
        for unit,texture in zip((1,2),self.textures):
            GL.glActiveTexture(GL.GL_TEXTURE0+unit)
            GL.glBindTexture(GL.GL_TEXTURE_2D,int(texture))
        shader=self.app.shader
        shader.set_int("u_state",1)
        shader.set_int("u_clip",1)
        shader.set_int("u_field",2)
        shader.set_vec4("u_grid_mapping",(1/self.app.terrain_cpu.world_size,1/self.app.terrain_cpu.world_depth,0,0))

    def delete(self):
        GL.glDeleteTextures(self.textures)
        self.root.destroy()
