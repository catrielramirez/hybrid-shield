import os
import sys
from pathlib import Path
import pytest
from dotenv import load_dotenv
import json
import uuid

load_dotenv()
sys.path.append(str(Path(__file__).parents[4]))

from backend.agents.moderator.graph import HybridShieldAgent

class TestModeratorFlowVisualizer:
    """
    Script de depuración para visualizar el rastro de datos (input/output) 
    de cada nodo en el grafo de moderación.
    """

    @pytest.mark.asyncio
    async def test_visualize_graph_flow(self):
        # Setup del grafo y configuración de persistencia
        app = await HybridShieldAgent()._build_graph()
        thread_id = f"debug_flow_{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": thread_id}}

        # Datos de entrada para la simulación
        initial_input = {
            "input_data": {
                "title": "Piloto de lluvia para perro",
                "price": 250.0,
                "description": "en varios colores"
            },
            "gcs_uri": "gs://ecommerce-police-portfolio-buckets/imagenes_ingesta/2026/04/27/a7f38d94-a73a-4e6f-b582-74d277fe3f7c_20250527_1347_Fashionable Dog in Raincoat_remix_01jw9a6pj0f3wtjq9egxypdqw8.png"
        }

        print(f"\nINICIO DE TRAZA: {thread_id}")
        print("-" * 80)

        try:
            # El modo 'updates' permite ver solo lo que el nodo retorna en ese paso
            async for event in app.astream(initial_input, config, stream_mode="updates"):
                for node_name, output in event.items():
                    print(f"\nNODO: {node_name.upper()}")
                    print("-" * 20)
                    
                    # Muestra el diccionario exacto que el nodo inyecta al estado
                    print(f"OUTPUT DEL NODO '{node_name}':")
                    print(json.dumps(output, indent=4, ensure_ascii=False))
                    
                    # Verificación de las llaves presentes en el estado global tras la ejecución del nodo
                    state_now = await app.aget_state(config)
                    print(f"\nESTADO ACTUAL (Keys): {list(state_now.values.keys())}")
                    print("-" * 40)

        except Exception as e:
            print(f"ERROR EN FLUJO: {str(e)}")
            raise e

        print("\nPROCESO FINALIZADO")
        print("-" * 80)

if __name__ == "__main__":
    pytest.main(["-s", __file__])