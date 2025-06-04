from __future__ import annotations
from typing import List, Dict, Tuple, Union, Any

import os
import json
import sys
import time
from pathlib import Path
from traceback import format_exc
from concurrent.futures import ThreadPoolExecutor, as_completed

from ipaddress import IPv4Network
from gns3fy import Project
from jinja2 import Environment, FileSystemLoader

from tools.generate_config import generate_configs


PATH = Path(__file__).parent.resolve()

os.chdir(PATH)

from lib.fileDialog import FileDialog
from lib.ui import ProjectSelector, MessageBox
from lib.telnetClient import SessionManager
from lib.argParser import parse_args

from tools.files_management import CONFIG_DIR, CURRENT_DIR


if __name__ == "__main__":

    print("""
/==================================================\\
||   ____        _   _    _    ____  _            ||
||  |  _ \ _   _| \ | |  / \  / ___|| |_ _   _    ||
||  | | | | | | |  \| | / _ \ \___ \| __| | | |   ||
||  | |_| | |_| | |\  |/ ___ \ ___) | |_| |_| |   ||
||  |____/ \__, |_| \_/_/   \_\____/ \__|\__, |   ||
||         |___/ Lise, Ethan PJ & Mathéo |___/    ||
\==================================================/
""")
    # Parser les arguments en ligne de commande
    args = parse_args()

    # Si le fichier d'intention n'est pas spécifié, ouvrir une boîte de dialogue pour le sélectionner
    if not args.file:
        file_dialog = FileDialog()
        selected_file = Path(file_dialog.select_json_file())
    else:
        # Rendre le chemin absolu
        selected_file = Path(args.file)
        if not selected_file.is_absolute():
            selected_file = CURRENT_DIR / selected_file

    # Vérifier si le fichier  a bien été sélectionné
    if not selected_file:
        print("No file selected. Exiting.")
        exit()

    # Vérifier si le fichier existe
    if not selected_file.exists():
        print(f"File {selected_file} does not exist. Exiting.")
        exit()
    
    # Vérifier si le fichier est un fichier JSON*
    try:
        with open(selected_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading JSON file: {e}. Please check the file format.")
        exit()

    # TODO: Validation du fichier d'intention

    # Générer les configurations à partir du fichier d'intention
    try:
        config_files: dict[str, Path] = generate_configs(data)
    except KeyError as e:
        print(f"An Error occured: KeyError: {e}. Please check the intention file.")
        print("A relation in the intention file might be missing or corrupted.")
        exit()

    print(f"Configurations saved to {CONFIG_DIR}.")

    # Open the file explorer to the config directory
    if args.opendir:
        os.startfile(str(CONFIG_DIR))
        time.sleep(1.5)

    # Automatically push the configs to GNS3 (not implemented yet)
    if args.push is None:
        push = MessageBox("Push configurations to GNS3", "Do you want to push the configurations to GNS3?").prompt()
    if args.push:
        print("Pushing configurations to GNS3.")

        selector = ProjectSelector(url="http://localhost:3080", user="admin", cred="admin")

        if args.push is True:
            project: Project = selector.get_project()
        else:
            project: Project = selector.get_project(args.push)
        
        if project:
            # Make sure the project is running
            if not project.status == "running":
                project.open()
                print(f"Opened project \"{project.name}\".")

            # Make sure all nodes are up
            project.start_nodes()

            # Get all the nodes in the project
            nodes = project.nodes
            
            # Push the configurations using the SessionManager
            session_manager = SessionManager()
            print(f"Pushing configurations to {len(nodes)} nodes.\n\n\n")
            for node in nodes:
                node_name = node.name
                node_host = node.console_host
                node_port = node.console
                config_file = config_files.get(node_name)
                if not config_file or not config_file.exists():
                    print(f"Missing config for {node_name}")
                    continue
                if not node_host or not node_port:
                    print(f"Missing host/port for {node_name}")
                    continue
                session_manager.push_configuration(node_name, node_host, node_port, config_file.read_text())
            
            while not session_manager.all_done():
                try:
                    session_manager.status(flush=True)
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    session_manager.terminate_all()
                    print("Terminating all sessions...")
                    sys.exit(0)
            else:
                session_manager.status(flush=True)
            print("All configurations pushed.")
        else:
            print("No project selected. Exiting.")
    
    exit()