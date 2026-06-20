import cloudpickle
import sys
import os

# Forzamos la ruta del backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.moderator.graph import HybridShieldAgent

try:
    print("Intentando serializar el agente localmente...")
    agente = HybridShieldAgent()
    
    # Simulamos el empaquetado de Vertex AI
    congelado = cloudpickle.dumps(agente)
    
    print("Intentando deserializar el agente...")
    descongelado = cloudpickle.loads(congelado)
    
    print("Validacion exitosa: La estructura de tu agente es 100% compatible con Vertex AI.")
except Exception as e:
    print("Error critico de serializacion detectado:")
    print(str(e))