import pytest
from backend.agents.moderator.services.firestore_service import (
    update_job_status, 
    get_job_status,
    update_ui_state
)

class TestFirestoreService:

    @pytest.mark.asyncio
    async def test_update_and_get_status(self, unique_id):
        """
        Prueba el flujo completo: Crear/Actualizar un estado y recuperarlo.
        """
        # 1. Definimos los datos de prueba
        test_status = "PROCESANDO_IMAGEN"
        test_metadata = {
            "model_used": "gemini-2.5-flash", 
            "priority": "high",
            "execution_metrics": {
                "totals": {"prompt_tokens": 150, "candidates_tokens": 50},
                "nodes": {"pre_filter_node": {"prompt_tokens": 150, "candidates_tokens": 50, "model_name": "gemini-2.5-flash"}}
            }
        }

        # 2. Ejecutamos la actualización
        await update_job_status(
            thread_id=unique_id, 
            status=test_status, 
            metadata=test_metadata
        )

        # 3. Recuperamos los datos de la base de datos real
        retrieved_data = await get_job_status(unique_id)

        # 4. Verificaciones (Asserts)
        assert retrieved_data is not None
        assert retrieved_data["status"] == test_status
        assert retrieved_data["model_used"] == "gemini-2.5-flash"
        assert "execution_metrics" in retrieved_data
        assert retrieved_data["execution_metrics"]["totals"]["prompt_tokens"] == 150
        assert "last_update" in retrieved_data
        # Verificamos que la fecha se convirtió a string ISO como pide tu función
        assert isinstance(retrieved_data["last_update"], str)

    @pytest.mark.asyncio
    async def test_get_non_existent_job(self):
        """Verifica que buscar un ID que no existe devuelva None."""
        result = await get_job_status("id_que_no_existe_12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_empty_thread_id(self):
        """Verifica que la función maneje correctamente un thread_id vacío."""
        # No debería lanzar excepción gracias a tu manejo de errores
        await update_job_status(thread_id="", status="FAILED")

    @pytest.mark.asyncio
    async def test_update_ui_state(self, unique_id):
        """Verifica la actualización asíncrona de la proyección de UI."""
        # Al ser creación, fallará el update() y usará set()
        await update_ui_state(
            thread_id=unique_id,
            current_node="pre_filter",
            ui_context="checking_safety",
            ui_message="Test Init",
            status="INITIALIZING"
        )
        
        # Una vez creado, actualizamos
        await update_ui_state(
            thread_id=unique_id,
            current_node="extractor",
            ui_context="analyzing_data",
            ui_message="Test Update",
            status="ANALYZING"
        )