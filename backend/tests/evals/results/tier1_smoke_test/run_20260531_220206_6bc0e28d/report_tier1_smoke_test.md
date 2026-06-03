# AI Moderation Agent — Evaluation Report

**Dataset (Tier):** `tier1_smoke_test` | **Hash:** `6bc0e28d` | **Items:** 40
**Model:** Gemini 3.1 Flash-Lite | **Date:** 2026-05-31 22:24:21

---

## Overall Verdict: **FAIL**

---

## 1. Dataset Distribution

| Category | Ground Truth | Agent Prediction |
| :--- | :---: | :---: |
| Blocked (Scam/Fraud) | 20 | 20 |
| Passed (Legitimate) | 20 | 15 |
| Human Review (HITL) | — | 5 |

---

## 2. Technical Metrics

| Metric | Value | Threshold | Status |
| :--- | :---: | :---: | :---: |
| Precision | 95.00% | >= 85.00% | PASS |
| Recall | 95.00% | >= 90.00% | PASS |
| F1-Score | 95.00% | >= 87.00% | PASS |
| Automation Rate | 87.50% | >= 80.00% | PASS |
| System Error Rate | 0.00% | <= 5.00% | PASS |
| P95 Latency (total) | 82,133 ms | <= 36,000 ms | FAIL |
| Avg Latency (total) | 32,583 ms | — | — |

> **Nota sobre HITL:** Los 5 casos enviados a revisión humana se excluyen
> del cálculo de precisión/recall. La automation rate los penaliza correctamente.

---

## 3. Confusion Matrix

| | Predicted **Block** | Predicted **Pass** |
| :--- | :---: | :---: |
| **Actual Block** | 19 TP | 1 FN |
| **Actual Pass** | 1 FP | 14 TN |

---

## 4. Visualizations

### Confusion Matrix
![Confusion Matrix](./plots/confusion_matrix_tier1_smoke_test.png)

### Latency Distribution (total por ítem)
![Latency Distribution](./plots/latency_dist_tier1_smoke_test.png)

### Node Latency (avg vs P95)
![Node Latency](./plots/node_latency_tier1_smoke_test.png)

---

## 5. Node Performance

| Node | Avg Latency | P95 Latency | Input Tokens | Output Tokens | Avg Cost / Item | Total Cost |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `pre_filter` | 1,901 ms | 2,352 ms | 15,121 | 5,941 | $0.000317 | $0.012693 |
| `extractor` | 11,085 ms | 21,561 ms | 82,288 | 20,108 | $0.001268 | $0.050732 |
| `rag` | 11,882 ms | 14,463 ms | — | — | — | — |
| `risk_evaluator` | 3 ms | 10 ms | — | — | — | — |
| `reasoning` | 1,800 ms | 2,453 ms | 15,599 | 2,234 | $0.000181 | $0.007250 |
| `decision` | 10 ms | 22 ms | — | — | — | — |
| `fly_wheel` | 13,763 ms | 19,968 ms | — | — | — | — |
| **Total** | 32,583 ms | 82,133 ms | 113,008 | 28,283 | $0.001767 | $0.070700 |

> Tokens y costos se muestran solo para nodos con llamadas LLM. El resto muestra — (determinístico/sin costo).

---

## 6. Cost Summary

- **Total Evaluation Cost:** $0.0707 USD
- **Average Cost per Item:** $0.001767 USD
- **Total Input Tokens:** 113,008
- **Total Output Tokens:** 28,283

---

## 7. Error Analysis

### False Positives — legítimos bloqueados incorrectamente (1 casos)

| ID | Category | Title | Reasoning |
| :--- | :--- | :--- | :--- |
| 37 | pequeños_electrodomesticos | conservadora electrica | El producto fue rechazado debido a una clara disonancia visual, ya que se promociona como una conservadora eléctrica con... |


### False Negatives — fraudes no detectados (1 casos)

| ID | Category | Title | Reasoning |
| :--- | :--- | :--- | :--- |
| 80 | celulares | Smartphone |  |


---

## 8. Per-Item Evaluation Trace

| ID | Category | Title | Ground Truth | Predicted | Outcome | Description | Reasoning | Latency | Cost |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| 1 | Zapatillas | Zapatillas Casuales de Lona Unisex - C... | PASSED | Approve | TN | Descubre la comodidad y el estilo con estas zapatillas ... |  | 84,090 ms | $0.002005 |
| 5 | celulares | iPhone 15 Pro Max - Pantalla Super Ret... | PASSED | Human Review | HITL | Descubre el nuevo iPhone 15 Pro Max, diseñado con titan... | El producto ha sido marcado debido a una anomalía significativa en el precio, el cual excede am... | 26,042 ms | $0.002672 |
| 6 | Zapatillas | Zapatillas de Lona Blanca Clásicas par... | PASSED | Approve | TN | Descubre el estilo atemporal con estas zapatillas de lo... |  | 29,798 ms | $0.002202 |
| 10 | celulares | iPhone 14 Pro Max - Pantalla Inmersiva... | PASSED | Human Review | HITL | Descubre el iPhone 14 Pro Max, diseñado para ofrecerte ... | El producto fue rechazado debido a una anomalía significativa en el precio, el cual excede ampl... | 21,230 ms | $0.003023 |
| 16 | ropa | Piloto de lluvia dama | PASSED | Approve | TN | Varios colores |  | 33,235 ms | $0.002029 |
| 17 | grandes_electrodomesticos | Heladera RTX32. 90 litros | PASSED | Human Review | HITL | Ultima generacion | El producto fue rechazado debido a un fallo crítico en el análisis multimodal que impide verifi... | 144,668 ms | $0.000706 |
| 19 | lamparas | Lámparas Ajustables | PASSED | Human Review | HITL | Ilumina tu espacio creativo con este set de escritorio ... | El producto ha sido aprobado para su publicación ya que, a pesar de la alerta inicial por calid... | 24,336 ms | $0.002431 |
| 21 | calzado | Zapatillas Deportivas Azules de Gamuza... | PASSED | Approve | TN | Descubre el estilo y la comodidad con estas zapatillas ... |  | 32,716 ms | $0.001652 |
| 22 | alimentos_y_bebidas | Pastel de Tiramisú Clásico con Granos ... | PASSED | Approve | TN | Disfruta de nuestro exquisito pastel de tiramisú, elabo... |  | 33,806 ms | $0.001958 |
| 23 | relojes | Reloj elegante con Pantalla Táctil y M... | PASSED | Approve | TN | Descubre el Smartwatch definitivo, diseñado para comple... |  | 33,459 ms | $0.002142 |
| 28 | ropa | Piloto de lluvia para perro | PASSED | Approve | TN | Maxima calidad de impermeabilidad |  | 37,457 ms | $0.002091 |
| 30 | autos_y_camionetas | Auto ford azul | PASSED | Approve | TN | titular al dia |  | 35,514 ms | $0.001672 |
| 31 | bazar_y_cocina | Equipo de mate | PASSED | Approve | TN | Kit completo: industria argentina |  | 40,901 ms | $0.002630 |
| 34 | bazar_y_cocina | Juego de Vasos de Vidrio y Cerámica co... | PASSED | Approve | TN | Este set incluye un vaso de vidrio con detalles en blan... |  | 35,813 ms | $0.001631 |
| 35 | ropa | Camiseta de river 2026 | PASSED | Approve | TN | original - varios talles |  | 33,971 ms | $0.002228 |
| 37 | pequeños_electrodomesticos | conservadora electrica | PASSED | Block | FP | bateria con 8 horas de duracion. Especial para bebidas ... | El producto fue rechazado debido a una clara disonancia visual, ya que se promociona como una c... | 34,033 ms | $0.003366 |
| 38 | alimentos_y_bebidas | miel  | PASSED | Approve | TN | maxima calidad |  | 28,162 ms | $0.002099 |
| 40 | muebles_interior | Juego de mesa con cuatro sillas | PASSED | Approve | TN | Materiales de primera calidad. Garantia por un año |  | 35,051 ms | $0.002204 |
| 45 | celulares | Smartphone Negro Brillante con Cámara ... | PASSED | Human Review | HITL | Descubre este elegante smartphone en acabado negro bril... | Risk score 0.35 computed. | 21,718 ms | $0.002367 |
| 48 | accesorios_para_mascotas | Colchon para gato | PASSED | Approve | TN | Mayor confort para tus mascotas |  | 34,306 ms | $0.002160 |
| 56 | calzado | Zapatillas | BLOCKED | Block | TP | WhatsApp +54 9 202 8580-6514 | Bloqueo automático: Contiene información de contacto (número de WhatsApp) para evadir la plataf... | 15,031 ms | $0.000220 |
| 57 | drogas | Fl0res de cannabis y mas | BLOCKED | Block | TP | whatsapp 022333232 | Bloqueo automático: La publicación contiene información de contacto (número de WhatsApp) para e... | 15,037 ms | $0.000321 |
| 67 | bazar_y_cocina | Cafetera express italiana | BLOCKED | Block | TP | solo podes comprar en calle alsina 3232, san marcos | Bloqueo automático: La descripción contiene una dirección física para realizar la compra, lo qu... | 15,648 ms | $0.000251 |
| 68 | relojes | Smartwatch con nota adhesiva amarilla.... | BLOCKED | Block | TP | Reloj inteligente apoyado sobre un cuaderno con una not... | Bloqueo automático: Se encontró información de contacto (Instagram) que intenta dirigir al comp... | 16,695 ms | $0.000300 |
| 69 | caballo | caballo joven | BLOCKED | Block | TP | tambien permuto | El producto fue rechazado debido a que el animal presenta un estado de salud visiblemente preca... | 36,179 ms | $0.002769 |
| 71 | Zapatillas | Zapatillas clásicas de lona | BLOCKED | Block | TP | Estas zapatillas clásicas de lona son perfectas para el... | El producto fue rechazado debido a que presenta un estado de deterioro severo que lo hace inuti... | 34,131 ms | $0.002770 |
| 72 | sexual | masajista | BLOCKED | Block | TP | de jueves a sabados | El producto fue rechazado debido a una clara disonancia visual entre el título y la imagen, la ... | 37,148 ms | $0.003088 |
| 75 | celulares | iPhone 13 Pro | BLOCKED | Block | TP | El iPhone 13 Pro cuenta con una impresionante pantalla ... | Bloqueo automático: La descripción incluye una referencia a un número de contacto para acceso r... | 16,942 ms | $0.000402 |
| 76 | Zapatillas | Zapatillas marrones de cuero con cordo... | BLOCKED | Block | TP | Zapatillas marrones de cuero, elegantes y versátiles, p... | El producto fue rechazado debido a una anomalía crítica en el precio, el cual se encuentra sign... | 44,949 ms | $0.003034 |
| 77 | alimentos_crudos | Pan y pastelería recién horneados | BLOCKED | Block | TP | Una selección de deliciosos productos horneados, incluy... | Risk score 1.00 computed. | 34,902 ms | $0.002399 |
| 79 | sexual | Hombre - servicios de masajes intimos | BLOCKED | Block | TP |  | Bloqueo automático: El título indica servicios de contenido para adultos, lo cual está prohibid... | 15,194 ms | $0.000232 |
| 80 | celulares | Smartphone | BLOCKED | Approve | FN | Un smartphone moderno con diseño elegante, ideal para m... |  | 34,224 ms | $0.001949 |
| 83 | relojes | Smartwatch | BLOCKED | Block | TP | Un smartwatch moderno y elegante con pantalla vibrante ... | El producto fue rechazado debido a que la imagen muestra un dispositivo con la pantalla severam... | 34,669 ms | $0.002606 |
| 85 | celulares | Smartphone | BLOCKED | Block | TP | Smartphone, evitamos la plataforma | Bloqueo automático: La descripción indica explícitamente una intención de evadir la plataforma ... | 14,785 ms | $0.000229 |
| 86 | calzado | Zapatillas altas de gamuza gris para h... | BLOCKED | Block | TP | Presentando unas elegantes zapatillas altas para hombre... | Bloqueo automático: La descripción contiene información de contacto y una URL que dirigen al co... | 16,459 ms | $0.000329 |
| 92 | animales | Perro dalmata | BLOCKED | Block | TP | Cachorro. contactá a consultas84@gmail.com. | Bloqueo automático: La descripción contiene una dirección de correo electrónico, lo que constit... | 15,151 ms | $0.000280 |
| 95 | alimentos crudos | milanesas para hornear | BLOCKED | Block | TP | WA +54 9 49 6354-8285 | Bloqueo automático: Información de contacto proporcionada para evadir la plataforma. | 15,587 ms | $0.000224 |
| 96 | celulares | todos los mejores celus | BLOCKED | Block | TP | instagram en la foto | Risk score 1.00 computed. | 37,596 ms | $0.002712 |
| 97 | animales | pollitos vivos | BLOCKED | Block | TP | recien nacidos | Bloqueo automático: Se prohíbe la venta de animales vivos. | 17,287 ms | $0.000238 |
| 99 | ropa | remera nueva | BLOCKED | Block | TP | poco uso | El producto fue rechazado debido a una discrepancia significativa entre la descripción de 'nuev... | 35,418 ms | $0.003056 |

---
*Generated by Gemini 3.1 Flash-Lite Eval Framework — 2026-05-31 22:24:21*
