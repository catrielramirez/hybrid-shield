import os

def load_prompt(prompt_name: str) -> str:
    """Carga un prompt desde la carpeta de prompts."""
    # Obtenemos la ruta del directorio donde está este archivo utils
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # current_dir es: .../backend/agents/moderator/utils
    # Queremos llegar a: .../backend/agents/moderator/prompts
    # Subimos un nivel ('..') para salir de 'utils' y entrar en 'moderator'
    base_path = os.path.join(current_dir, "..", "prompts")
    
    file_path = os.path.abspath(os.path.join(base_path, f"{prompt_name}.md"))
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo en: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()