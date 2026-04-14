import os
import vertexai
from vertexai.preview import reasoning_engines
from dotenv import load_dotenv
import sys

# Optional: Load env for local testing of this script
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecommerce-police-portfolio")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = f"gs://{os.getenv('GCS_BUCKET_NAME', 'ecommerce-police-portfolio-buckets')}"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

class ModeratorAgent:
    """
    Wrapper for the Semantic Shield LangGraph moderator agent to be deployed
    to Vertex AI Reasoning Engine.
    """
    def __init__(self):
        self.graph = None

    def set_up(self):
        """
        Initializes the LangGraph. This runs in the remote managed environment.
        """
        # Late imports to ensure dependencies are available in the remote environment
        # and to avoid pickling related issues during deployment.
        from backend.agents.moderator.graph import create_moderator_graph
        self.graph = create_moderator_graph()

    def query(self, input_data: dict = None, thread_id: str = None, human_feedback: dict = None) -> dict:
        """
        Entry point for the Reasoning Engine.
        
        Args:
            input_data: The initial state data for the graph (required for first call).
            thread_id: Unique session identifier for LangGraph persistence.
            human_feedback: Optional manual feedback to resume from a breakpoint.
            
        Returns:
            The final state of the graph.
        """
        if not self.graph:
            self.set_up()
            
        # Prepare config for persistence
        config = {}
        if thread_id:
            config["configurable"] = {"thread_id": thread_id}
            
        # Handle manual review (resumption)
        if human_feedback:
            # Inject feedback and clear the intervention flag
            # This replicates the update_state logic from main.py
            self.graph.update_state(
                config, 
                {"human_feedback": human_feedback, "requires_human_intervention": False}, 
                as_node="human_pause"
            )
            # Resume execution
            return self.graph.invoke(None, config)

        # Initial analysis
        if not input_data:
            raise ValueError("input_data is required for the initial analysis.")
            
        if thread_id and "thread_id" not in input_data:
            input_data["thread_id"] = thread_id
            
        return self.graph.invoke(input_data, config)

if __name__ == "__main__":
    print(f"Deploying SemanticShield_ReasoningEngine to {LOCATION}...")
    
    # Requirements file path
    # Requirements file path relative to the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    requirements_path = os.path.join(project_root, "requirements.txt")
    
    # Ensure project root is in sys.path so 'backend' can be imported
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    # Validation: Ensure backend exists and is a package
    backend_path = os.path.join(project_root, "backend")
    if not os.path.isdir(backend_path):
        raise FileNotFoundError(f"Backend directory not found at {backend_path}")
    if not os.path.exists(os.path.join(backend_path, "__init__.py")):
        print(f"Warning: {backend_path} is missing __init__.py. Reasoning Engine might fail to import it.")

    # Instantiate the agent
    agent = ModeratorAgent()
    
    # Deploy to Vertex AI Reasoning Engine
    remote_engine = reasoning_engines.ReasoningEngine.create(
        agent,
        display_name="SemanticShield_ReasoningEngine",
        requirements=requirements_path,
        # We include 'backend' as an extra package so the remote environment can find the agent logic.
        extra_packages=[backend_path]
    )
    
    print("\n" + "="*50)
    print(f"Deployment SUCCESSFUL!")
    print(f"Resource ID: {remote_engine.resource_name}")
    print("="*50)
