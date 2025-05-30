import json
from pathlib import Path
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader


PATH = Path(__file__).parent.parent.resolve()
CONFIG_DIR = PATH / "data" / "configs"
TEMPLATES_DIR = PATH / "templates"
CURRENT_DIR = Path.cwd()
ENV = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), keep_trailing_newline=True) # Charger le répertoire des templates

def load_intention(path: Path) -> Dict[str, Any]:
    """
    Charge et renvoie le dictionnaire d'intention à partir d'un fichier JSON.
    """
    with open(path, 'r') as f:
        return json.load(f)

def render_and_write(device: str, details: Dict[str, Any], templates: Dict[str, str]) -> Path:
    """
    Rend et écrit la configuration pour un device donné selon son rôle.
    Retourne le chemin du fichier généré.
    """
    # Choix du template
    tmpl = ENV.get_template(templates.get(details['role']))

    if not tmpl:
        raise ValueError(f"No template found for role '{details['role']}' in device '{device}'.")

    # Passage en json-serializable
    to_render = json.loads(json.dumps(details, default=str))
    config_text = tmpl.render(to_render)

    # Ecriture fichier
    path = CONFIG_DIR / f"{device}.cfg"
    with open(path, 'w') as f:
        f.write(config_text)
    return path
