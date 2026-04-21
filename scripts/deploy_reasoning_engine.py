import os
import sys
import shutil
from pathlib import Path
import vertexai
from vertexai import agent_engines
from dotenv import load_dotenv

# Ensure the project root is in sys.path for backend imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.agents.moderator.builder import moderator_runnable_builder

# Optional: Load env for local testing of this script
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = f"gs://{os.getenv('GCS_BUCKET_NAME', 'ecommerce-police-portfolio-buckets')}"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)


def cleanup_backend():
    """Recursively removes all __pycache__ directories and .pyc files in the backend folder."""
    backend_dir = Path(project_root) / "backend"
    if not backend_dir.exists():
        return

    print(f"Cleaning up cache in {backend_dir}...")
    count_dirs = 0
    count_files = 0
    
    for pycache in backend_dir.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache)
            count_dirs += 1
            
    for pyc in backend_dir.rglob("*.pyc"):
        pyc.unlink()
        count_files += 1
        
    print(f"Removed {count_dirs} __pycache__ directories and {count_files} .pyc files.")

if __name__ == "__main__":
    cleanup_backend()
    
    print(f"\nDeploying SemanticShield to Vertex AI Agent Engine in {LOCATION}...")
    print(f"Monitor build progress at: https://console.cloud.google.com/cloud-build/builds?project={PROJECT_ID}")
    print("-" * 50)
    
    # Requirements file path relative to the project root
    requirements_path = os.path.join(project_root, "scripts", "requirements_reasoning_engine.txt")
    
    # Validation: Ensure backend exists and is a package
    backend_path = os.path.join(project_root, "backend")
    if not os.path.isdir(backend_path):
        raise FileNotFoundError(f"Backend directory not found at {backend_path}")
    if not os.path.exists(os.path.join(backend_path, "__init__.py")):
        raise FileNotFoundError(f"{backend_path} is missing __init__.py — required for extra_packages.")

    # Instantiate LanggraphAgent with custom runnable_builder.
    # model is required by LanggraphAgent but unused in our builder —
    # we pass a valid model name so the SDK doesn't fail on validation.
    agent = agent_engines.LanggraphAgent(
        model="gemini-2.0-flash",
        runnable_builder=moderator_runnable_builder,
    )
    
    # Deploy to Vertex AI Agent Engine
    # Use relative path for extra_packages to ensure consistent behavior in the remote container
    os.chdir(project_root)
    remote_engine = agent_engines.create(
        agent_engine=agent,
        display_name="SemanticShield_AgentEngine",
        requirements=requirements_path,
        extra_packages=["backend"],
    )
    
    print("\n" + "="*50)
    print(f"Deployment SUCCESSFUL!")
    print(f"Resource ID: {remote_engine.resource_name}")
    print("="*50)
