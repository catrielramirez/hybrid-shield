import subprocess
import json
import os

project_id = "ecommerce-police-portfolio"
service_name = "aiplatform.googleapis.com"

print(f"Obteniendo la política actual para {project_id}...")
try:
    # 1. Obtener la política actual en JSON
    result = subprocess.run(
        ["gcloud", "projects", "get-iam-policy", project_id, "--format=json"],
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        shell=True
    )
    
    policy = json.loads(result.stdout)
    
    # 2. Modificar la sección auditConfigs
    if "auditConfigs" not in policy:
        policy["auditConfigs"] = []
        
    service_config = None
    for config in policy["auditConfigs"]:
        if config.get("service") == service_name:
            service_config = config
            break
            
    if not service_config:
        service_config = {"service": service_name, "auditLogConfigs": []}
        policy["auditConfigs"].append(service_config)
        
    existing_log_types = [log.get("logType") for log in service_config["auditLogConfigs"]]
    
    for log_type in ["DATA_READ", "DATA_WRITE"]:
        if log_type not in existing_log_types:
            service_config["auditLogConfigs"].append({"logType": log_type})
            
    # 3. Escribir la política a un archivo temporal asegurando UTF-8 puro
    temp_file = "temp_iam_policy.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(policy, f, indent=2)
        
    # 4. Aplicar la nueva política
    print(f"Aplicando la nueva política para {service_name}...")
    subprocess.run(
        ["gcloud", "projects", "set-iam-policy", project_id, temp_file],
        check=True,
        shell=True
    )
    
    # Limpieza
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    print("¡Política IAM actualizada con éxito! Se habilitaron los Data Audit Logs (DATA_READ y DATA_WRITE).")

except subprocess.CalledProcessError as e:
    print(f"Error ejecutando comando de gcloud: {e}")
    if e.stderr:
        print(e.stderr)
except Exception as e:
    print(f"Error inesperado: {e}")
