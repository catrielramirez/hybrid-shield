# Instrucciones para Despliegue en Vercel - Modo Mock

## ✅ Cambio Realizado

Se modificó el archivo `app/page.tsx` para que los estados del sistema en modo mock tengan delays más realistas:

- **Antes**: Todos los estados duraban 1.4 segundos (uniforme)
- **Ahora**: Cada estado tiene un delay variable:
  - "Iniciando análisis de riesgo..." → 2.1s
  - "Extrayendo características visuales..." → 2.7s
  - "Consultando base de conocimientos (RAG)..." → 2.3s
  - "Evaluando políticas de e-commerce..." → 2.5s

Esto da una sensación más realista para la demo en video.

---

## 🚀 Pasos para Despliegue en Vercel (Modo Mock)

### 1. Configurar Variables de Entorno en Vercel

Accede al dashboard de tu proyecto en Vercel y configura las siguientes variables de entorno para el **Production Environment**:

```env
NEXT_PUBLIC_DATA_SOURCE=mock
NEXT_PUBLIC_STORAGE_STRATEGY=mock
NEXT_PUBLIC_API_URL=https://tu-dominio-vercel.vercel.app
NEXT_PUBLIC_APP_URL=https://tu-dominio-vercel.vercel.app

# Firebase config (requeridos por la inicialización pero no usados en mock mode)
NEXT_PUBLIC_FIREBASE_PROJECT_ID=mock-project
NEXT_PUBLIC_FIREBASE_API_KEY=mock-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=mock-domain.firebaseapp.com
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=mock-bucket.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

**Importante**: Reemplaza `https://tu-dominio-vercel.vercel.app` con la URL real de tu despliegue en Vercel.

### 2. Desplegar con Vercel CLI

Desde el directorio `frontend`, ejecuta:

```bash
# Opción 1: Despliegue a producción directo
vercel --prod

# Opción 2: Preview primero, luego promueve a producción
vercel
# luego
vercel --prod
```

### 3. Desplegar desde Git (Alternativa)

Si prefieres usar el workflow de Git:

```bash
# Hacer commit de los cambios
git add app/page.tsx
git commit -m "feat: delays variables y realistas para estados del sistema en modo mock"

# Push a tu rama principal
git push origin main
```

Vercel detectará el push automáticamente y desplegará con las variables de entorno configuradas en el dashboard.

---

## 🎬 Verificación Post-Despliegue

1. Accede a tu URL de Vercel
2. Abre las DevTools (F12) y ve a la pestaña Network
3. Sube una imagen o completa un formulario
4. Observa que los estados cambien con delays entre 2-3 segundos cada uno
5. **Graba tu demo** 🎥

---

## 📋 Checklist

- [ ] Variables de entorno configuradas en Vercel Dashboard
- [ ] Código modificado en `app/page.tsx`
- [ ] Build exitoso localmente
- [ ] Despliegue a Vercel completado
- [ ] Verificación de delays en producción
- [ ] Demo grabada

---

## 🔄 Para Volver al Modo Production

Cuando quieras volver al modo de producción real, solo cambia las variables de entorno en Vercel:

```env
NEXT_PUBLIC_DATA_SOURCE=production
NEXT_PUBLIC_STORAGE_STRATEGY=signed_url
NEXT_PUBLIC_API_URL=https://hybrid-shield-backend-679252770153.us-central1.run.app
# ... resto de variables de Firebase reales
```

Y redespliega.
