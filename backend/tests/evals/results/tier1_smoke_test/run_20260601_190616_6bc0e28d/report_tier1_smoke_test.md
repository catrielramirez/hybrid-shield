# AI Moderation Agent — Evaluation Report

**Dataset (Tier):** `tier1_smoke_test` | **Hash:** `6bc0e28d` | **Items:** 40
**Model:** Gemini 3.1 Flash-Lite | **Date:** 2026-06-01 19:13:56

---

## Overall Verdict: **FAIL**

---

## 1. Dataset Distribution

| Category | Ground Truth | Agent Prediction |
| :--- | :---: | :---: |
| Blocked (Scam/Fraud) | 20 | 18 |
| Passed (Legitimate) | 20 | 16 |
| Human Review (HITL) | — | 6 |

---

## 2. Technical Metrics

| Metric | Value | Threshold | Status |
| :--- | :---: | :---: | :---: |
| Precision | 100.00% | >= 85.00% | PASS |
| Recall | 94.74% | >= 90.00% | PASS |
| F1-Score | 97.30% | >= 87.00% | PASS |
| Automation Rate | 85.00% | >= 80.00% | PASS |
| System Error Rate | 0.00% | <= 5.00% | PASS |
| P95 Latency (total) | 369,063 ms | <= 36,000 ms | FAIL |
| Avg Latency (total) | 236,339 ms | — | — |

> **Nota sobre HITL:** Los 6 casos enviados a revisión humana se excluyen
> del cálculo de precisión/recall. La automation rate los penaliza correctamente.

---

## 3. Confusion Matrix

| | Predicted **Block** | Predicted **Pass** |
| :--- | :---: | :---: |
| **Actual Block** | 18 TP | 1 FN |
| **Actual Pass** | 0 FP | 15 TN |

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
| `pre_filter` | 7,324 ms | 29,415 ms | 15,121 | 5,990 | $0.000319 | $0.012765 |
| `extractor` | 9,466 ms | 20,684 ms | 73,779 | 7,889 | $0.000757 | $0.030277 |
| `rag` | 4,779 ms | 34,365 ms | — | — | — | — |
| `risk_evaluator` | 34 ms | 144 ms | — | — | — | — |
| `reasoning` | 3,051 ms | 12,176 ms | 11,704 | 2,541 | $0.000168 | $0.006737 |
| `decision` | 699 ms | 1,191 ms | — | — | — | — |
| `fly_wheel` | 102 ms | 469 ms | — | — | — | — |
| **Total** | 236,339 ms | 369,063 ms | 100,604 | 16,420 | $0.001244 | $0.049800 |

> Tokens y costos se muestran solo para nodos con llamadas LLM. El resto muestra — (determinístico/sin costo).

---

## 6. Cost Summary

- **Total Evaluation Cost:** $0.0498 USD
- **Average Cost per Item:** $0.001244 USD
- **Total Input Tokens:** 100,604
- **Total Output Tokens:** 16,420

---

## 7. Error Analysis

### False Positives

Ninguno. ✓


### False Negatives — fraudes no detectados (1 casos)

| ID | Category | Title | Reasoning |
| :--- | :--- | :--- | :--- |
| 80 | celulares | Smartphone |  |


---

## 8. Per-Item Evaluation Trace

| ID | Category | Title | Ground Truth | Predicted | Outcome | Description | Reasoning | Latency | Cost |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| 1 | Zapatillas | Zapatillas Casuales de Lona Unisex - C... | PASSED | Approve | TN | Descubre la comodidad y el estilo con estas zapatillas ... | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 93,347 ms | $0.001270 |
| 5 | celulares | iPhone 15 Pro Max - Pantalla Super Ret... | PASSED | Human Review | HITL | Descubre el nuevo iPhone 15 Pro Max, diseñado con titan... | El producto fue rechazado debido a una anomalía significativa en el precio, el cual excede ampl... | 87,613 ms | $0.001857 |
| 6 | Zapatillas | Zapatillas de Lona Blanca Clásicas par... | PASSED | Approve | TN | Descubre el estilo atemporal con estas zapatillas de lo... | Risk score 0.00 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 87,114 ms | $0.001299 |
| 10 | celulares | iPhone 14 Pro Max - Pantalla Inmersiva... | PASSED | Human Review | HITL | Descubre el iPhone 14 Pro Max, diseñado para ofrecerte ... | El producto fue rechazado debido a una anomalía significativa en el precio, el cual excede ampl... | 101,187 ms | $0.001831 |
| 17 | grandes_electrodomesticos | Heladera RTX32. 90 litros | PASSED | Approve | TN | Ultima generacion | Risk score 0.25 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 103,903 ms | $0.001382 |
| 16 | ropa | Piloto de lluvia dama | PASSED | Human Review | HITL | Varios colores | El producto fue rechazado debido a una discrepancia entre la descripción y la imagen, ya que se... | 104,512 ms | $0.001802 |
| 21 | calzado | Zapatillas Deportivas Azules de Gamuza... | PASSED | Approve | TN | Descubre el estilo y la comodidad con estas zapatillas ... | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 119,875 ms | $0.001337 |
| 22 | alimentos_y_bebidas | Pastel de Tiramisú Clásico con Granos ... | PASSED | Approve | TN | Disfruta de nuestro exquisito pastel de tiramisú, elabo... | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 120,145 ms | $0.001318 |
| 19 | lamparas | Lámparas Ajustables | PASSED | Approve | TN | Ilumina tu espacio creativo con este set de escritorio ... | Risk score 0.25 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 123,736 ms | $0.001368 |
| 23 | relojes | Reloj elegante con Pantalla Táctil y M... | PASSED | Approve | TN | Descubre el Smartwatch definitivo, diseñado para comple... | Risk score 0.00 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 145,082 ms | $0.001354 |
| 30 | autos_y_camionetas | Auto ford azul | PASSED | Approve | TN | titular al dia | Risk score 0.15 < 0.35. Confidence=0.95. Uncertainty=0.05. Action: Approve. | 165,230 ms | $0.001464 |
| 28 | ropa | Piloto de lluvia para perro | PASSED | Approve | TN | Maxima calidad de impermeabilidad | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 167,048 ms | $0.001462 |
| 34 | bazar_y_cocina | Juego de Vasos de Vidrio y Cerámica co... | PASSED | Approve | TN | Este set incluye un vaso de vidrio con detalles en blan... | Risk score 0.25 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 207,283 ms | $0.001353 |
| 31 | bazar_y_cocina | Equipo de mate | PASSED | Approve | TN | Kit completo: industria argentina | Risk score 0.00 < 0.35. Confidence=0.95. Uncertainty=0.05. Action: Approve. | 213,416 ms | $0.001571 |
| 35 | ropa | Camiseta de river 2026 | PASSED | Approve | TN | original - varios talles | Risk score 0.15 < 0.35. Confidence=0.95. Uncertainty=0.05. Action: Approve. | 216,381 ms | $0.001556 |
| 38 | alimentos_y_bebidas | miel  | PASSED | Approve | TN | maxima calidad | Risk score 0.15 < 0.35. Confidence=0.95. Uncertainty=0.05. Action: Approve. | 238,974 ms | $0.001348 |
| 37 | pequeños_electrodomesticos | conservadora electrica | PASSED | Human Review | HITL | bateria con 8 horas de duracion. Especial para bebidas ... | El producto fue rechazado debido a una discrepancia visual significativa entre el objeto mostra... | 240,746 ms | $0.002190 |
| 40 | muebles_interior | Juego de mesa con cuatro sillas | PASSED | Approve | TN | Materiales de primera calidad. Garantia por un año | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 240,890 ms | $0.001501 |
| 56 | calzado | Zapatillas | BLOCKED | Block | TP | WhatsApp +54 9 202 8580-6514 | Bloqueo automático: Contiene información de contacto (número de WhatsApp) para evadir la plataf... | 243,760 ms | $0.000220 |
| 57 | drogas | Fl0res de cannabis y mas | BLOCKED | Block | TP | whatsapp 022333232 | Bloqueo automático: La publicación contiene información de contacto (número de WhatsApp) para e... | 246,538 ms | $0.000321 |
| 48 | accesorios_para_mascotas | Colchon para gato | PASSED | Approve | TN | Mayor confort para tus mascotas | Risk score 0.15 < 0.35. Confidence=0.98. Uncertainty=0.02. Action: Approve. | 251,622 ms | $0.001457 |
| 45 | celulares | Smartphone Negro Brillante con Cámara ... | PASSED | Human Review | HITL | Descubre este elegante smartphone en acabado negro bril... | El producto fue rechazado debido a una discrepancia significativa entre la descripción textual ... | 253,385 ms | $0.002005 |
| 68 | relojes | Smartwatch con nota adhesiva amarilla.... | BLOCKED | Block | TP | Reloj inteligente apoyado sobre un cuaderno con una not... | Bloqueo automático: Se encontró información de contacto (Instagram) que intenta dirigir al comp... | 252,427 ms | $0.000300 |
| 67 | bazar_y_cocina | Cafetera express italiana | BLOCKED | Block | TP | solo podes comprar en calle alsina 3232, san marcos | Bloqueo automático: La descripción contiene una dirección física para completar la compra, lo q... | 268,101 ms | $0.000255 |
| 72 | sexual | masajista | BLOCKED | Block | TP | de jueves a sabados | El producto fue rechazado debido a que la imagen presenta contenido censurado y no corresponde ... | 286,529 ms | $0.001795 |
| 69 | caballo | caballo joven | BLOCKED | Block | TP | tambien permuto | El producto fue rechazado debido a que presenta un estado de salud deficiente y una disonancia ... | 288,752 ms | $0.001744 |
| 71 | Zapatillas | Zapatillas clásicas de lona | BLOCKED | Block | TP | Estas zapatillas clásicas de lona son perfectas para el... | El producto fue rechazado debido a una discrepancia significativa entre la descripción y el est... | 290,490 ms | $0.001989 |
| 75 | celulares | iPhone 13 Pro | BLOCKED | Block | TP | El iPhone 13 Pro cuenta con una impresionante pantalla ... | Bloqueo automático: La descripción incluye una referencia a un número de contacto para acceso r... | 290,640 ms | $0.000402 |
| 79 | sexual | Hombre - servicios de masajes intimos | BLOCKED | Block | TP |  | Bloqueo automático: Contenido sexualmente explícito. | 292,647 ms | $0.000223 |
| 76 | Zapatillas | Zapatillas marrones de cuero con cordo... | BLOCKED | Human Review | HITL | Zapatillas marrones de cuero, elegantes y versátiles, p... | El producto fue rechazado debido a una anomalía significativa en el precio, ya que el valor de ... | 309,737 ms | $0.001743 |
| 77 | alimentos_crudos | Pan y pastelería recién horneados | BLOCKED | Block | TP | Una selección de deliciosos productos horneados, incluy... | El producto fue rechazado debido a una discrepancia significativa entre el precio listado y el ... | 311,610 ms | $0.002049 |
| 80 | celulares | Smartphone | BLOCKED | Unknown | FN | Un smartphone moderno con diseño elegante, ideal para m... |  | 319,598 ms | $0.001278 |
| 85 | celulares | Smartphone | BLOCKED | Block | TP | Smartphone, evitamos la plataforma | Bloqueo automático: La descripción indica explícitamente una intención de evadir la plataforma ... | 321,616 ms | $0.000229 |
| 92 | animales | Perro dalmata | BLOCKED | Block | TP | Cachorro. contactá a consultas84@gmail.com. | Bloqueo automático: La descripción contiene una dirección de correo electrónico, lo que constit... | 338,002 ms | $0.000280 |
| 86 | calzado | Zapatillas altas de gamuza gris para h... | BLOCKED | Block | TP | Presentando unas elegantes zapatillas altas para hombre... | Bloqueo automático: La descripción contiene información de contacto y una URL que dirigen al co... | 338,075 ms | $0.000329 |
| 83 | relojes | Smartwatch | BLOCKED | Block | TP | Un smartwatch moderno y elegante con pantalla vibrante ... | Risk score 1.00 computed. | 339,980 ms | $0.001346 |
| 95 | alimentos crudos | milanesas para hornear | BLOCKED | Block | TP | WA +54 9 49 6354-8285 | Bloqueo automático: Contiene información de contacto (número de teléfono) que intenta dirigir l... | 342,719 ms | $0.000311 |
| 97 | animales | pollitos vivos | BLOCKED | Block | TP | recien nacidos | Bloqueo automático: Se prohíbe la venta de animales vivos. | 347,416 ms | $0.000238 |
| 96 | celulares | todos los mejores celus | BLOCKED | Block | TP | instagram en la foto | El producto fue rechazado debido a la presencia de información de contacto externa en la imagen... | 370,202 ms | $0.001969 |
| 99 | ropa | remera nueva | BLOCKED | Block | TP | poco uso | El producto fue rechazado debido a una discrepancia significativa entre la descripción de 'reme... | 373,217 ms | $0.002033 |

---
*Generated by Gemini 3.1 Flash-Lite Eval Framework — 2026-06-01 19:13:56*
