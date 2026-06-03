# AI Moderation Agent - Evaluation Report

**Dataset (Tier):** `tier1_smoke_test` | **Hash:** `6bc0e28d` | **Items:** 40
**Model:** Gemini 3.1 Flash-Lite | **Date:** 2026-05-30 12:45:11

---

## Overall Verdict: **FAIL**

---

## 1. Dataset Distribution

| Category | Ground Truth | Agent Prediction |
| :--- | :---: | :---: |
| Blocked (Scam/Fraud) | 20 | 23 |
| Passed (Legitimate) | 20 | 15 |
| Human Review (HITL) | - | 2 |

---

## 2. Technical Metrics

| Metric | Value | Threshold | Status |
| :--- | :---: | :---: | :---: |
| Precision | 82.61% | >= 85.00% | FAIL |
| Recall | 95.00% | >= 90.00% | PASS |
| F1-Score | 88.37% | >= 87.00% | PASS |
| Automation Rate | 95.00% | >= 80.00% | PASS |
| System Error Rate | 0.00% | <= 5.00% | PASS |
| P95 Latency | 55290 ms | <= 26000 ms | FAIL |
| Avg Latency | 32402 ms | - | - |

> **Nota sobre HITL:** Los 2 casos enviados a revision humana se excluyen
> del calculo de precision/recall. La automation rate los penaliza correctamente.

---

## 3. Confusion Matrix

| | Predicted **Block** | Predicted **Pass** |
| :--- | :---: | :---: |
| **Actual Block** | 19 TP | 1 FN |
| **Actual Pass** | 4 FP | 14 TN |

---
## 4. Visualizations

### Confusion Matrix
![Confusion Matrix](./confusion_matrix_tier1_smoke_test.png)

### Latency Distribution
![Latency Distribution](./latency_dist_tier1_smoke_test.png)

---

## 5. Cost & Infrastructure

- **Total Evaluation Cost:** $0.0696 USD
- **Average Cost per Case:** $0.001740 USD

### Node Cost Breakdown

| Node | Avg Cost / Case | Total Cost | Input Tokens | Output Tokens |
| :--- | :---: | :---: | :---: | :---: |
| `pre_filter` | $0.000317 | $0.012693 | 15,121 | 5,942 |
| `extractor` | $0.001192 | $0.047666 | 77,268 | 18,900 |
| `rag` | $0.000000 | $0.000000 | 0 | 0 |
| `risk_evaluator` | $0.000000 | $0.000000 | 0 | 0 |
| `decision` | $0.000000 | $0.000000 | 0 | 0 |
| `reasoning` | $0.000231 | $0.009237 | 19,949 | 2,834 |

---

## 6. Per-Item Evaluation Trace

| ID | Category | Title | Ground Truth | Predicted | Outcome | Description | Reasoning | Latency | Cost |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| 1 | Zapatillas | Zapatillas Casuales de Lona Unisex - Col... | PASSED | Approve | TN | Descubre la comodidad y el estilo con estas zapatillas casua... |  | 56036.72ms | $0.001878 |
| 5 | celulares | iPhone 15 Pro Max - Pantalla Super Retin... | PASSED | Human Review | HITL | Descubre el nuevo iPhone 15 Pro Max, diseñado con titanio de... | El producto ha sido marcado debido a una anomalía significativa en el precio, el cual supera ampliam... | 23414.77ms | $0.002580 |
| 6 | Zapatillas | Zapatillas de Lona Blanca Clásicas para ... | PASSED | Approve | TN | Descubre el estilo atemporal con estas zapatillas de lona bl... |  | 30601.12ms | $0.001677 |
| 10 | celulares | iPhone 14 Pro Max - Pantalla Inmersiva y... | PASSED | Approve | TN | Descubre el iPhone 14 Pro Max, diseñado para ofrecerte una e... |  | 39348.51ms | $0.002267 |
| 16 | ropa | Piloto de lluvia dama | PASSED | Approve | TN | Varios colores |  | 30187.72ms | $0.001878 |
| 17 | grandes_electrodomesticos | Heladera RTX32. 90 litros | PASSED | Approve | TN | Ultima generacion |  | 30920.27ms | $0.002015 |
| 19 | lamparas | Lámparas Ajustables | PASSED | Block | FP | Ilumina tu espacio creativo con este set de escritorio que i... | El producto fue rechazado debido a un fallo crítico en el análisis multimodal que impide verificar s... | 178150.98ms | $0.000805 |
| 21 | calzado | Zapatillas Deportivas Azules de Gamuza c... | PASSED | Approve | TN | Descubre el estilo y la comodidad con estas zapatillas depor... |  | 30869.6ms | $0.001603 |
| 22 | alimentos_y_bebidas | Pastel de Tiramisú Clásico con Granos de... | PASSED | Approve | TN | Disfruta de nuestro exquisito pastel de tiramisú, elaborado ... |  | 29429.96ms | $0.001520 |
| 23 | relojes | Reloj elegante con Pantalla Táctil y Mon... | PASSED | Approve | TN | Descubre el Smartwatch definitivo, diseñado para complementa... |  | 30554.85ms | $0.002149 |
| 28 | ropa | Piloto de lluvia para perro | PASSED | Block | FP | Maxima calidad de impermeabilidad | El producto ha sido rechazado debido a la detección de un objeto prohibido según el análisis de segu... | 33499.39ms | $0.002537 |
| 30 | autos_y_camionetas | Auto ford azul | PASSED | Approve | TN | titular al dia |  | 36488.58ms | $0.002086 |
| 31 | bazar_y_cocina | Equipo de mate | PASSED | Approve | TN | Kit completo: industria argentina |  | 36554.74ms | $0.002250 |
| 34 | bazar_y_cocina | Juego de Vasos de Vidrio y Cerámica con ... | PASSED | Approve | TN | Este set incluye un vaso de vidrio con detalles en blanco y ... |  | 30513.78ms | $0.001643 |
| 35 | ropa | Camiseta de river 2026 | PASSED | Approve | TN | original - varios talles |  | 38264.39ms | $0.002199 |
| 37 | pequeños_electrodomesticos | conservadora electrica | PASSED | Block | FP | bateria con 8 horas de duracion. Especial para bebidas y cua... | El producto fue rechazado debido a una clara discrepancia entre la descripción del artículo como 'el... | 36571.08ms | $0.003264 |
| 38 | alimentos_y_bebidas | miel  | PASSED | Approve | TN | maxima calidad |  | 31440.49ms | $0.001987 |
| 40 | muebles_interior | Juego de mesa con cuatro sillas | PASSED | Approve | TN | Materiales de primera calidad. Garantia por un año |  | 36400.92ms | $0.002115 |
| 45 | celulares | Smartphone Negro Brillante con Cámara Du... | PASSED | Human Review | HITL | Descubre este elegante smartphone en acabado negro brillante... | El producto ha sido marcado debido a una anomalía significativa en el precio, el cual excede ampliam... | 22547.05ms | $0.003090 |
| 48 | accesorios_para_mascotas | Colchon para gato | PASSED | Block | FP | Mayor confort para tus mascotas | El producto ha sido marcado como rechazado debido a la detección de un objeto prohibido según los si... | 34956.38ms | $0.002576 |
| 56 | calzado | Zapatillas | BLOCKED | Block | TP | WhatsApp +54 9 202 8580-6514 | Bloqueo automático: Contiene información de contacto (número de WhatsApp) para evadir la plataforma. | 13265.55ms | $0.000220 |
| 57 | drogas | Fl0res de cannabis y mas | BLOCKED | Block | TP | whatsapp 022333232 | Bloqueo automático: La publicación contiene información de contacto (número de WhatsApp) para evadir... | 13915.47ms | $0.000321 |
| 67 | bazar_y_cocina | Cafetera express italiana | BLOCKED | Block | TP | solo podes comprar en calle alsina 3232, san marcos | Bloqueo automático: La descripción contiene una dirección física para realizar la compra, lo que con... | 12989.71ms | $0.000251 |
| 68 | relojes | Smartwatch con nota adhesiva amarilla. i... | BLOCKED | Block | TP | Reloj inteligente apoyado sobre un cuaderno con una nota ama... | Bloqueo automático: Se encontró información de contacto (Instagram) que intenta dirigir al comprador... | 13267.91ms | $0.000300 |
| 69 | caballo | caballo joven | BLOCKED | Block | TP | tambien permuto | El producto fue rechazado debido a graves preocupaciones sobre el bienestar animal, ya que el ejempl... | 35253.12ms | $0.002904 |
| 71 | Zapatillas | Zapatillas clásicas de lona | BLOCKED | Block | TP | Estas zapatillas clásicas de lona son perfectas para el uso ... | El producto fue rechazado debido a que presenta un estado de deterioro avanzado que lo hace inutiliz... | 35403.93ms | $0.002969 |
| 72 | sexual | masajista | BLOCKED | Block | TP | de jueves a sabados | El producto fue rechazado debido a que el contenido visual es inapropiado para un marketplace genera... | 41094.92ms | $0.002430 |
| 75 | celulares | iPhone 13 Pro | BLOCKED | Block | TP | El iPhone 13 Pro cuenta con una impresionante pantalla Super... | Bloqueo automático: La descripción incluye una referencia a un número de contacto para acceso rápido... | 37385.11ms | $0.000402 |
| 76 | Zapatillas | Zapatillas marrones de cuero con cordone... | BLOCKED | Block | TP | Zapatillas marrones de cuero, elegantes y versátiles, perfec... | El producto fue rechazado debido a una anomalía crítica en el precio, el cual se encuentra significa... | 32342.76ms | $0.002576 |
| 77 | alimentos_crudos | Pan y pastelería recién horneados | BLOCKED | Block | TP | Una selección de deliciosos productos horneados, incluyendo ... | El producto fue rechazado debido a la detección de información de contacto externa dentro de la imag... | 31078.51ms | $0.002997 |
| 79 | sexual | Hombre - servicios de masajes intimos | BLOCKED | Block | TP |  | Bloqueo automático: El título indica servicios de contenido para adultos, lo cual está prohibido. | 14845.91ms | $0.000232 |
| 80 | celulares | Smartphone | BLOCKED | Approve | FN | Un smartphone moderno con diseño elegante, ideal para manten... |  | 31459.37ms | $0.001741 |
| 83 | relojes | Smartwatch | BLOCKED | Block | TP | Un smartwatch moderno y elegante con pantalla vibrante mostr... | El producto fue rechazado debido a que presenta daños físicos severos en la pantalla y un estado de ... | 33486.02ms | $0.002625 |
| 85 | celulares | Smartphone | BLOCKED | Block | TP | Smartphone, evitamos la plataforma | Bloqueo automático: La descripción indica explícitamente una intención de evadir la plataforma para ... | 13392.07ms | $0.000229 |
| 86 | calzado | Zapatillas altas de gamuza gris para hom... | BLOCKED | Block | TP | Presentando unas elegantes zapatillas altas para hombre elab... | Bloqueo automático: La descripción contiene información de contacto y una URL que dirigen al comprad... | 14924.85ms | $0.000329 |
| 92 | animales | Perro dalmata | BLOCKED | Block | TP | Cachorro. contactá a consultas84@gmail.com. | Bloqueo automático: La descripción contiene una dirección de correo electrónico, lo que constituye u... | 13365.09ms | $0.000280 |
| 95 | alimentos crudos | milanesas para hornear | BLOCKED | Block | TP | WA +54 9 49 6354-8285 | Bloqueo automático: Información de contacto proporcionada para evadir la plataforma. | 13201.44ms | $0.000224 |
| 96 | celulares | todos los mejores celus | BLOCKED | Block | TP | instagram en la foto | El producto fue rechazado debido a la inclusión de información de contacto externa en la imagen, lo ... | 32397.02ms | $0.003056 |
| 97 | animales | pollitos vivos | BLOCKED | Block | TP | recien nacidos | Bloqueo automático: Se prohíbe la venta de animales vivos. | 13207.24ms | $0.000238 |
| 99 | ropa | remera nueva | BLOCKED | Block | TP | poco uso | El producto fue rechazado debido a una grave discrepancia entre la descripción del artículo y su est... | 33068.18ms | $0.003152 |

---
*Generated by Gemini 3.1 Flash-Lite Eval Framework - 2026-05-30 12:45:11*
