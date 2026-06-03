import os
import sys
import json
import time
import uuid
import shutil
import logging
import statistics
import hashlib
import asyncio
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

# --- Rutas del Proyecto ---
PROJECT_ROOT = os.getcwd()
sys.path.insert(0, PROJECT_ROOT)

from backend.agents.moderator.graph import HybridShieldAgent
from backend.shared.image_utils import optimize_image

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("eval_framework")

# --- Configuracion GCP ---
BUCKET_NAME       = os.getenv("GOOGLE_CLOUD_BUCKET", "ecommerce-police-portfolio-golden-dataset")
RESULTS_DIR       = os.path.join(PROJECT_ROOT, "backend/tests/evals/results")

# --- Directorio local de datos ---
LOCAL_DATASET_DIR = os.path.join(PROJECT_ROOT, "data")

# --- Outcomes que se consideran "no paso" ---
FAILED_OUTCOMES = {"FP", "FN"}

# --- Modelo y Precios ---
MODEL_NAME      = "Gemini 3.1 Flash-Lite"
PRICE_INPUT_1M  = 0.25
PRICE_OUTPUT_1M = 1.50

# --- Nodos que hacen llamadas LLM (tienen costos reales) ---
LLM_NODES = {"pre_filter", "extractor", "reasoning"}

# --- Umbrales de Evaluacion ---
MIN_PRECISION       = 0.85
MIN_RECALL          = 0.90
MIN_F1              = 0.87
MAX_ERROR_RATE      = 0.05
MAX_P95_LATENCY_MS  = 36000.0
MIN_AUTOMATION_RATE = 0.80
MAX_CONCURRENT_EVALS = 2

# --- Valores validos de final_action del AgentState ---
ACTION_BLOCK        = "Block"
ACTION_APPROVE      = "Approve"
ACTION_HUMAN_REVIEW = {"Human Review", "Pending"}

# --- Orden canónico de nodos para tablas ---
NODE_ORDER = ["pre_filter", "extractor", "rag", "risk_evaluator", "reasoning", "decision", "fly_wheel"]


class ModeratorEvaluator:

    def __init__(self, bucket_name: str, results_dir: str, eval_tier: str = "balanced"):
        self.bucket_name    = bucket_name
        self.results_dir    = results_dir
        self.eval_tier      = eval_tier
        self.storage_client = storage.Client()
        self.app            = None

    def _resolve_local_path(self, file_path: str) -> str:
        if not file_path:
            return ""
        # Remueve cualquier extensión previa para quedarse con el nombre base (ej. "balanced/blocked/059")
        base_path, _ = os.path.splitext(file_path)
        
        # Extensiones candidatas a verificar en el disco
        extensions = [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG"]
        for ext in extensions:
            full_path = os.path.join(LOCAL_DATASET_DIR, base_path + ext)
            if os.path.isfile(full_path):
                return full_path
                
        # Si no encuentra ninguna variación, retorna la ruta original como fallback
        return os.path.join(LOCAL_DATASET_DIR, file_path)

    # ------------------------------------------------------------------
    # Carga de Dataset
    # ------------------------------------------------------------------

    def _load_metadata_local(self) -> tuple[list, str]:
        if self.eval_tier == "balanced":
            path = os.path.join(LOCAL_DATASET_DIR, "balanced", "metadata.json")
        else:
            path = os.path.join(LOCAL_DATASET_DIR, "evals", self.eval_tier, "metadata.json")

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No se encontró el archivo de metadatos para el tier '{self.eval_tier}' "
                f"en la ruta: {path}. Asegúrate de haber corrido el script sampler primero."
            )

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        dataset_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return json.loads(content), dataset_hash

    # ------------------------------------------------------------------
    # Calculo de Costos y Tokens
    # ------------------------------------------------------------------

    def _calculate_item_metrics(self, execution_metrics: dict) -> tuple[float, dict, dict]:
        node_costs  = {}
        node_tokens = {}
        total_cost  = 0.0

        for node_name, usage in execution_metrics.get("nodes", {}).items():
            p    = usage.get("prompt_tokens", 0)
            c    = usage.get("candidates_tokens", 0)
            cost = (p / 1_000_000) * PRICE_INPUT_1M + (c / 1_000_000) * PRICE_OUTPUT_1M

            node_costs[node_name]  = round(cost, 6)
            node_tokens[node_name] = {"prompt": p, "candidates": c}
            total_cost += cost

        if total_cost == 0.0:
            totals     = execution_metrics.get("totals", {})
            total_cost = (
                (totals.get("prompt_tokens", 0)     / 1_000_000) * PRICE_INPUT_1M +
                (totals.get("candidates_tokens", 0) / 1_000_000) * PRICE_OUTPUT_1M
            )

        return round(total_cost, 6), node_costs, node_tokens

    # ------------------------------------------------------------------
    # Agregacion de Latencias por Nodo
    # ------------------------------------------------------------------

    def _aggregate_node_latencies(self, results: list) -> dict:
        """Calcula avg y P95 de latencia por nodo across todos los items."""
        node_latency_lists = {}

        for r in results:
            for node_name, metrics in r.get("node_metrics", {}).items():
                lat = metrics.get("latency_ms")
                if lat is not None:
                    node_latency_lists.setdefault(node_name, []).append(lat)

        aggregated = {}
        for node, lats in node_latency_lists.items():
            sorted_lats = sorted(lats)
            p95_idx     = int(len(sorted_lats) * 0.95)
            aggregated[node] = {
                "avg_ms": round(statistics.mean(lats), 1),
                "p95_ms": round(sorted_lats[min(p95_idx, len(sorted_lats) - 1)], 1),
                "min_ms": round(sorted_lats[0], 1),
                "max_ms": round(sorted_lats[-1], 1),
            }

        return aggregated

    # ------------------------------------------------------------------
    # Visualizaciones
    # ------------------------------------------------------------------

    def _generate_plots(self, summary: dict, latencies: list, node_latencies: dict, output_dir: str):
        sns.set_theme(style="whitegrid")

        # --- 1. Confusion Matrix ---
        cm      = summary["confusion_matrix"]
        cm_data = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])

        plt.figure(figsize=(6, 5))
        sns.heatmap(
            cm_data, annot=True, fmt="d", cmap="Blues", cbar=False,
            xticklabels=["Predicted Pass", "Predicted Block"],
            yticklabels=["Actual Pass", "Actual Block"]
        )
        plt.title(f"Confusion Matrix — {self.eval_tier}", pad=20, fontsize=14)
        plt.ylabel("Ground Truth")
        plt.xlabel("Model Prediction")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"confusion_matrix_{self.eval_tier}.png"), dpi=300)
        plt.close()

        # --- 2. Latency Distribution (total por item) ---
        if latencies:
            plt.figure(figsize=(8, 4))
            sns.histplot(latencies, bins=20, kde=True, color="purple")
            plt.axvline(
                summary["metrics"]["p95_latency_ms"], color="red",
                linestyle="dashed", linewidth=2,
                label=f"P95 ({summary['metrics']['p95_latency_ms']:.0f} ms)"
            )
            plt.axvline(
                summary["metrics"]["avg_latency_ms"], color="orange",
                linestyle="dashed", linewidth=2,
                label=f"Avg ({summary['metrics']['avg_latency_ms']:.0f} ms)"
            )
            plt.title(f"Latency Distribution — {self.eval_tier}", pad=15, fontsize=14)
            plt.xlabel("Latency (ms)")
            plt.ylabel("Frequency")
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"latency_dist_{self.eval_tier}.png"), dpi=300)
            plt.close()

        # --- 3. Avg Latency por Nodo (bar chart) ---
        if node_latencies:
            ordered_nodes = [n for n in NODE_ORDER if n in node_latencies]
            avg_vals      = [node_latencies[n]["avg_ms"] for n in ordered_nodes]
            p95_vals      = [node_latencies[n]["p95_ms"] for n in ordered_nodes]

            x   = np.arange(len(ordered_nodes))
            w   = 0.35
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(x - w / 2, avg_vals, w, label="Avg", color="steelblue")
            ax.bar(x + w / 2, p95_vals, w, label="P95", color="tomato")
            ax.set_xticks(x)
            ax.set_xticklabels(ordered_nodes, rotation=15, ha="right")
            ax.set_ylabel("Latency (ms)")
            ax.set_title(f"Node Latency — {self.eval_tier}", pad=15, fontsize=14)
            ax.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"node_latency_{self.eval_tier}.png"), dpi=300)
            plt.close()

        logger.info(f"Plots saved to {output_dir}")

    # ------------------------------------------------------------------
    # Loop Principal de Evaluacion
    # ------------------------------------------------------------------

    async def run_evaluation(self) -> str:
        logger.info(f"Loading local dataset metadata for Tier: '{self.eval_tier}'...")
        dataset, dataset_hash = self._load_metadata_local()
        total_items = len(dataset)

        # 1. Generar el ID al principio de la ejecución
        run_id = "run_" + datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{dataset_hash}"
        
        # 2. Crear un directorio específico para este run, agrupado por el tier de evaluación
        current_run_dir = os.path.join(self.results_dir, self.eval_tier, run_id)
        plots_dir = os.path.join(current_run_dir, "plots")
        failed_dir = os.path.join(current_run_dir, "no-pasaron")
        
        os.makedirs(current_run_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)
        os.makedirs(failed_dir, exist_ok=True)

        logger.info("Initializing Moderator Graph...")
        self.app = await HybridShieldAgent()._build_graph()

        results              = []
        tp = fp = fn = tn = errors = 0
        hitl_count           = 0
        actual_blocked       = 0
        actual_passed        = 0
        pred_blocked         = 0
        pred_passed          = 0
        total_cost           = 0.0
        global_node_costs    = {}
        global_node_tokens   = {}
        successful_latencies = []

        logger.info(f"Starting evaluation on {total_items} items...\n")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_EVALS)

        async def process_item(item):
            async with semaphore:
                nonlocal tp, fp, fn, tn, errors, hitl_count
                nonlocal actual_blocked, actual_passed, pred_blocked, pred_passed
                nonlocal total_cost, global_node_costs, global_node_tokens, successful_latencies

                item_id        = item["id"]
                is_scam_actual = item["label"] == "BLOCKED"
                input_data     = item.get("input_data", {})
                item_title     = input_data.get("title", "N/A")
                item_desc      = input_data.get("description", "N/A")

                if is_scam_actual:
                    actual_blocked += 1
                else:
                    actual_passed += 1

                # Optimize image and upload to GCS for the eval
                local_image_path = self._resolve_local_path(item.get("file_path", ""))
                
                def optimize_and_upload():
                    with open(local_image_path, "rb") as f:
                        original_bytes = f.read()
                    optimized_bytes = optimize_image(original_bytes)
                    
                    # Upload to GCS
                    bucket = self.storage_client.bucket(self.bucket_name)
                    eval_blob_path = f"optimized_evals/{item_id}.webp"
                    blob = bucket.blob(eval_blob_path)
                    blob.upload_from_string(optimized_bytes, content_type="image/webp")
                    return f"gs://{self.bucket_name}/{eval_blob_path}"

                try:
                    # Ejecución en hilo separado para no bloquear el Event Loop de Windows
                    final_gcs_uri = await asyncio.to_thread(optimize_and_upload)
                except Exception as e:
                    logger.warning(f"  [eval] Could not optimize/upload image for item {item_id}: {e}. Falling back to original.")
                    final_gcs_uri = f"gs://{self.bucket_name}/{item['file_path']}"

                input_state = {
                    "input_data": input_data,
                    "gcs_uri": final_gcs_uri,
                    "execution_metrics": {
                        "totals": {"prompt_tokens": 0, "candidates_tokens": 0},
                        "nodes": {}
                    }
                }

                config     = {"configurable": {"thread_id": f"eval_{uuid.uuid4().hex[:8]}"}}
                start_time = time.time()

                logger.info(
                    f"[{item_id:>3}] GT={'BLOCKED' if is_scam_actual else 'PASSED '} | "
                    f"Category={item.get('category', 'N/A')}"
                )

                try:
                    state_output = await self.app.ainvoke(input_state, config=config)
                
                    latency_ms   = (time.time() - start_time) * 1000
                    successful_latencies.append(latency_ms)

                    final_action = state_output.get("final_action", "Unknown")
                    reasoning    = state_output.get("reasoning", "")
                    exec_metrics = state_output.get("execution_metrics", {})

                    is_hitl            = final_action in ACTION_HUMAN_REVIEW
                    is_scam_prediction = final_action == ACTION_BLOCK

                    if is_hitl:
                        hitl_count += 1
                        outcome = "HITL"
                    elif is_scam_actual and is_scam_prediction:
                        tp += 1; outcome = "TP"; pred_blocked += 1
                    elif is_scam_actual and not is_scam_prediction:
                        fn += 1; outcome = "FN"; pred_passed  += 1
                    elif not is_scam_actual and is_scam_prediction:
                        fp += 1; outcome = "FP"; pred_blocked += 1
                    else:
                        tn += 1; outcome = "TN"; pred_passed  += 1

                    item_cost, node_costs, node_tokens = self._calculate_item_metrics(exec_metrics)
                    total_cost += item_cost

                    for node, cost in node_costs.items():
                        global_node_costs[node] = global_node_costs.get(node, 0.0) + cost
                        if node not in global_node_tokens:
                            global_node_tokens[node] = {"prompt": 0, "candidates": 0}

                    for node, tkns in node_tokens.items():
                        if node not in global_node_tokens:
                            global_node_tokens[node] = {"prompt": 0, "candidates": 0}
                        global_node_tokens[node]["prompt"]     += tkns["prompt"]
                        global_node_tokens[node]["candidates"] += tkns["candidates"]

                    results.append({
                        "id":               item_id,
                        "category":         item.get("category", "N/A"),
                        "actual_label":     item["label"],
                        "predicted_action": final_action,
                        "outcome":          outcome,
                        "title":            item_title,
                        "description":      item_desc,
                        "reasoning":        reasoning,
                        "latency_ms":       round(latency_ms, 2),
                        "cost_usd":         item_cost,
                        "file_path":        item.get("file_path", ""),
                        "node_metrics":     exec_metrics.get("nodes", {}),
                    })

                    logger.info(f"       -> {final_action} | {outcome} | {latency_ms:.0f}ms | ${item_cost:.6f}")

                except Exception as e:
                    errors += 1
                    logger.error(f"       -> ERROR: {e}")
                    results.append({
                        "id":               item_id,
                        "category":         item.get("category", "N/A"),
                        "actual_label":     item["label"],
                        "predicted_action": "ERROR",
                        "outcome":          "ERROR",
                        "title":            item_title,
                        "description":      item_desc,
                        "reasoning":        str(e),
                        "latency_ms":       None,
                        "cost_usd":         0.0,
                        "file_path":        item.get("file_path", ""),
                        "node_metrics":     {},
                    })

        tasks = [process_item(item) for item in dataset]
        await asyncio.gather(*tasks)

        # ------------------------------------------------------------------
        # Metricas Agregadas
        # ------------------------------------------------------------------
        precision       = tp / (tp + fp)                                     if (tp + fp) > 0            else 0.0
        recall          = tp / (tp + fn)                                     if (tp + fn) > 0            else 0.0
        f1_score        = 2 * precision * recall / (precision + recall)      if (precision + recall) > 0 else 0.0
        error_rate      = errors / total_items                               if total_items > 0          else 0.0
        automation_rate = (total_items - hitl_count - errors) / total_items  if total_items > 0          else 0.0

        p95_latency = 0.0
        if len(successful_latencies) >= 20:
            p95_latency = statistics.quantiles(successful_latencies, n=20)[18]
        elif successful_latencies:
            p95_latency = sorted(successful_latencies)[int(len(successful_latencies) * 0.95)]

        avg_latency = statistics.mean(successful_latencies) if successful_latencies else 0.0

        node_latencies = self._aggregate_node_latencies(results)

        summary = {
            "dataset":     self.eval_tier,
            "hash":        dataset_hash,
            "model":       MODEL_NAME,
            "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_items": total_items,

            "distribution": {
                "actual":    {"blocked": actual_blocked, "passed": actual_passed},
                "predicted": {"blocked": pred_blocked, "passed": pred_passed, "hitl": hitl_count},
            },

            "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},

            "metrics": {
                "precision":       round(precision,       4),
                "recall":          round(recall,          4),
                "f1_score":        round(f1_score,        4),
                "automation_rate": round(automation_rate, 4),
                "error_rate":      round(error_rate,      4),
                "p95_latency_ms":  round(p95_latency,     2),
                "avg_latency_ms":  round(avg_latency,     2),
            },

            "cost": {
                "total_usd":        round(total_cost, 4),
                "avg_per_item_usd": round(total_cost / total_items, 6) if total_items > 0 else 0.0,
                "by_node": {
                    node: {
                        "total_usd":        round(global_node_costs[node], 6),
                        "avg_usd":          round(global_node_costs[node] / total_items, 6),
                        "prompt_tokens":    global_node_tokens.get(node, {}).get("prompt", 0),
                        "candidate_tokens": global_node_tokens.get(node, {}).get("candidates", 0),
                    }
                    for node in global_node_costs
                }
            },

            "node_latencies": node_latencies,
        }

        thresholds = {
            "precision":       (summary["metrics"]["precision"],       ">=", MIN_PRECISION),
            "recall":          (summary["metrics"]["recall"],          ">=", MIN_RECALL),
            "f1_score":        (summary["metrics"]["f1_score"],        ">=", MIN_F1),
            "automation_rate": (summary["metrics"]["automation_rate"], ">=", MIN_AUTOMATION_RATE),
            "error_rate":      (summary["metrics"]["error_rate"],      "<=", MAX_ERROR_RATE),
            "p95_latency_ms":  (summary["metrics"]["p95_latency_ms"],  "<=", MAX_P95_LATENCY_MS),
        }

        def _passes(name):
            val, op, threshold = thresholds[name]
            return val >= threshold if op == ">=" else val <= threshold

        verdict = "PASS" if all(_passes(m) for m in thresholds) else "FAIL"

        # 3. Guardar outputs pasando los directorios generados dinámicamente
        self._generate_plots(summary, successful_latencies, node_latencies, plots_dir)
        self._write_markdown(results, summary, thresholds, verdict, current_run_dir)
        self._write_json(results, summary, verdict, current_run_dir)
        self._save_failed_items(results, dataset, failed_dir)

        logger.info(f"\n{'='*50}")
        logger.info(f"VERDICT: {verdict}")
        logger.info(f"F1={f1_score:.2%} | Recall={recall:.2%} | Precision={precision:.2%}")
        logger.info(f"Automation={automation_rate:.2%} | Errors={errors} | P95={p95_latency:.0f}ms")
        logger.info(f"Total Cost: ${total_cost:.4f} USD")
        logger.info(f"Reports saved to: {current_run_dir}")

        return verdict

    # ------------------------------------------------------------------
    # Dataset local de items que no pasaron
    # ------------------------------------------------------------------

    def _save_failed_items(self, results: list, dataset: list, output_dir: str):
        failed = [r for r in results if r["outcome"] in FAILED_OUTCOMES]

        if not failed:
            logger.info("No failed items to save locally.")
            return

        dataset_index = {item["id"]: item for item in dataset}

        saved  = 0
        errors = 0

        for r in failed:
            item = dataset_index.get(r["id"])
            if item is None:
                continue

            item_dir = os.path.join(output_dir, str(r["id"]))
            os.makedirs(item_dir, exist_ok=True)

            file_path = item.get("file_path", "")
            local_src = self._resolve_local_path(file_path)
            if file_path and os.path.isfile(local_src):
                filename  = os.path.basename(local_src)
                local_dst = os.path.join(item_dir, filename)
                try:
                    shutil.copy2(local_src, local_dst)
                except Exception as e:
                    logger.warning(f"  [save] Could not copy image for item {r['id']}: {e}")
                    errors += 1
            else:
                logger.warning(f"  [save] Image not found locally for item {r['id']}: {local_src}")
                errors += 1

            meta = {
                "id":               r["id"],
                "category":         r["category"],
                "title":            r["title"],
                "description":      r["description"],
                "actual_label":     r["actual_label"],
                "predicted_action": r["predicted_action"],
                "outcome":          r["outcome"],
                "reasoning":        r["reasoning"],
                "latency_ms":       r["latency_ms"],
                "cost_usd":         r["cost_usd"],
                "input_data":       item.get("input_data", {}),
            }
            meta_path = os.path.join(item_dir, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            saved += 1

        logger.info(f"Failed items saved -> {output_dir} ({saved} saved, {errors} image errors)")

    # ------------------------------------------------------------------
    # Reporte Markdown
    # ------------------------------------------------------------------

    def _write_markdown(self, results: list, summary: dict, thresholds: dict, verdict: str, output_dir: str):

        def status(name):
            val, op, threshold = thresholds[name]
            ok = val >= threshold if op == ">=" else val <= threshold
            return "PASS" if ok else "FAIL"

        def truncate(text: str, max_len: int) -> str:
            return text if len(text) <= max_len else text[:max_len] + "..."

        def fmt_ms(val):
            return f"{val:,.0f} ms" if val is not None else "—"

        def fmt_tokens(val):
            return f"{val:,}" if val and val > 0 else "—"

        def fmt_cost(val):
            return f"${val:.6f}" if val and val > 0 else "—"

        m   = summary["metrics"]
        cm  = summary["confusion_matrix"]
        d   = summary["distribution"]
        c   = summary["cost"]
        nl  = summary.get("node_latencies", {})

        # ------------------------------------------------------------------
        # Sección 5: Node Performance Table
        # ------------------------------------------------------------------
        all_nodes = list(dict.fromkeys(
            NODE_ORDER + [n for n in c["by_node"] if n not in NODE_ORDER]
        ))

        node_perf_rows = ""
        for node in all_nodes:
            lat    = nl.get(node, {})
            cost   = c["by_node"].get(node, {})
            tokens = summary["cost"]["by_node"].get(node, {})

            has_llm  = node in LLM_NODES
            avg_ms   = fmt_ms(lat.get("avg_ms"))
            p95_ms   = fmt_ms(lat.get("p95_ms"))
            inp_tok  = fmt_tokens(tokens.get("prompt_tokens"))    if has_llm else "—"
            out_tok  = fmt_tokens(tokens.get("candidate_tokens")) if has_llm else "—"
            avg_cost = fmt_cost(cost.get("avg_usd"))              if has_llm else "—"
            tot_cost = fmt_cost(cost.get("total_usd"))            if has_llm else "—"

            node_perf_rows += (
                f"| `{node}` "
                f"| {avg_ms} "
                f"| {p95_ms} "
                f"| {inp_tok} "
                f"| {out_tok} "
                f"| {avg_cost} "
                f"| {tot_cost} |\n"
            )

        # Fila de totales
        total_prompt    = sum(summary["cost"]["by_node"][n].get("prompt_tokens", 0)    for n in summary["cost"]["by_node"])
        total_candidate = sum(summary["cost"]["by_node"][n].get("candidate_tokens", 0) for n in summary["cost"]["by_node"])
        node_perf_rows += (
            f"| **Total** "
            f"| {fmt_ms(m['avg_latency_ms'])} "
            f"| {fmt_ms(m['p95_latency_ms'])} "
            f"| {fmt_tokens(total_prompt)} "
            f"| {fmt_tokens(total_candidate)} "
            f"| {fmt_cost(c['avg_per_item_usd'])} "
            f"| {fmt_cost(c['total_usd'])} |\n"
        )

        # ------------------------------------------------------------------
        # Sección 7: Error Analysis — FPs y FNs
        # ------------------------------------------------------------------
        fp_rows = ""
        fn_rows = ""
        for r in results:
            if r["outcome"] == "FP":
                fp_rows += (
                    f"| {r['id']} "
                    f"| {r['category']} "
                    f"| {truncate(r['title'], 35)} "
                    f"| {truncate(r['reasoning'], 120)} |\n"
                )
            elif r["outcome"] == "FN":
                fn_rows += (
                    f"| {r['id']} "
                    f"| {r['category']} "
                    f"| {truncate(r['title'], 35)} "
                    f"| {truncate(r['reasoning'], 120)} |\n"
                )

        fp_section = ""
        if fp_rows:
            fp_section = f"""
### False Positives — legítimos bloqueados incorrectamente ({cm['fp']} casos)

| ID | Category | Title | Reasoning |
| :--- | :--- | :--- | :--- |
{fp_rows}"""
        else:
            fp_section = "\n### False Positives\n\nNinguno. ✓\n"

        fn_section = ""
        if fn_rows:
            fn_section = f"""
### False Negatives — fraudes no detectados ({cm['fn']} casos)

| ID | Category | Title | Reasoning |
| :--- | :--- | :--- | :--- |
{fn_rows}"""
        else:
            fn_section = "\n### False Negatives\n\nNinguno. ✓\n"

        # ------------------------------------------------------------------
        # Sección 8: Per-Item Trace
        # ------------------------------------------------------------------
        item_rows = ""
        for r in results:
            latency_fmt = f"{r['latency_ms']:,.0f} ms" if r["latency_ms"] is not None else "—"
            item_rows += (
                f"| {r['id']} "
                f"| {r['category']} "
                f"| {truncate(r['title'], 38)} "
                f"| {r['actual_label']} "
                f"| {r['predicted_action']} "
                f"| {r['outcome']} "
                f"| {truncate(r['description'], 55)} "
                f"| {truncate(r['reasoning'], 95)} "
                f"| {latency_fmt} "
                f"| {fmt_cost(r['cost_usd'])} |\n"
            )

        # ------------------------------------------------------------------
        # Reporte completo
        # ------------------------------------------------------------------
        report = f"""# AI Moderation Agent — Evaluation Report

**Dataset (Tier):** `{summary['dataset']}` | **Hash:** `{summary['hash']}` | **Items:** {summary['total_items']}
**Model:** {summary['model']} | **Date:** {summary['timestamp']}

---

## Overall Verdict: **{verdict}**

---

## 1. Dataset Distribution

| Category | Ground Truth | Agent Prediction |
| :--- | :---: | :---: |
| Blocked (Scam/Fraud) | {d['actual']['blocked']} | {d['predicted']['blocked']} |
| Passed (Legitimate) | {d['actual']['passed']} | {d['predicted']['passed']} |
| Human Review (HITL) | — | {d['predicted']['hitl']} |

---

## 2. Technical Metrics

| Metric | Value | Threshold | Status |
| :--- | :---: | :---: | :---: |
| Precision | {m['precision']:.2%} | >= {MIN_PRECISION:.2%} | {status('precision')} |
| Recall | {m['recall']:.2%} | >= {MIN_RECALL:.2%} | {status('recall')} |
| F1-Score | {m['f1_score']:.2%} | >= {MIN_F1:.2%} | {status('f1_score')} |
| Automation Rate | {m['automation_rate']:.2%} | >= {MIN_AUTOMATION_RATE:.2%} | {status('automation_rate')} |
| System Error Rate | {m['error_rate']:.2%} | <= {MAX_ERROR_RATE:.2%} | {status('error_rate')} |
| P95 Latency (total) | {fmt_ms(m['p95_latency_ms'])} | <= {fmt_ms(MAX_P95_LATENCY_MS)} | {status('p95_latency_ms')} |
| Avg Latency (total) | {fmt_ms(m['avg_latency_ms'])} | — | — |

> **Nota sobre HITL:** Los {d['predicted']['hitl']} casos enviados a revisión humana se excluyen
> del cálculo de precisión/recall. La automation rate los penaliza correctamente.

---

## 3. Confusion Matrix

| | Predicted **Block** | Predicted **Pass** |
| :--- | :---: | :---: |
| **Actual Block** | {cm['tp']} TP | {cm['fn']} FN |
| **Actual Pass** | {cm['fp']} FP | {cm['tn']} TN |

---

## 4. Visualizations

### Confusion Matrix
![Confusion Matrix](./plots/confusion_matrix_{summary['dataset']}.png)

### Latency Distribution (total por ítem)
![Latency Distribution](./plots/latency_dist_{summary['dataset']}.png)

### Node Latency (avg vs P95)
![Node Latency](./plots/node_latency_{summary['dataset']}.png)

---

## 5. Node Performance

| Node | Avg Latency | P95 Latency | Input Tokens | Output Tokens | Avg Cost / Item | Total Cost |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
{node_perf_rows}
> Tokens y costos se muestran solo para nodos con llamadas LLM. El resto muestra — (determinístico/sin costo).

---

## 6. Cost Summary

- **Total Evaluation Cost:** ${c['total_usd']:.4f} USD
- **Average Cost per Item:** ${c['avg_per_item_usd']:.6f} USD
- **Total Input Tokens:** {fmt_tokens(total_prompt)}
- **Total Output Tokens:** {fmt_tokens(total_candidate)}

---

## 7. Error Analysis
{fp_section}
{fn_section}

---

## 8. Per-Item Evaluation Trace

| ID | Category | Title | Ground Truth | Predicted | Outcome | Description | Reasoning | Latency | Cost |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: |
{item_rows}
---
*Generated by {MODEL_NAME} Eval Framework — {summary['timestamp']}*
"""
        report_path = os.path.join(output_dir, f"report_{self.eval_tier}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Markdown report -> {report_path}")

    # ------------------------------------------------------------------
    # Reporte JSON
    # ------------------------------------------------------------------

    def _write_json(self, results: list, summary: dict, verdict: str, output_dir: str):
        payload = {"verdict": verdict, "summary": summary, "results": results}
        json_path = os.path.join(output_dir, f"results_{self.eval_tier}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON report    -> {json_path}")


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------

if __name__ == "__main__":
    TARGET_TIER = "tier3_full_test"

    evaluator = ModeratorEvaluator(
        bucket_name=BUCKET_NAME,
        results_dir=RESULTS_DIR,
        eval_tier=TARGET_TIER
    )
    verdict   = asyncio.run(evaluator.run_evaluation())
    sys.exit(0 if verdict == "PASS" else 1)