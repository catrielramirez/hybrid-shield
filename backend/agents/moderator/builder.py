from .graph import create_moderator_graph

def moderator_runnable_builder(model, **kwargs):
    """
    Custom runnable_builder for LanggraphAgent.
    
    Builds and returns the compiled Semantic Shield moderator graph.
    The `model` param is provided by LanggraphAgent internals but is
    unused here — our graph nodes call Vertex AI models directly via
    ai_service, not through a LangChain chat model.
    """
    return create_moderator_graph()
