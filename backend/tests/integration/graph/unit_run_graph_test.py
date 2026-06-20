"""
Script to test the LangGraph moderator pipeline step-by-step using examples from metadata.json.
"""
import os
import sys
import json
import asyncio
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno correctamente desde la raíz
load_dotenv(find_dotenv())

# Fix para poder ejecutar con: python backend/tests/integration/graph/unit_run_graph_test.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from backend.agents.moderator.graph import HybridShieldAgent


class GraphTester:
    def __init__(self, metadata_path: str, bucket_name: str = "ecommerce-police-portfolio-golden-dataset"):
        self.metadata_path = metadata_path
        self.bucket_name = bucket_name
        self.metadata = self._load_metadata()
        self.app = None

    async def initialize(self):
        from unittest.mock import AsyncMock, patch
        from langgraph.checkpoint.memory import MemorySaver
        agent = HybridShieldAgent()
        mock_cp = AsyncMock(return_value=MemorySaver())
        with patch.object(agent, '_initialize_checkpointer', mock_cp):
            self.app = await agent._build_graph()

    def _load_metadata(self) -> Dict[int, Dict[str, Any]]:
        if not os.path.exists(self.metadata_path):
            print(f"Error: metadata file not found at {self.metadata_path}")
            return {}
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {item["id"]: item for item in data}
        except Exception as e:
            print(f"Error loading metadata from {self.metadata_path}: {e}")
            return {}

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        return self.metadata.get(item_id)

    async def run_step_by_step(self, item_id: int) -> None:
        item = self.get_item(item_id)
        if not item:
            print(f"Item with ID {item_id} not found in metadata.")
            return

        print("-" * 50)
        print(f"Starting graph test for Item ID: {item_id}")
        print(f"Category: {item.get('category')}")
        print(f"Title: {item.get('input_data', {}).get('title')}")
        print(f"Expected Label: {item.get('label')}")
        print("-" * 50 + "\n")

        gcs_uri = f"gs://{self.bucket_name}/{item['file_path']}"

        initial_state = {
            "input_data": item["input_data"],
            "gcs_uri": gcs_uri,
            "thread_id": f"test_thread_id_{item_id}"
        }

        config = {"configurable": {"thread_id": f"test_thread_id_{item_id}"}}

        print("Streaming graph execution step-by-step...\n")
        try:
            async for event in self.app.astream(initial_state, config=config, stream_mode="updates"):
                for node_name, node_state in event.items():
                    print(f"Node executed: [{node_name.upper()}]")

                    if node_name == "__interrupt__":
                        print(f"  ↳ Interrupt data: {node_state}")
                        print("-" * 50)
                        continue

                    for key, value in node_state.items():
                        if isinstance(value, (dict, list)):
                            try:
                                formatted_val = json.dumps(value, indent=2, ensure_ascii=False)
                                formatted_val = formatted_val.replace('\n', '\n      ')
                                print(f"  ↳ {key}:\n      {formatted_val}")
                            except (TypeError, ValueError):
                                print(f"  ↳ {key}: {value}")
                        else:
                            print(f"  ↳ {key}: {value}")

                    print("-" * 50)

            final_snapshot = self.app.get_state(config)
            if final_snapshot.next:
                print(f"\nGraph execution paused (Interrupt). Next pending node: {final_snapshot.next}")
                print(f"  State requires human intervention: {final_snapshot.values.get('requires_human_intervention')}")
            else:
                print("\nGraph execution completed successfully without pending interruptions.")

        except Exception as e:
            print(f"\nError during graph execution: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Test LangGraph Moderator Pipeline Step-by-Step")
    parser.add_argument("--id", type=int, default=89, help="Item ID from metadata to test")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    metadata_path = os.path.join(project_root, "data", "balanced", "metadata.json")

    tester = GraphTester(metadata_path=metadata_path)
    await tester.initialize()
    await tester.run_step_by_step(args.id)


if __name__ == "__main__":
    asyncio.run(main())