"""Pantalla de entrada y cierre de sesión de la demo."""
import tkinter as tk
from tkinter import ttk
from dzone_auth import authenticate, revoke


class LoginActions:
    def show_login(self):
        self.session=None
        self.title('Dzone · Iniciar sesión')
        self.geometry('1100x760');self.minsize(960,640)
        for child in self.winfo_children():child.destroy()
        shell=tk.Frame(self,bg='#f2f5fa');shell.pack(fill='both',expand=True)
        brand=tk.Frame(shell,bg='#14243b',width=360);brand.pack(side='left',fill='y');brand.pack_propagate(False)
        tk.Label(brand,text='DZONE',font=('Segoe UI',32,'bold'),fg='white',bg='#14243b').pack(anchor='w',padx=36,pady=(75,12))
        tk.Label(brand,text='Cada tarea,\nen las manos correctas.',font=('Segoe UI',22,'bold'),fg='white',bg='#14243b',justify='left').pack(anchor='w',padx=36,pady=15)
        tk.Label(brand,text='Asigna · Atiende · Documenta · Valida',font=('Segoe UI',11),fg='#a8bdd7',bg='#14243b',wraplength=290,justify='left').pack(anchor='w',padx=36,pady=20)
        area=tk.Frame(shell,bg='white');area.pack(side='left',fill='both',expand=True,padx=40,pady=50)
        tk.Label(area,text='Bienvenido a Dzone',bg='white',fg='#14243b',font=('Segoe UI',24,'bold')).pack(anchor='w',padx=28,pady=(36,8))
        tk.Label(area,text='Ingresa con tu cuenta de demostración.',bg='white',fg='#59697f',font=('Segoe UI',11)).pack(anchor='w',padx=28,pady=(0,20))
        self.login_user=tk.StringVar();self.login_password=tk.StringVar();self.login_error=tk.StringVar()
        for label,var,secret in [('Usuario',self.login_user,False),('Contraseña',self.login_password,True)]:
            tk.Label(area,text=label,bg='white',fg='#14243b',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=28,pady=(12,6))
            entry=ttk.Entry(area,textvariable=var,show='●' if secret else '',font=('Segoe UI',13))
            entry.pack(fill='x',padx=28,ipady=7);entry.bind('<Return>',lambda e:self.login(self.login_user.get(),self.login_password.get()))
            if not secret:entry.focus_set()
        tk.Label(area,textvariable=self.login_error,bg='white',fg='#b42318',wraplength=380,justify='left').pack(anchor='w',padx=28,pady=10)
        self.button(area,'Iniciar sesión',lambda:self.login(self.login_user.get(),self.login_password.get()),True).pack(fill='x',padx=28,pady=10)
        tk.Label(area,text='Cuentas de prueba\nSupervisor: demo0 / demo0\nTécnicos: demo1 / demo1 hasta demo4 / demo4',bg='#edf3fb',fg='#475467',font=('Segoe UI',10),justify='left',padx=16,pady=16).pack(fill='x',padx=28,pady=22)

    def login(self,username,password):
        try:session=authenticate(username,password)
        except ValueError as exc:
            self.login_error.set(str(exc));self.login_password.set('');return False
        self.login_password.set('');self.session=session
        for child in self.winfo_children():child.destroy()
        self.build_workspace();return True

    def logout(self):
        revoke(self.session)
        self.session=None
        self.show_login()
