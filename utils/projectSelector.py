from tkinter import Tk, ttk
from gns3fy import Gns3Connector, Project

class ProjectSelector:
    def __init__(self, gns3_server: Gns3Connector):
        self.server = gns3_server
        self.project_name = None

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
    
    def get_project(self, project_name: str = None) -> Project:
        if not project_name:
            project_name = self.get_project_infos()
        if project_name:
            try:
                project = Project(name=project_name, connector=self.server)
                return project
            except Exception as e:
                print(f"Error retrieving project: {e}")
        else:
            print("No project selected. Exiting.")
        return None