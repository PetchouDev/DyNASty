from tkinter import Tk, ttk, Frame
from gns3fy import Gns3Connector, Project
from tkinter import messagebox

class ProjectSelector():
    def __init__(self, **kwargs):
        self.server = Gns3Connector(**kwargs)
        self.project_name = None
        self.project = None

    # Callback function
    def __callback(self):
        self.project_name = self.combo.get()
        self.root.destroy()

    def get_project_infos(self) -> tuple[str, str, int, int, str]:
        projects = self.server.projects_summary(is_print=False)
        
        # Create root window
        self.root = Tk()
        self.root.title("Select GNS3 Project")
        self.root.geometry("250x130")
        self.root.eval('tk::PlaceWindow . center')
        self.root.attributes("-topmost", True)
        
        # Label
        self.label = ttk.Label(self.root, text="Select a project:", font=("Arial", 12, "bold"))
        self.label.pack(pady=10)
        
        # Combo box
        self.combo = ttk.Combobox(self.root, values=[project[0] for project in projects], font=("Arial", 10))
        self.combo.set("Select a project")
        self.combo.pack(pady=5)
        self.combo.focus()
        
        # Button
        self.btn = ttk.Button(self.root, text="OK", command=self.__callback)
        self.btn.pack(pady=10)
        
        # Bind keys
        self.btn.bind("<Return>", lambda event: self.__callback())
        self.btn.bind("<Escape>", lambda event: self.root.destroy())
        self.btn.bind("<Button-1>", lambda event: self.__callback())
        
        # Display the window
        self.root.update()
        self.root.deiconify()
        self.root.wait_window()
        
        return self.project_name if self.project_name and self.project_name != "Select a project" else None
    
    def get_project_uuid(self, project_name: str = None) -> str:
        if not project_name:
            project_name = self.get_project_infos()
        if project_name:
            try:
                projects = self.server.projects_summary(is_print=False)
                for project in projects:
                    if project[0] == project_name:
                        return project[1]
            except Exception as e:
                print(f"Error retrieving project UUID: {e}")
        else:
            print("No project selected. Exiting.")
        return None
    
    def get_project(self, project_name: str = None) -> Project:
        if not project_name:
            project_name = self.get_project_infos()
        if project_name:
            try:
                project_uuid = self.get_project_uuid(project_name)
                if not project_uuid:
                    raise ValueError("Project UUID not found.")
                self.project = Project(project_id=project_uuid, connector=self.server)
                return self.project
            except Exception as e:
                print(f"Error retrieving project: {e}")
        else:
            print("No project selected. Exiting.")
        return None


from tkinter import Tk, Label, Button

class MessageBox:
    def __init__(self, title: str = "", message: str = ""):
        self.root = Tk()
        self.root.title(title)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.result = False

        self.root.geometry("400x100")
        self.root.eval('tk::PlaceWindow . center')
        self.root.bind("<Escape>", lambda event: self.no())

        Label(self.root, text=message, padx=20, pady=10).pack()
        btn_frame = Frame(self.root)
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Yes", width=10, command=self.yes).pack(side="left", padx=5)
        Button(btn_frame, text="No", width=10, command=self.no).pack(side="right", padx=5)

    def yes(self):
        self.result = True
        self.root.quit()
        self.root.destroy()

    def no(self):
        self.result = False
        self.root.quit()
        self.root.destroy()

    def prompt(self) -> bool:
        self.root.mainloop()
        return self.result


# Test the MessageBox class
if __name__ == "__main__":
    msg_box = MessageBox("Test", "This is a test message.").prompt()
    print(f"User response: {msg_box}")
