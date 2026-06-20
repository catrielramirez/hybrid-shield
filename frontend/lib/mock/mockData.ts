/**
 * Mock data for demo mode.
 * Activated via NEXT_PUBLIC_DATA_SOURCE=mock
 *
 * Products reflect real Argentine e-commerce in 2026:
 * - ARS prices based on USD ~$1,100 ARS/USD (June 2026)
 * - Covers 3 flows: Approve / Block / Human Review
 * - Each job has full fields needed by both page.tsx and hitl/page.tsx
 */

import type { AnalysisResult } from "@/app/actions/analyze";

export interface MockJob {
  id: string;
  thread_id: string;
  status: string;
  final_action: "Approve" | "Block" | "Human Review";
  title: string;
  description: string;
  price: number;
  image_url: string;
  risk_score: number;
  uncertainty: number;
  reasoning: string;
  signals: {
    visual_dissonance: boolean;
    contact_info_detected: boolean;
    price_anomaly: boolean;
    condition_issue?: boolean;
    policy_match: boolean;
  };
  policy_violations?: Array<{ policy_id: string; factor: string; explanation: string }>;
  policy_citations?: Array<{
    policy_id: string;
    policy_title: string;
    snippet: string;
    reason: string;
    relevance_score: number;
  }>;
  risk_breakdown?: Array<{ factor: string; weight: number }>;
  features: {
    primary_object?: string;
    object_category?: string;
    objects_detected?: string[];
    text_in_image?: string[];
    contact_info_detected?: boolean;
    visual_dissonance?: boolean;
    product_condition?: string;
    condition_issue_detected?: boolean;
    image_quality?: string;
    image_type?: string;
    is_sellable?: boolean;
    fraud_signals?: string[];
    confidence?: number;
    error?: string;
  };
  min_price?: number;
  max_price?: number;
  routing_reason?: string;
  created_at: string;
  last_update: string;
  trace: Array<{
    checkpoint_id: string;
    next_node: string;
    status: string;
    timestamp: string;
    state: Record<string, any>;
  }>;
}

// ─── Helper to generate ISO timestamps relative to now ──────────────────────
function hoursAgo(h: number): string {
  return new Date(Date.now() - h * 3600 * 1000).toISOString();
}

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * 60 * 1000).toISOString();
}

// ─── TRACE TEMPLATES ─────────────────────────────────────────────────────────
function buildTrace(jobId: string, finalAction: string, riskScore: number): MockJob["trace"] {
  const base = new Date(Date.now() - 4 * 60 * 1000);
  const t = (offsetSeconds: number) =>
    new Date(base.getTime() + offsetSeconds * 1000).toISOString();

  return [
    {
      checkpoint_id: `${jobId}-cp1`,
      next_node: "EXTRACTOR",
      status: "completed",
      timestamp: t(0),
      state: {
        resumen: "Nodo de extracción visual completado. Se identificaron características del producto desde la imagen.",
        job_id: jobId,
        phase: "extraction",
      },
    },
    {
      checkpoint_id: `${jobId}-cp2`,
      next_node: "RAG_RETRIEVAL",
      status: "completed",
      timestamp: t(15),
      state: {
        resumen: "Recuperación de políticas completada. Se encontraron políticas relevantes en la base de conocimiento.",
        rag_hits: 3,
        top_policy: "POL-001",
      },
    },
    {
      checkpoint_id: `${jobId}-cp3`,
      next_node: "RISK_AGGREGATION",
      status: "completed",
      timestamp: t(35),
      state: {
        resumen: `Señales de riesgo agregadas. Score calculado: ${riskScore.toFixed(2)}.`,
        risk_score: riskScore,
        signals_active: riskScore > 0.5 ? 2 : 0,
      },
    },
    {
      checkpoint_id: `${jobId}-cp4`,
      next_node: "DECISION",
      status: "completed",
      timestamp: t(55),
      state: {
        resumen: `Decisión tomada: ${finalAction}. El grafo finalizó su ejecución.`,
        final_action: finalAction,
        flow_completed: true,
      },
    },
  ];
}

// ─── THE 22 MOCK JOBS ─────────────────────────────────────────────────────────
export const MOCK_JOBS: MockJob[] = [
  // ══════════════════════════════════════════════════════
  // APPROVE CASES (8 productos legítimos)
  // ══════════════════════════════════════════════════════
  {
    id: "job-approve-001",
    thread_id: "job-approve-001",
    status: "APPROVE",
    final_action: "Approve",
    title: "iPhone 15 Pro 256GB – Titanio Natural – Usado 10 puntos",
    description:
      "iPhone 15 Pro en perfecto estado. Comprado en Apple Store Palermo en diciembre 2024. Sin rayones, batería al 96%, todos los accesorios originales incluidos. Factura de compra disponible. Ideal para cambio de equipo.",
    price: 1850000,
    image_url: "/mock/iphone15pro.png",
    risk_score: 0.11,
    uncertainty: 0.08,
    min_price: 1600000,
    max_price: 2100000,
    routing_reason: "auto_approved",
    reasoning:
      "El producto es un iPhone 15 Pro usado en buen estado. El precio de $1.850.000 ARS es consistente con el mercado secundario argentino para este modelo (rango típico $1.600.000–$2.100.000). No se detectaron señales de fraude ni violaciones de política. Se aprueba la publicación.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      condition_issue: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-003",
        policy_title: "Dispositivos electrónicos de segunda mano",
        snippet: "Los dispositivos usados pueden publicarse siempre que se declare el estado real y no se incluya información de contacto externo a la plataforma.",
        reason: "Verificación estándar para electrónicos usados",
        relevance_score: 0.91,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.05 },
      { factor: "policy_match", weight: 0.04 },
    ],
    features: {
      primary_object: "Smartphone",
      object_category: "Electrónica",
      objects_detected: ["iPhone", "caja original", "cable USB-C"],
      text_in_image: [],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Usado – muy buen estado",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto real del producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.95,
    },
    created_at: hoursAgo(18),
    last_update: hoursAgo(17.5),
    trace: buildTrace("job-approve-001", "Approve", 0.11),
  },

  {
    id: "job-approve-002",
    thread_id: "job-approve-002",
    status: "APPROVE",
    final_action: "Approve",
    title: "Smart TV Samsung 55\" QLED 4K Q70D – Nuevo sellado",
    description:
      "Televisor Samsung QLED 55 pulgadas modelo Q70D 2024. Nuevo en caja sellada con garantía oficial Samsung Argentina 1 año. Quantum HDR, Tizen OS, 4 puertos HDMI. Retiro en San Isidro o envío a domicilio por Andreani.",
    price: 870000,
    image_url: "/mock/samsung_tv.png",
    risk_score: 0.08,
    uncertainty: 0.06,
    min_price: 780000,
    max_price: 950000,
    routing_reason: "auto_approved",
    reasoning:
      "TV Samsung nuevo sellado con garantía oficial. Precio de $870.000 ARS está dentro del rango de mercado para este modelo. Sin señales de fraude ni inconsistencias visuales. Publicación aprobada.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      condition_issue: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-002",
        policy_title: "Electrónica de consumo masivo",
        snippet: "Los televisores y electrodomésticos nuevos con garantía de fábrica son elegibles para publicación estándar.",
        reason: "Producto estándar de electrónica",
        relevance_score: 0.88,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.03 },
      { factor: "policy_match", weight: 0.03 },
    ],
    features: {
      primary_object: "Televisor",
      object_category: "Electrónica del hogar",
      objects_detected: ["TV Samsung", "caja sellada", "control remoto"],
      text_in_image: ["SAMSUNG", "QLED 4K"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto nuevo",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.97,
    },
    created_at: hoursAgo(14),
    last_update: hoursAgo(13.7),
    trace: buildTrace("job-approve-002", "Approve", 0.08),
  },

  {
    id: "job-approve-003",
    thread_id: "job-approve-003",
    status: "APPROVE",
    final_action: "Approve",
    title: "Laptop Lenovo IdeaPad 5 AMD Ryzen 5 7530U 16GB RAM – Nueva",
    description:
      "Notebook Lenovo IdeaPad 5 con AMD Ryzen 5 7530U, 16GB RAM DDR4, SSD 512GB, pantalla 15.6\" Full HD IPS. Color gris ártico. Nueva en caja con garantía de 1 año. Factura A disponible. Excelente relación precio-calidad para trabajo y estudio.",
    price: 740000,
    image_url: "/mock/laptop_lenovo.png",
    risk_score: 0.09,
    uncertainty: 0.07,
    min_price: 680000,
    max_price: 820000,
    routing_reason: "auto_approved",
    reasoning:
      "Notebook nueva con especificaciones detalladas y precio consistente con el mercado. La descripción incluye número de modelo, specs técnicas verificables y modalidad de factura. Sin señales de fraude. Aprobado.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-002",
        policy_title: "Electrónica de consumo masivo",
        snippet: "Las computadoras personales nuevas con especificaciones técnicas verificables son aptas para publicación estándar.",
        reason: "Laptop nueva con factura",
        relevance_score: 0.86,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.03 },
      { factor: "price_anomaly", weight: 0.04 },
      { factor: "policy_match", weight: 0.02 },
    ],
    features: {
      primary_object: "Laptop",
      object_category: "Computación",
      objects_detected: ["laptop Lenovo", "teclado", "pantalla"],
      text_in_image: ["LENOVO"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto real del producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.94,
    },
    created_at: hoursAgo(10),
    last_update: hoursAgo(9.5),
    trace: buildTrace("job-approve-003", "Approve", 0.09),
  },

  {
    id: "job-approve-004",
    thread_id: "job-approve-004",
    status: "APPROVE",
    final_action: "Approve",
    title: "Auriculares Sony WH-1000XM5 – Cancelación de ruido – Nuevo",
    description:
      "Sony WH-1000XM5, la mejor cancelación de ruido del mercado. Nuevos, sin abrir, con garantía oficial Sony Argentina 1 año. 30hs de batería, audio Hi-Res, conectividad multipoint. Color negro. Ideal para home office y viajes.",
    price: 395000,
    image_url: "/mock/sony_headphones.png",
    risk_score: 0.07,
    uncertainty: 0.05,
    min_price: 350000,
    max_price: 460000,
    routing_reason: "auto_approved",
    reasoning:
      "Auriculares Sony WH-1000XM5 nuevos con garantía oficial. Precio $395.000 ARS dentro del rango de mercado. Descripción técnica precisa y coherente con el producto visual. Publicación aprobada.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-002",
        policy_title: "Electrónica de consumo masivo",
        snippet: "Los auriculares y dispositivos de audio nuevos con garantía de fabricante son elegibles para publicación estándar.",
        reason: "Producto de audio estándar",
        relevance_score: 0.82,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.03 },
      { factor: "policy_match", weight: 0.02 },
    ],
    features: {
      primary_object: "Auriculares",
      object_category: "Audio",
      objects_detected: ["auriculares Sony", "estuche", "cable USB-C"],
      text_in_image: ["SONY"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.96,
    },
    created_at: hoursAgo(8),
    last_update: hoursAgo(7.7),
    trace: buildTrace("job-approve-004", "Approve", 0.07),
  },

  {
    id: "job-approve-005",
    thread_id: "job-approve-005",
    status: "APPROVE",
    final_action: "Approve",
    title: "Drone DJI Mini 3 Pro + Control RC-N2 – Nuevo sellado",
    description:
      "DJI Mini 3 Pro con control RC-N2 incluido. Nuevo en caja sellada. Cámara 4K/60fps, 34 min vuelo, peso <249g (sin registro ANAC). Importación directa con factura. Garantía 6 meses. Solo retiro Capital Federal o envío asegurado.",
    price: 680000,
    image_url: "https://images.unsplash.com/photo-1579829366248-204fe8413f31?w=800&q=80",
    risk_score: 0.13,
    uncertainty: 0.09,
    min_price: 600000,
    max_price: 780000,
    routing_reason: "auto_approved",
    reasoning:
      "Drone DJI Mini 3 Pro nuevo con factura. El peso <249g lo exime del registro ANAC obligatorio en Argentina, aspecto correctamente aclarado en la descripción. Precio dentro del rango. Sin señales de fraude. Aprobado.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-007",
        policy_title: "Vehículos aéreos no tripulados",
        snippet: "Los drones con peso inferior a 250g están permitidos para publicación sin registro previo conforme normativa ANAC vigente.",
        reason: "Verificación normativa ANAC para drones",
        relevance_score: 0.93,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.04 },
      { factor: "price_anomaly", weight: 0.06 },
      { factor: "policy_match", weight: 0.03 },
    ],
    features: {
      primary_object: "Drone",
      object_category: "Fotografía / Tecnología",
      objects_detected: ["drone DJI", "control remoto", "baterías", "caja"],
      text_in_image: ["DJI", "Mini 3 Pro"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.92,
    },
    created_at: hoursAgo(6),
    last_update: hoursAgo(5.7),
    trace: buildTrace("job-approve-005", "Approve", 0.13),
  },

  {
    id: "job-approve-006",
    thread_id: "job-approve-006",
    status: "APPROVE",
    final_action: "Approve",
    title: "Monitor LG 27\" IPS 144Hz QHD – Nuevo con factura",
    description:
      "Monitor LG 27GP850-B, 27 pulgadas, resolución 2560x1440 QHD, panel Nano-IPS, 144Hz, 1ms GtG. Nuevo en caja con factura A. Garantía oficial LG 3 años. Puerto DisplayPort + 2x HDMI. Ideal para gaming y diseño gráfico profesional.",
    price: 320000,
    image_url: "https://images.unsplash.com/photo-1527443224154-c4a573d5b6a4?w=800&q=80",
    risk_score: 0.06,
    uncertainty: 0.05,
    min_price: 280000,
    max_price: 370000,
    routing_reason: "auto_approved",
    reasoning:
      "Monitor LG nuevo con especificaciones técnicas completas y precio dentro del rango de mercado. Producto estándar de electrónica de consumo. Sin señales de alerta. Aprobado.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.02 },
      { factor: "policy_match", weight: 0.02 },
    ],
    features: {
      primary_object: "Monitor",
      object_category: "Computación",
      objects_detected: ["monitor LG", "base ajustable", "cables"],
      text_in_image: ["LG", "27GP850"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.98,
    },
    created_at: hoursAgo(4),
    last_update: hoursAgo(3.7),
    trace: buildTrace("job-approve-006", "Approve", 0.06),
  },

  {
    id: "job-approve-007",
    thread_id: "job-approve-007",
    status: "APPROVE",
    final_action: "Approve",
    title: "Silla Ergonómica HM Chairs Pro – Lumbar ajustable – Nueva",
    description:
      "Silla ergonómica de oficina HM Chairs Pro con soporte lumbar ajustable, apoyabrazos 4D, reposacabezas, altura regulable. Peso máx 130kg. Fabricación nacional, garantía 2 años. Colores: negro/gris. Envío a todo el país con flete bonificado en CABA y GBA.",
    price: 185000,
    image_url: "https://images.unsplash.com/photo-1585412727339-54e4bae3bbf9?w=800&q=80",
    risk_score: 0.05,
    uncertainty: 0.04,
    min_price: 150000,
    max_price: 220000,
    routing_reason: "auto_approved",
    reasoning:
      "Silla ergonómica de fabricación nacional con precio razonable y descripción completa. Producto de mobiliario de oficina sin restricciones. Aprobado.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.02 },
      { factor: "policy_match", weight: 0.01 },
    ],
    features: {
      primary_object: "Silla de oficina",
      object_category: "Muebles",
      objects_detected: ["silla ergonómica", "apoyabrazos", "ruedas"],
      text_in_image: [],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media-alta",
      image_type: "Foto de producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.97,
    },
    created_at: hoursAgo(2),
    last_update: hoursAgo(1.7),
    trace: buildTrace("job-approve-007", "Approve", 0.05),
  },

  {
    id: "job-approve-008",
    thread_id: "job-approve-008",
    status: "APPROVE",
    final_action: "Approve",
    title: "Yerba Mate Exportación Amanda Premium 500g x20 – Lote",
    description:
      "Lote de 20 paquetes de Yerba Mate Amanda Premium 500g c/u, apta para exportación. Certificación SENASA vigente, habilitación INYM. Ideal para distribuidores en Europa y USA. Precio por lote mayorista. Factura A con CUIT.",
    price: 160000,
    image_url: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    risk_score: 0.10,
    uncertainty: 0.07,
    min_price: 130000,
    max_price: 190000,
    routing_reason: "auto_approved",
    reasoning:
      "Producto de exportación de yerba mate con certificaciones SENASA e INYM correctamente declaradas. Precio por lote mayorista dentro de rango. Producto alimenticio sin restricciones para comercio. Aprobado.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-010",
        policy_title: "Alimentos y bebidas para exportación",
        snippet: "Los productos alimenticios con certificación SENASA vigente son elegibles para publicación en categoría de exportación.",
        reason: "Verificación de habilitaciones sanitarias",
        relevance_score: 0.88,
      },
    ],
    risk_breakdown: [
      { factor: "visual_dissonance", weight: 0.03 },
      { factor: "price_anomaly", weight: 0.05 },
      { factor: "policy_match", weight: 0.02 },
    ],
    features: {
      primary_object: "Yerba mate",
      object_category: "Alimentos y bebidas",
      objects_detected: ["paquetes de yerba", "logo AMANDA"],
      text_in_image: ["AMANDA", "500g", "SENASA"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: true,
      fraud_signals: [],
      confidence: 0.91,
    },
    created_at: minutesAgo(45),
    last_update: minutesAgo(40),
    trace: buildTrace("job-approve-008", "Approve", 0.10),
  },

  // ══════════════════════════════════════════════════════
  // BLOCK CASES (7 productos con violaciones claras)
  // ══════════════════════════════════════════════════════
  {
    id: "job-block-001",
    thread_id: "job-block-001",
    status: "BLOCK",
    final_action: "Block",
    title: "Zapatillas Nike Air Jordan 1 High OG \"Originales\" – Talle 42",
    description:
      "Nike Air Jordan 1 High OG originales, sin uso. Talle 42. Caja original incluida. WhatsApp al 11-5544-3322 para consultas. Acepto Mercado Pago.",
    price: 28000,
    image_url: "/mock/nike_replica.png",
    risk_score: 0.94,
    uncertainty: 0.06,
    min_price: 280000,
    max_price: 420000,
    routing_reason: "auto_blocked",
    reasoning:
      "Múltiples señales de fraude detectadas: (1) El precio de $28.000 ARS representa apenas el 7-10% del valor de mercado para este modelo ($280.000–$420.000), señal típica de réplicas o fraude. (2) Se detectó información de contacto externo (número de WhatsApp) en la descripción, práctica prohibida por política. (3) Análisis visual sugiere inconsistencias en el logo y costuras del calzado.",
    signals: {
      visual_dissonance: true,
      contact_info_detected: true,
      price_anomaly: true,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-001",
        factor: "contact_info_detected",
        explanation: "La descripción contiene un número de WhatsApp (11-5544-3322), lo que viola la política de comunicación exclusiva dentro de la plataforma.",
      },
      {
        policy_id: "POL-005",
        factor: "price_anomaly",
        explanation: "El precio ($28.000 ARS) es un 90% inferior al rango de mercado documentado ($280.000–$420.000 ARS), indicador de posible réplica o fraude.",
      },
      {
        policy_id: "POL-008",
        factor: "visual_dissonance",
        explanation: "El análisis visual detectó inconsistencias en el logo Nike y calidad de materiales inconsistentes con producto original.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-001",
        policy_title: "Prohibición de contacto externo",
        snippet: "Está prohibido incluir información de contacto externo (teléfonos, emails, redes sociales) en descripciones de productos.",
        reason: "Número de WhatsApp detectado",
        relevance_score: 0.99,
      },
      {
        policy_id: "POL-005",
        policy_title: "Anomalías de precio en calzado de marca",
        snippet: "Calzado de marca premium con precio inferior al 30% del valor de mercado verificado es considerado de alto riesgo de falsificación.",
        reason: "Precio 90% por debajo del mercado",
        relevance_score: 0.97,
      },
    ],
    risk_breakdown: [
      { factor: "contact_info_detected", weight: 0.40 },
      { factor: "price_anomaly", weight: 0.35 },
      { factor: "visual_dissonance", weight: 0.19 },
    ],
    features: {
      primary_object: "Zapatillas deportivas",
      object_category: "Calzado",
      objects_detected: ["zapatillas Nike", "caja de calzado"],
      text_in_image: ["NIKE", "AIR JORDAN"],
      contact_info_detected: true,
      visual_dissonance: true,
      product_condition: "Sin uso (declarado)",
      condition_issue_detected: false,
      image_quality: "Media-baja",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["possible_replica", "external_contact", "price_manipulation"],
      confidence: 0.91,
    },
    created_at: hoursAgo(36),
    last_update: hoursAgo(35.5),
    trace: buildTrace("job-block-001", "Block", 0.94),
  },

  {
    id: "job-block-002",
    thread_id: "job-block-002",
    status: "BLOCK",
    final_action: "Block",
    title: "Clonazepam 2mg x30 comprimidos – Envío discreto a todo el país",
    description:
      "Clonazepam 2mg, caja de 30 comprimidos. Envío en sobre anónimo. Sin receta médica. Pago solo en efectivo o criptomoneda. Envíos Correo Argentino a todo el país.",
    price: 12000,
    image_url: "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&q=80",
    risk_score: 0.99,
    uncertainty: 0.01,
    min_price: 0,
    max_price: 0,
    routing_reason: "auto_blocked",
    reasoning:
      "Publicación bloqueada de forma automática. La venta de psicotrópicos de venta bajo receta (Clonazepam, Lista IV del SEDRONAR) sin receta médica constituye un delito federal en Argentina (Ley 23.737). La descripción explicita la venta sin receta y métodos de pago anónimos, señales inequívocas de actividad ilegal.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-011",
        factor: "policy_match",
        explanation: "Venta de medicamentos psicotrópicos controlados (Clonazepam) sin prescripción médica, prohibida por Ley 23.737 y políticas de la plataforma.",
      },
      {
        policy_id: "POL-012",
        factor: "policy_match",
        explanation: "La descripción menciona explícitamente 'sin receta médica' y métodos de pago anónimos (criptomoneda/efectivo), indicadores de evasión de controles.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-011",
        policy_title: "Medicamentos controlados y psicotrópicos",
        snippet: "Está absolutamente prohibida la venta de sustancias psicotrópicas y estupefacientes controlados por el SEDRONAR sin habilitación profesional vigente.",
        reason: "Medicamento de venta bajo receta",
        relevance_score: 1.0,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.90 },
      { factor: "visual_dissonance", weight: 0.05 },
      { factor: "price_anomaly", weight: 0.04 },
    ],
    features: {
      primary_object: "Medicamento",
      object_category: "Farmacia / Psicotrópicos",
      objects_detected: ["caja de medicamento", "comprimidos"],
      text_in_image: ["CLONAZEPAM", "2mg"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["controlled_substance", "no_prescription", "anonymous_payment"],
      confidence: 0.99,
    },
    created_at: hoursAgo(28),
    last_update: hoursAgo(27.5),
    trace: buildTrace("job-block-002", "Block", 0.99),
  },

  {
    id: "job-block-003",
    thread_id: "job-block-003",
    status: "BLOCK",
    final_action: "Block",
    title: "Perfume \"Chanel N°5\" 100ml Eau de Parfum – Importado",
    description:
      "Perfume Chanel N°5 EDP 100ml. Importado directo de Francia. Original garantizado. Precio especial de liquidación. Acepto transferencia o efectivo. Tel 011-4789-1122.",
    price: 18000,
    image_url: "/mock/suplemento.png",
    risk_score: 0.91,
    uncertainty: 0.07,
    min_price: 250000,
    max_price: 380000,
    routing_reason: "auto_blocked",
    reasoning:
      "Tres señales críticas de fraude: (1) Precio de $18.000 ARS versus rango de mercado $250.000–$380.000 para este producto original (93% por debajo), indicador principal de réplica. (2) Número de teléfono en descripción (011-4789-1122), violación de política de contacto externo. (3) La combinación 'original garantizado' + 'liquidación' + precio extremadamente bajo es un patrón de fraude documentado.",
    signals: {
      visual_dissonance: true,
      contact_info_detected: true,
      price_anomaly: true,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-001",
        factor: "contact_info_detected",
        explanation: "Número de teléfono (011-4789-1122) incluido en la descripción, violando la política de comunicación interna.",
      },
      {
        policy_id: "POL-005",
        factor: "price_anomaly",
        explanation: "Precio 93% inferior al valor de mercado para un perfume Chanel original. Patrón consistente con venta de réplicas.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-006",
        policy_title: "Productos de lujo y autenticidad",
        snippet: "Los productos de marcas de lujo requieren documentación de autenticidad o factura de importación verificable. Precios anómalos activan revisión automática.",
        reason: "Perfume de lujo con precio anómalo",
        relevance_score: 0.96,
      },
    ],
    risk_breakdown: [
      { factor: "price_anomaly", weight: 0.45 },
      { factor: "contact_info_detected", weight: 0.30 },
      { factor: "visual_dissonance", weight: 0.16 },
    ],
    features: {
      primary_object: "Perfume",
      object_category: "Belleza y fragancias",
      objects_detected: ["frasco de perfume", "caja"],
      text_in_image: [],
      contact_info_detected: true,
      visual_dissonance: true,
      product_condition: "Nuevo (sin abrir)",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["possible_replica", "external_contact", "price_manipulation"],
      confidence: 0.88,
    },
    created_at: hoursAgo(22),
    last_update: hoursAgo(21.5),
    trace: buildTrace("job-block-003", "Block", 0.91),
  },

  {
    id: "job-block-004",
    thread_id: "job-block-004",
    status: "BLOCK",
    final_action: "Block",
    title: "Cuchillo Táctico Militar K-BAR 7\" – Hoja de acero 1095",
    description:
      "Cuchillo K-BAR estilo militar, hoja de 7 pulgadas acero 1095, filo de doble cara. Incluye funda de cuero. Ideal para caza, supervivencia y defensa personal. Envío a todo el país. Solo mayores de 18.",
    price: 45000,
    image_url: "https://images.unsplash.com/photo-1607624400905-a5e76ecf4cde?w=800&q=80",
    risk_score: 0.87,
    uncertainty: 0.09,
    min_price: 35000,
    max_price: 65000,
    routing_reason: "auto_blocked",
    reasoning:
      "El artículo corresponde a un cuchillo táctico/militar con filo de doble cara, prohibido para venta en plataformas de e-commerce según Ley 20.429 (Armas de Guerra) y normativas de la RENAR. La mención explícita de 'defensa personal' eleva el riesgo al clasificar el objeto como potencialmente peligroso bajo el artículo 189 bis del Código Penal argentino.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-013",
        factor: "policy_match",
        explanation: "Cuchillo táctico de hoja de doble filo clasificado como arma blanca. Su venta online está prohibida sin habilitación RENAR.",
      },
      {
        policy_id: "POL-014",
        factor: "policy_match",
        explanation: "La descripción menciona 'defensa personal' como uso, lo que lo clasifica como arma blanca bajo la normativa argentina.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-013",
        policy_title: "Armas, cuchillos y elementos peligrosos",
        snippet: "Está prohibida la venta de cuchillos tácticos, militares, con hoja de doble filo o aquellos descritos con finalidad defensiva sin habilitación RENAR.",
        reason: "Cuchillo táctico de doble filo",
        relevance_score: 0.98,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.75 },
      { factor: "visual_dissonance", weight: 0.07 },
      { factor: "price_anomaly", weight: 0.05 },
    ],
    features: {
      primary_object: "Cuchillo táctico",
      object_category: "Herramientas / Armas blancas",
      objects_detected: ["cuchillo", "hoja metálica", "funda de cuero"],
      text_in_image: ["K-BAR"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["banned_object", "dangerous_item"],
      confidence: 0.93,
    },
    created_at: hoursAgo(16),
    last_update: hoursAgo(15.5),
    trace: buildTrace("job-block-004", "Block", 0.87),
  },

  {
    id: "job-block-005",
    thread_id: "job-block-005",
    status: "BLOCK",
    final_action: "Block",
    title: "Suplemento ULTRA QUEMA MAX – Adelgazante extremo 90 cápsulas",
    description:
      "ULTRA QUEMA MAX, el suplemento más potente del mercado. Baja hasta 10kg en 30 días garantizado. Fórmula importada de USA. Sin ANMAT porque es 100% natural. Envío en 48hs. Resultados comprobados.",
    price: 38000,
    image_url: "/mock/suplemento.png",
    risk_score: 0.89,
    uncertainty: 0.08,
    min_price: 0,
    max_price: 0,
    routing_reason: "auto_blocked",
    reasoning:
      "Producto bloqueado por múltiples violaciones: (1) La descripción contiene afirmaciones de salud no verificables ('baja hasta 10kg en 30 días garantizado'), prohibidas por ANMAT. (2) La frase 'Sin ANMAT porque es 100% natural' es una declaración de evasión regulatoria que viola la Ley 16.463. (3) Suplemento dietario sin número de aprobación ANMAT no puede comercializarse en Argentina.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-015",
        factor: "policy_match",
        explanation: "El producto carece de habilitación ANMAT (Disposición 1674/2002). La venta de suplementos sin aprobación regulatoria está prohibida.",
      },
      {
        policy_id: "POL-016",
        factor: "policy_match",
        explanation: "La publicación contiene afirmaciones de salud no avaladas: 'baja hasta 10kg garantizado'. Las promesas de pérdida de peso sin respaldo clínico están prohibidas.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-015",
        policy_title: "Suplementos dietarios y productos de salud",
        snippet: "Todo suplemento dietario debe contar con número de aprobación ANMAT vigente para ser comercializado en Argentina.",
        reason: "Ausencia declarada de aprobación ANMAT",
        relevance_score: 0.99,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.82 },
      { factor: "visual_dissonance", weight: 0.04 },
      { factor: "price_anomaly", weight: 0.03 },
    ],
    features: {
      primary_object: "Suplemento dietario",
      object_category: "Salud y bienestar",
      objects_detected: ["frasco de cápsulas", "etiqueta sin certificación"],
      text_in_image: ["ULTRA QUEMA MAX", "90 CÁPSULAS"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["unregulated_health_product", "misleading_claims"],
      confidence: 0.94,
    },
    created_at: hoursAgo(12),
    last_update: hoursAgo(11.5),
    trace: buildTrace("job-block-005", "Block", 0.89),
  },

  {
    id: "job-block-006",
    thread_id: "job-block-006",
    status: "BLOCK",
    final_action: "Block",
    title: "Cigarrillo Electrónico VUSE Alto – Pod con Nicotina 18mg – x3",
    description:
      "Pack de 3 pods VUSE Alto con nicotina 18mg. Compatibles con device VUSE original. Sabores: menta, tabaco, mango. Importados de USA. Envío discreto sin declarar contenido.",
    price: 22000,
    image_url: "https://images.unsplash.com/photo-1560472355-536de3962603?w=800&q=80",
    risk_score: 0.92,
    uncertainty: 0.05,
    min_price: 0,
    max_price: 0,
    routing_reason: "auto_blocked",
    reasoning:
      "La venta de cigarrillos electrónicos con nicotina está prohibida en Argentina por Resolución 731/2019 del Ministerio de Salud y confirmada por el Código Alimentario Argentino. Adicionalmente, la descripción menciona 'envío sin declarar contenido', lo que configura una intención explícita de evasión de controles aduaneros, agravando la violación.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-017",
        factor: "policy_match",
        explanation: "La venta de cigarrillos electrónicos con nicotina está prohibida en Argentina por Resolución MSN 731/2019.",
      },
      {
        policy_id: "POL-018",
        factor: "policy_match",
        explanation: "La mención de 'envío sin declarar contenido' implica evasión aduanera, lo que configura un agravante legal.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-017",
        policy_title: "Productos de tabaco y nicotina electrónica",
        snippet: "La comercialización de dispositivos de vapeo y cigarrillos electrónicos está prohibida en Argentina según normativa del Ministerio de Salud.",
        reason: "Producto prohibido por resolución ministerial",
        relevance_score: 1.0,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.88 },
      { factor: "visual_dissonance", weight: 0.02 },
      { factor: "price_anomaly", weight: 0.02 },
    ],
    features: {
      primary_object: "Cigarrillo electrónico",
      object_category: "Tabaco / Nicotina",
      objects_detected: ["pods de vapeo", "empaque VUSE"],
      text_in_image: ["VUSE", "NICOTINE 18mg"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: false,
      fraud_signals: ["banned_object", "customs_evasion"],
      confidence: 0.97,
    },
    created_at: hoursAgo(5),
    last_update: hoursAgo(4.5),
    trace: buildTrace("job-block-006", "Block", 0.92),
  },

  {
    id: "job-block-007",
    thread_id: "job-block-007",
    status: "BLOCK",
    final_action: "Block",
    title: "Tarjeta de Regalo Steam $50 USD – Código digital por WhatsApp",
    description:
      "Gift card Steam de $50 USD. Te mando el código por WhatsApp al comprar. Solo transferencia o Mercado Pago. Tengo stock de $5, $10, $20 y $50. Envío del código en menos de 2 horas. WA: 1130445566.",
    price: 55000,
    image_url: "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80",
    risk_score: 0.88,
    uncertainty: 0.10,
    min_price: 50000,
    max_price: 65000,
    routing_reason: "auto_blocked",
    reasoning:
      "Publicación de tarjetas de regalo digitales con entrega por canales externos (WhatsApp) detectada. La venta de códigos digitales con comunicación fuera de la plataforma y número de contacto en descripción viola múltiples políticas. Las tarjetas de regalo con entrega por WhatsApp son el método de estafa más frecuente en e-commerce argentino.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: true,
      price_anomaly: false,
      policy_match: true,
    },
    policy_violations: [
      {
        policy_id: "POL-001",
        factor: "contact_info_detected",
        explanation: "Número de WhatsApp en descripción (WA: 1130445566). Comunicación de entrega planificada fuera de la plataforma.",
      },
      {
        policy_id: "POL-019",
        factor: "policy_match",
        explanation: "Las tarjetas de regalo digitales deben entregarse a través del sistema de mensajería de la plataforma, no por canales externos.",
      },
    ],
    policy_citations: [
      {
        policy_id: "POL-019",
        policy_title: "Bienes digitales y tarjetas de regalo",
        snippet: "La entrega de bienes digitales (códigos, claves) a través de canales externos constituye una violación que expone al comprador a riesgo de estafa.",
        reason: "Entrega de código por WhatsApp",
        relevance_score: 0.95,
      },
    ],
    risk_breakdown: [
      { factor: "contact_info_detected", weight: 0.55 },
      { factor: "policy_match", weight: 0.28 },
      { factor: "visual_dissonance", weight: 0.05 },
    ],
    features: {
      primary_object: "Tarjeta de regalo digital",
      object_category: "Bienes digitales",
      objects_detected: ["imagen de tarjeta Steam"],
      text_in_image: ["STEAM", "$50"],
      contact_info_detected: true,
      visual_dissonance: false,
      product_condition: "N/A (digital)",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Imagen representativa",
      is_sellable: false,
      fraud_signals: ["external_contact", "digital_scam_pattern"],
      confidence: 0.89,
    },
    created_at: minutesAgo(90),
    last_update: minutesAgo(85),
    trace: buildTrace("job-block-007", "Block", 0.88),
  },

  // ══════════════════════════════════════════════════════
  // HUMAN REVIEW CASES (5 casos ambiguos)
  // ══════════════════════════════════════════════════════
  {
    id: "job-review-001",
    thread_id: "job-review-001",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Pistola Airsoft Glock 17 Réplica – 6mm – Competición",
    description:
      "Réplica de pistola Glock 17 para airsoft, calibre 6mm BBs. Uso exclusivo para partidas de airsoft y competición. Material plástico reforzado y metal en partes internas. NO es arma de fuego real. FPS: 280. Envío a domicilio con embalaje discreto.",
    price: 95000,
    image_url: "https://images.unsplash.com/photo-1595590424283-b8f17842773f?w=800&q=80",
    risk_score: 0.61,
    uncertainty: 0.38,
    min_price: 70000,
    max_price: 130000,
    routing_reason: "uncertainty_high",
    reasoning:
      "El artículo es una réplica de airsoft declarada explícitamente como no-arma. En Argentina el airsoft es legal y regulado, sin embargo las réplicas de armas de fuego reales requieren marcación obligatoria (color naranja en caño) según disposición 72/2015. La descripción no menciona si cumple con este requisito. La frase 'embalaje discreto' genera señal adicional de ambigüedad. Se deriva a revisión humana.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_citations: [
      {
        policy_id: "POL-013",
        policy_title: "Armas y réplicas",
        snippet: "Las réplicas de armas requieren marcación de seguridad (punta naranja). Su venta está condicionada al cumplimiento de la disposición 72/2015.",
        reason: "Réplica de arma sin mención de marcación",
        relevance_score: 0.82,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.45 },
      { factor: "visual_dissonance", weight: 0.10 },
      { factor: "price_anomaly", weight: 0.06 },
    ],
    features: {
      primary_object: "Réplica de pistola (airsoft)",
      object_category: "Deportes / Airsoft",
      objects_detected: ["réplica de pistola", "cargador plástico"],
      text_in_image: [],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: null,
      fraud_signals: ["ambiguous_weapon_replica"],
      confidence: 0.67,
    },
    created_at: minutesAgo(30),
    last_update: minutesAgo(25),
    trace: buildTrace("job-review-001", "Human Review", 0.61),
  },

  {
    id: "job-review-002",
    thread_id: "job-review-002",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Cuero Exportación – Cuero Bovino Curtido Vegetal 50 pieles",
    description:
      "Lote de 50 pieles de cuero bovino curtido vegetal, calidad exportación. Procedencia Córdoba. Certificado SENASA y IGTF. Apto para mercado europeo (REACH compliance). Precio FOB Buenos Aires. Solo compradores con CUIT activo en categoría exportación.",
    price: 1200000,
    image_url: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    risk_score: 0.52,
    uncertainty: 0.42,
    min_price: 900000,
    max_price: 1600000,
    routing_reason: "uncertainty_high",
    reasoning:
      "Publicación B2B para exportación de cuero con documentación SENASA declarada. El precio por lote ($1.200.000 ARS) está dentro del rango para 50 pieles de calidad exportación. Sin embargo: el volumen de la transacción es alto, requiere verificación de CUIT del vendedor en categoría exportación, y la mención de 'precio FOB' sugiere una transacción que puede requerir documentación aduanera adicional. Incertidumbre del modelo: 42%. Se deriva a revisión humana para validación de documentación.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-020",
        policy_title: "Comercio B2B y exportaciones",
        snippet: "Las transacciones B2B de alto valor con destino exportación requieren verificación documental adicional por parte del equipo de compliance.",
        reason: "Transacción de alto valor para exportación",
        relevance_score: 0.74,
      },
    ],
    risk_breakdown: [
      { factor: "price_anomaly", weight: 0.25 },
      { factor: "policy_match", weight: 0.20 },
      { factor: "visual_dissonance", weight: 0.07 },
    ],
    features: {
      primary_object: "Cuero curtido",
      object_category: "Materias primas / Exportación",
      objects_detected: ["pieles de cuero", "apiladas en galpón"],
      text_in_image: [],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo (curtido)",
      condition_issue_detected: false,
      image_quality: "Media",
      image_type: "Foto de producto",
      is_sellable: null,
      fraud_signals: [],
      confidence: 0.61,
    },
    created_at: minutesAgo(60),
    last_update: minutesAgo(55),
    trace: buildTrace("job-review-002", "Human Review", 0.52),
  },

  {
    id: "job-review-003",
    thread_id: "job-review-003",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Crema Aclarante Kojic Acid + Niacinamide 30ml – Importada USA",
    description:
      "Crema despigmentante con Kojic Acid 2% y Niacinamida 10%. Importada directamente de USA. Sin número ANMAT porque es de uso cosmético, no medicamento. Apta para piel sensible. Resultados visibles en 4 semanas.",
    price: 48000,
    image_url: "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=800&q=80",
    risk_score: 0.58,
    uncertainty: 0.41,
    min_price: 35000,
    max_price: 70000,
    routing_reason: "uncertainty_high",
    reasoning:
      "Crema con ácido kójico al 2% en zona gris regulatoria: puede ser cosméticos (ANMAT Disposición 155/1998) o dermatológico (requiere receta). La descripción 'despigmentante' y la concentración 2% de Kojic acid la acercan a la categoría de producto con efecto terapéutico. La ausencia de número de inscripción ANMAT es declarada pero justificada como cosmético. Incertidumbre del modelo: 41%. Se requiere revisión humana para clasificación regulatoria.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: true,
    },
    policy_citations: [
      {
        policy_id: "POL-015",
        policy_title: "Suplementos dietarios y productos de salud",
        snippet: "Los cosméticos con ingredientes activos en concentraciones que generan efectos terapéuticos pueden requerir inscripción ANMAT como producto de uso médico.",
        reason: "Concentración de ácido kójico en zona gris",
        relevance_score: 0.79,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.42 },
      { factor: "price_anomaly", weight: 0.10 },
      { factor: "visual_dissonance", weight: 0.06 },
    ],
    features: {
      primary_object: "Crema cosmética",
      object_category: "Belleza / Dermocosméticos",
      objects_detected: ["frasco de crema", "packaging minimalista"],
      text_in_image: ["KOJIC ACID", "NIACINAMIDE"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: null,
      fraud_signals: ["regulatory_gray_area"],
      confidence: 0.63,
    },
    created_at: minutesAgo(20),
    last_update: minutesAgo(15),
    trace: buildTrace("job-review-003", "Human Review", 0.58),
  },

  {
    id: "job-review-004",
    thread_id: "job-review-004",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Set Navajas Profesionales Chef's Knife – Acero Alemán 5 piezas",
    description:
      "Set de 5 navajas profesionales de cocina, acero inoxidable alemán. Incluye: chef 8\", pan 8\", filetero 7\", santoku 7\", pelador 3.5\". Soporte magnético incluido. Uso exclusivo culinario. Exportación certificada NSF. Precio mayorista.",
    price: 180000,
    image_url: "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=800&q=80",
    risk_score: 0.44,
    uncertainty: 0.35,
    min_price: 140000,
    max_price: 250000,
    routing_reason: "uncertainty_medium",
    reasoning:
      "Set de cuchillos de cocina profesionales con certificación NSF (alimentaria). La descripción es específicamente culinaria y el precio está dentro del rango para el segmento profesional. El modelo tiene incertidumbre moderada (35%) porque los cuchillos en general pueden generar falsos positivos de 'objeto peligroso'. El contexto culinario y la certificación NSF son indicadores positivos, pero se prefiere validación humana para sets de alto valor.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-013",
        policy_title: "Armas, cuchillos y elementos peligrosos",
        snippet: "Los cuchillos de uso culinario con certificación de uso alimentario y descripción exclusivamente gastronómica están permitidos.",
        reason: "Set de cocina con certificación NSF",
        relevance_score: 0.71,
      },
    ],
    risk_breakdown: [
      { factor: "policy_match", weight: 0.28 },
      { factor: "visual_dissonance", weight: 0.10 },
      { factor: "price_anomaly", weight: 0.06 },
    ],
    features: {
      primary_object: "Set de cuchillos de cocina",
      object_category: "Gastronomía / Exportación",
      objects_detected: ["cuchillos de cocina", "soporte magnético", "caja"],
      text_in_image: ["NSF", "CHEF"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Nuevo",
      condition_issue_detected: false,
      image_quality: "Alta",
      image_type: "Foto de producto",
      is_sellable: null,
      fraud_signals: [],
      confidence: 0.72,
    },
    created_at: minutesAgo(10),
    last_update: minutesAgo(5),
    trace: buildTrace("job-review-004", "Human Review", 0.44),
  },

  {
    id: "job-review-005",
    thread_id: "job-review-005",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Console Sony PS5 Digital Edition + 2 Joysticks – Usado",
    description:
      "PlayStation 5 Digital Edition, color blanco. Usado, buen estado. 800hs de uso aproximado. Incluye 2 DualSense blancos y cable HDMI 2.1. No tiene caja original. Precio negociable para pago en efectivo. Consultar por privado.",
    price: 1050000,
    image_url: "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=800&q=80",
    risk_score: 0.47,
    uncertainty: 0.39,
    min_price: 900000,
    max_price: 1350000,
    routing_reason: "uncertainty_medium",
    reasoning:
      "PS5 usado en buen estado con precio razonable ($1.050.000 ARS, dentro del rango para el modelo digital usado). La frase 'consultar por privado' puede ser un vector de contacto externo aunque no incluye datos explícitos. El descuento por efectivo es una práctica habitual en Argentina pero genera leve señal. Sin datos de contacto explícitos. Incertidumbre del modelo: 39%. Se pide revisión para confirmar ausencia de intención de contacto externo.",
    signals: {
      visual_dissonance: false,
      contact_info_detected: false,
      price_anomaly: false,
      condition_issue: true,
      policy_match: false,
    },
    policy_citations: [
      {
        policy_id: "POL-003",
        policy_title: "Dispositivos electrónicos de segunda mano",
        snippet: "Los productos usados sin caja original requieren descripción honesta del estado y fotos reales del artículo.",
        reason: "PS5 usado sin caja original",
        relevance_score: 0.76,
      },
    ],
    risk_breakdown: [
      { factor: "condition_issue", weight: 0.20 },
      { factor: "price_anomaly", weight: 0.15 },
      { factor: "policy_match", weight: 0.12 },
    ],
    features: {
      primary_object: "Consola de videojuegos",
      object_category: "Electrónica / Gaming",
      objects_detected: ["consola PS5", "joysticks DualSense", "cables"],
      text_in_image: ["PlayStation", "PS5"],
      contact_info_detected: false,
      visual_dissonance: false,
      product_condition: "Usado – buen estado",
      condition_issue_detected: true,
      image_quality: "Media",
      image_type: "Foto real del producto",
      is_sellable: null,
      fraud_signals: ["implicit_external_contact_hint"],
      confidence: 0.68,
    },
    created_at: minutesAgo(5),
    last_update: minutesAgo(2),
    trace: buildTrace("job-review-005", "Human Review", 0.47),
  },
];

// ─── JOBS FOR LIVE FEED SIMULATION (nuevos que "llegan" durante la demo) ──────
export const MOCK_INCOMING_JOBS: MockJob[] = [
  {
    id: "job-live-001",
    thread_id: "job-live-001",
    status: "PENDING_HUMAN_REVIEW",
    final_action: "Human Review",
    title: "Motosierra Stihl MS 250 – Usada – Córdoba",
    description:
      "Motosierra Stihl MS 250 usada, bar de 45cm, funciona perfectamente. Uso doméstico para poda y leña. Precio negociable. Solo retiro en Villa Allende, Córdoba.",
    price: 185000,
    image_url: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    risk_score: 0.55,
    uncertainty: 0.40,
    routing_reason: "uncertainty_medium",
    reasoning: "Herramienta de corte de alto riesgo potencial. Se deriva a revisión humana para verificar contexto de uso declarado.",
    signals: { visual_dissonance: false, contact_info_detected: false, price_anomaly: false, policy_match: true },
    features: { primary_object: "Motosierra", object_category: "Herramientas", condition_issue_detected: false, is_sellable: null, confidence: 0.65, fraud_signals: [] },
    created_at: new Date().toISOString(),
    last_update: new Date().toISOString(),
    trace: buildTrace("job-live-001", "Human Review", 0.55),
  },
  {
    id: "job-live-002",
    thread_id: "job-live-002",
    status: "APPROVE",
    final_action: "Approve",
    title: "Teclado Mecánico Redragon K530 Compact TKL – RGB – Nuevo",
    description: "Teclado mecánico Redragon K530, switches azules, diseño TKL (sin numpad), iluminación RGB por tecla, conexión USB-C. Nuevo en caja. Ideal para gaming y programación.",
    price: 88000,
    image_url: "https://images.unsplash.com/photo-1561112078-7d24e04c3407?w=800&q=80",
    risk_score: 0.07,
    uncertainty: 0.05,
    routing_reason: "auto_approved",
    reasoning: "Teclado mecánico estándar sin señales de riesgo. Precio dentro del rango de mercado.",
    signals: { visual_dissonance: false, contact_info_detected: false, price_anomaly: false, policy_match: false },
    features: { primary_object: "Teclado mecánico", object_category: "Periféricos", condition_issue_detected: false, is_sellable: true, confidence: 0.97, fraud_signals: [] },
    created_at: new Date().toISOString(),
    last_update: new Date().toISOString(),
    trace: buildTrace("job-live-002", "Approve", 0.07),
  },
  {
    id: "job-live-003",
    thread_id: "job-live-003",
    status: "BLOCK",
    final_action: "Block",
    title: "iPhone 16 Pro Max 512GB – Nuevo – $95.000 ARS",
    description: "iPhone 16 Pro Max, nuevo sellado, 512GB. Precio irresistible por necesidad de efectivo urgente. Igual a precio de costo. Entrego en mano CABA.",
    price: 95000,
    image_url: "/mock/iphone15pro.png",
    risk_score: 0.96,
    uncertainty: 0.03,
    routing_reason: "auto_blocked",
    reasoning: "Precio 95% por debajo del valor de mercado ($1.800.000–$2.200.000 ARS). Patrón textbook de fraude electrónico.",
    signals: { visual_dissonance: false, contact_info_detected: false, price_anomaly: true, policy_match: true },
    policy_violations: [{ policy_id: "POL-005", factor: "price_anomaly", explanation: "Precio 95% inferior al mínimo de mercado para iPhone 16 Pro Max nuevo." }],
    features: { primary_object: "Smartphone", object_category: "Electrónica", condition_issue_detected: false, is_sellable: false, confidence: 0.98, fraud_signals: ["price_manipulation", "urgent_sale_fraud"] },
    created_at: new Date().toISOString(),
    last_update: new Date().toISOString(),
    trace: buildTrace("job-live-003", "Block", 0.96),
  },
  {
    id: "job-live-004",
    thread_id: "job-live-004",
    status: "APPROVE",
    final_action: "Approve",
    title: "Mate de Calabaza Curado + Bombilla Alpaca – Set de Exportación",
    description: "Set de mate artesanal: calabaza curada con aro de alpaca y bombilla de alpaca 18cm. Certificado para exportación a Europa. Packaging de regalo. Precio por lote mínimo de 10 unidades.",
    price: 75000,
    image_url: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    risk_score: 0.08,
    uncertainty: 0.06,
    routing_reason: "auto_approved",
    reasoning: "Artesanía argentina de exportación sin señales de riesgo. Producto cultural legítimo.",
    signals: { visual_dissonance: false, contact_info_detected: false, price_anomaly: false, policy_match: false },
    features: { primary_object: "Mate artesanal", object_category: "Artesanías / Exportación", condition_issue_detected: false, is_sellable: true, confidence: 0.95, fraud_signals: [] },
    created_at: new Date().toISOString(),
    last_update: new Date().toISOString(),
    trace: buildTrace("job-live-004", "Approve", 0.08),
  },
];

// ─── HELPER EXPORTS ───────────────────────────────────────────────────────────

/** Convert a MockJob to AnalysisResult format (for page.tsx result view) */
export function mockJobToAnalysisResult(job: MockJob): AnalysisResult {
  return {
    risk_score: job.risk_score,
    final_action: job.final_action,
    reasoning: job.reasoning,
    features: job.features as AnalysisResult["features"],
    signals: job.signals,
    policy_citations: job.policy_citations,
    risk_breakdown: job.risk_breakdown,
    policy_violations: job.policy_violations,
    uncertainty: job.uncertainty,
    status: job.status,
  };
}

/** Return a random Approve/Block/Human Review result for the client-side submission mock */
export function getRandomMockResult(): AnalysisResult {
  const pool = MOCK_JOBS.filter((j) => j.final_action !== "Human Review");
  const job = pool[Math.floor(Math.random() * pool.length)];
  return mockJobToAnalysisResult(job);
}
