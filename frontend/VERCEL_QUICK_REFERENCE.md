# 🚀 Referencia Rápida: Variables de Entorno para Vercel (Modo Mock)

## ✅ Variables a Configurar en Vercel

**Total: 10 variables**

Copia y pega estas variables en **Settings → Environment Variables** de tu proyecto en Vercel:

```
NEXT_PUBLIC_DATA_SOURCE=mock
NEXT_PUBLIC_STORAGE_STRATEGY=mock
NEXT_PUBLIC_API_URL=https://TU-DOMINIO.vercel.app
NEXT_PUBLIC_APP_URL=https://TU-DOMINIO.vercel.app
NEXT_PUBLIC_FIREBASE_PROJECT_ID=mock-project
NEXT_PUBLIC_FIREBASE_API_KEY=mock-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=mock-domain.firebaseapp.com
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=mock-bucket.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

**⚠️ IMPORTANTE:**
- Reemplaza `TU-DOMINIO.vercel.app` con tu URL real de Vercel
- Selecciona **"Production"** en el campo Environment para cada variable
- Después de agregar todas, haz **Redeploy sin cache**

---

## 🔍 Cómo Encontrar tu Dominio de Vercel

1. Ve a tu proyecto en Vercel Dashboard
2. Ve a la pestaña **"Deployments"**
3. Copia la URL del último despliegue (ejemplo: `hybrid-shield-abc123.vercel.app`)
4. Usa esa URL para reemplazar `TU-DOMINIO.vercel.app` en las variables de arriba

---

## ✅ Verificación Rápida

**En la consola del navegador (F12):**
```javascript
console.log(process.env.NEXT_PUBLIC_DATA_SOURCE);
// Debe mostrar: "mock"
```

**Visualmente:**
- Página principal: Delays de 2-3 segundos entre estados
- Página `/hitl`: 5 pendientes + 17 históricos con todos los datos completos

---

## 🔄 Pasos de Despliegue

1. ✅ Configurar las 10 variables en Vercel
2. ✅ Reemplazar `TU-DOMINIO.vercel.app` con tu URL real
3. ✅ Ir a Deployments → Redeploy → Sin cache
4. ✅ Esperar 2-3 minutos
5. ✅ Verificar en la consola que aparece "mock"
6. ✅ ¡Grabar tu demo!

---

**Lee `VERCEL_MOCK_SETUP_GUIDE.md` para la guía completa paso a paso.**
