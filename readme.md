Semantic Shield (Escudo semantico): 
Multi-Agent E-commerce Moderation
Semantic Shield es un sistema de moderación de contenido diseñado para detectar fraudes y anomalías en publicaciones de e-commerce. La solución utiliza una arquitectura desacoplada con un núcleo de inteligencia artificial en Python y una interfaz de gestión moderna en Next.js.

Estructura del Proyecto
El sistema se divide en dos componentes principales:

Backend (AI Engine)
Construido con Python y LangGraph, este módulo gestiona el flujo de razonamiento del agente.

Orquestación de Agentes: Implementación de un grafo de estados que coordina la extracción multimodal y la evaluación de riesgos.

Inferencia Multimodal: Uso de Gemini 2.0 Flash para el análisis simultáneo de imágenes y metadatos de productos.

Recuperación de Información (RAG): Integración con Vertex AI Search para el anclaje de decisiones basado en políticas legales reales.

Lógica de Disonancia: Detección de inconsistencias entre el título del producto y el contenido visual mediante visión por computadora.

Frontend (User Interface)
Desarrollado en Next.js, proporciona un panel de control para supervisar las moderaciones.

Visualización en Tiempo Real: Interfaz para revisar publicaciones aprobadas, bloqueadas y aquellas que requieren revisión humana.

Gestión de Estado: Conexión con los módulos de Python para mostrar el razonamiento (reasoning) detrás de cada puntaje de riesgo.

Arquitectura de Componentes: Diseño modular para la carga de imágenes y despliegue de métricas de fraude.

Arquitectura de Decisión
El flujo de trabajo sigue una lógica de grafos dirigida:

Nodo de Extracción: Gemini analiza la entrada y extrae características clave.

Bifurcación Condicional: Si se detecta disonancia visual o datos de contacto externos, el flujo se dirige al nodo de RAG.

Nodo de Evaluación: El evaluador cruza la información extraída con el contexto de las políticas recuperadas.

Nodo de Consolidación: Clasificación final del producto según el puntaje de riesgo obtenido.

Stack Tecnológico
Lenguajes: Python 3.10+, TypeScript.

Frameworks de IA: LangGraph, Google Cloud Agent Development Kit (ADK).

Modelos: Vertex AI Gemini 2.0 Flash, Vertex AI Search.

Frontend: Next.js, Tailwind CSS.

Infraestructura: Google Cloud Platform (GCP).

Propuesta de Valor
Explicabilidad: Cada bloqueo cuenta con una justificación técnica y una referencia a la política infringida.

Optimización de Recursos: El uso de lógica condicional en el grafo evita llamadas innecesarias a servicios de búsqueda, reduciendo la latencia y el consumo de tokens.

Seguridad Grounded: Minimización de alucinaciones mediante el anclaje de datos en un Data Store de políticas verificado.