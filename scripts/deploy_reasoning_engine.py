import os
import sys
import vertexai
from vertexai import agent_engines

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.moderator.builder import moderator_runnable_builder


def create_agent_instance():
    return agent_engines.LanggraphAgent(
        model="gemini-1.5-flash-001",
        runnable_builder=moderator_runnable_builder,
    )


if __name__ == "__main__":
    PROJECT_ID = "ecommerce-police-portfolio"
    LOCATION = "us-central1"
    STAGING_BUCKET = "gs://ecommerce-police-portfolio-buckets"

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    print("Iniciando despliegue estándar Agent Runtime 2026 (LangGraphAgent)...")

    try:
        local_agent = create_agent_instance()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        requirements_path = os.path.join(script_dir, "requirements_reasoning_engine.txt")
        print("Requirements:", requirements_path)

        remote_agent = agent_engines.create(
            agent_engine=local_agent,
            requirements=requirements_path,
            extra_packages=["backend"],
            display_name="SemanticShield_LangGraph_AgentRuntime_2026",
            description="Agente de moderación semántica basado en LangGraph",
            min_instances=1,
            max_instances=10,
            resource_limits={"cpu": "4", "memory": "4Gi"},
            container_concurrency=9,
        )

        print("\n" + "=" * 60)
        print("DESPLIEGUE EXITOSO")
        print(f"Resource Name: {remote_agent.api_resource.name}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR durante el despliegue: {type(e).__name__}")
        print(str(e))