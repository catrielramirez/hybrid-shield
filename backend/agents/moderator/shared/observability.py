import time
import logging
import asyncio
from typing import Optional
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger("moderation_pipeline")

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("moderation_pipeline")
except ImportError:
    # Fallback to a dummy tracer if opentelemetry is not installed (e.g. in some remote environments)
    import contextlib
    class DummyTracer:
        @contextlib.contextmanager
        def start_as_current_span(self, name, *args, **kwargs):
            yield None
    tracer = DummyTracer()


def measure_latency(span_name: Optional[str] = None):
    """Decorator to measure and log node execution time and trace spans (Sync/Async)."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def wrapper(state, config: RunnableConfig, *args, **kwargs):
                nonlocal span_name
                actual_span_name = span_name or func.__name__.replace("_node", "")
                pipeline_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id", "unknown")
                print(f"[NODE_START] Node '{actual_span_name}' starting for pipeline '{pipeline_id}'", flush=True)
                logger.info(f"[NODE_START] Node '{actual_span_name}' starting for pipeline '{pipeline_id}'")
                with tracer.start_as_current_span(actual_span_name):
                    start_time = time.time()
                    try:
                        result = await func(state, config, *args, **kwargs)
                        latency_ms = (time.time() - start_time) * 1000
                        logger.info("node_latency", extra={"node": actual_span_name, "latency_ms": latency_ms, "pipeline_id": pipeline_id})
                        
                        if isinstance(result, dict):
                            metrics = result.setdefault("execution_metrics", {})
                            nodes = metrics.setdefault("nodes", {})
                            node_metrics = nodes.setdefault(actual_span_name, {})
                            node_metrics["latency_ms"] = latency_ms
                            
                        print(f"[NODE_END] Node '{actual_span_name}' completed successfully for pipeline '{pipeline_id}'", flush=True)
                        logger.info(f"[NODE_END] Node '{actual_span_name}' completed successfully for pipeline '{pipeline_id}'")
                        return result
                    except Exception as e:
                        print(f"[NODE_ERROR] Node '{actual_span_name}' failed with error: {e} for pipeline '{pipeline_id}'", flush=True)
                        logger.error(f"[NODE_ERROR] Node '{actual_span_name}' failed with error: {e} for pipeline '{pipeline_id}'", exc_info=True)
                        raise e
            return wrapper
        else:
            def wrapper(state, config: RunnableConfig, *args, **kwargs):
                nonlocal span_name
                actual_span_name = span_name or func.__name__.replace("_node", "")
                pipeline_id = config.get("configurable", {}).get("thread_id") or state.get("thread_id", "unknown")
                print(f"[NODE_START] Node '{actual_span_name}' starting for pipeline '{pipeline_id}'", flush=True)
                logger.info(f"[NODE_START] Node '{actual_span_name}' starting for pipeline '{pipeline_id}'")
                with tracer.start_as_current_span(actual_span_name):
                    start_time = time.time()
                    try:
                        result = func(state, config, *args, **kwargs)
                        latency_ms = (time.time() - start_time) * 1000
                        logger.info("node_latency", extra={"node": actual_span_name, "latency_ms": latency_ms, "pipeline_id": pipeline_id})
                        
                        if isinstance(result, dict):
                            metrics = result.setdefault("execution_metrics", {})
                            nodes = metrics.setdefault("nodes", {})
                            node_metrics = nodes.setdefault(actual_span_name, {})
                            node_metrics["latency_ms"] = latency_ms
                            
                        print(f"[NODE_END] Node '{actual_span_name}' completed successfully for pipeline '{pipeline_id}'", flush=True)
                        logger.info(f"[NODE_END] Node '{actual_span_name}' completed successfully for pipeline '{pipeline_id}'")
                        return result
                    except Exception as e:
                        print(f"[NODE_ERROR] Node '{actual_span_name}' failed with error: {e} for pipeline '{pipeline_id}'", flush=True)
                        logger.error(f"[NODE_ERROR] Node '{actual_span_name}' failed with error: {e} for pipeline '{pipeline_id}'", exc_info=True)
                        raise e
            return wrapper
    return decorator
