import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Any

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class DatasetSampler:
    """
    Clase encargada de submuestrear un dataset de imágenes y su archivo de metadatos asociado,
    manteniendo la estructura de directorios y garantizando que no haya superposición
    de imágenes entre diferentes subdatasets (evita data leakage).
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.metadata_path = self.base_path / "metadata.json"
        
        # Registro global para rastrear las imágenes ya seleccionadas y evitar repetirlas
        self.used_images = set()
        
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de metadatos en {self.metadata_path}")

    def _load_metadata(self) -> List[Dict[str, Any]]:
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("El formato del JSON de metadatos debe ser una lista de objetos.")
        return data

    def _save_json(self, data: List[Dict[str, Any]], output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logging.info(f"Nuevo archivo de metadatos guardado en: {output_path}")

    def create_subdataset(self, output_dir_name: str, distribution: Dict[str, int]) -> None:
        target_base_dir = self.base_path.parent / "evals" / output_dir_name
        
        metadata_original = self._load_metadata()
        metadata_by_id = {str(item["id"]): item for item in metadata_original if "id" in item}
        
        sampled_metadata: List[Dict[str, Any]] = []
        all_copied_files: List[Path] = []

        logging.info(f"Iniciando muestreo para el subdataset: {output_dir_name}")

        for folder_name, sample_size in distribution.items():
            source_folder = self.base_path / folder_name
            
            if not source_folder.exists() or not source_folder.is_dir():
                logging.warning(f"La carpeta '{folder_name}' no existe en {self.base_path}. Omitiendo.")
                continue

            image_extensions = {".png", ".jpg", ".jpeg", ".img"}
            
            # Obtener todas las imágenes en la carpeta original
            all_images = sorted(
                [p for p in source_folder.iterdir() if p.is_file() and p.suffix.lower() in image_extensions]
            )

            # Filtrar las imágenes que ya fueron usadas en subdatasets anteriores
            available_images = [img for img in all_images if img not in self.used_images]

            if len(available_images) < sample_size:
                raise ValueError(
                    f"No hay suficientes imágenes disponibles (no usadas) en '{folder_name}'. "
                    f"Requeridas: {sample_size}, Disponibles: {len(available_images)} "
                    f"(Totales en carpeta: {len(all_images)}, Ya usadas: {len(all_images) - len(available_images)})"
                )

            # Seleccionar la muestra de las imágenes disponibles
            sampled_images = random.sample(available_images, sample_size)
            
            # Registrar las imágenes seleccionadas para no volver a usarlas
            self.used_images.update(sampled_images)

            target_folder = target_base_dir / folder_name
            target_folder.mkdir(parents=True, exist_ok=True)

            for img_path in sampled_images:
                dest_img_path = target_folder / img_path.name
                dest_img_path.write_bytes(img_path.read_bytes())
                all_copied_files.append(dest_img_path)

                img_id_str = img_path.stem  
                meta_match = metadata_by_id.get(img_id_str) or metadata_by_id.get(str(int(img_id_str)))

                if meta_match:
                    sampled_metadata.append(meta_match)
                else:
                    logging.warning(f"No se encontraron metadatos para la imagen: {img_path.name}")

        all_copied_files.sort(key=lambda p: (p.parent.name, p.name))
        sampled_metadata.sort(
            key=lambda m: (
                "passed" if m.get("label") == "pasa" else "blocked", 
                f"{int(m['id']):03d}"
            )
        )

        self._save_json(sampled_metadata, target_base_dir / "metadata.json")
        logging.info(f"Subdataset generado con éxito en: {target_base_dir}")


# --- Ejemplo de uso adaptado a tres tiers (Mutuamente excluyentes) ---
if __name__ == "__main__":

    DATASET_PATH = Path("./data/balanced") 

    try:
        sampler = DatasetSampler(base_path=DATASET_PATH)

        # ==========================================
        # CASO 1: Generar el Tier 1 (Smoke Test)
        # ==========================================
        config_smoke = {"passed": 20, "blocked": 20}
        sampler.create_subdataset(
            output_dir_name="tier1_smoke_test", 
            distribution=config_smoke
        )

        # ==========================================
        # CASO 2: Generar el Tier 2 (Stress Test)
        # ==========================================
        # Estas 30 imágenes "blocked" serán DIFERENTES a las 20 del Tier 1
        config_stress = {"passed": 0, "blocked": 20}
        sampler.create_subdataset(
             output_dir_name="tier2_stress_test", 
             distribution=config_stress
         )

        # ==========================================
        # CASO 3: Generar el Tier 3 (Full Benchmark)
        # ==========================================
        # Nota: Requieres suficientes imágenes en total. Si tu total original
        # era 50 "passed", pedir 20 (Tier 1) + 50 (Tier 3) lanzará un ValueError.
        # Asegúrate de ajustar las distribuciones al tamaño real de tu pool.
        config_benchmark = {"passed": 30, "blocked": 10}
        sampler.create_subdataset(
            output_dir_name="tier3_full_test", 
            distribution=config_benchmark
        )

    except Exception as e:
        logging.error(f"Error durante la ejecución: {e}", exc_info=True)