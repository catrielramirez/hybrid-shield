# 🚀 Pasos para Configurar y Desplegar en Vercel (Modo Mock)

## 📋 Paso 1: Acceder al Dashboard de Vercel

1. Ve a https://vercel.com/dashboard
2. Selecciona tu proyecto (probablemente se llama "ecommerce-police-portfolio" o "hybrid-shield")
3. Haz clic en **"Settings"** en la barra superior

---

## 🔐 Paso 2: Configurar Variables de Entorno

1. En el menú lateral, haz clic en **"Environment Variables"**

2. **OPCIÓN A: Borrar todas las variables existentes y agregar estas nuevas:**

   | Nombre | Valor | Environment |
   |--------|-------|-------------|
   | `NEXT_PUBLIC_DATA_SOURCE` | `mock` | Production |
   | `NEXT_PUBLIC_STORAGE_STRATEGY` | `mock` | Production |
   | `NEXT_PUBLIC_API_URL` | `https://tu-dominio.vercel.app` | Production |
   | `NEXT_PUBLIC_APP_URL` | `https://tu-dominio.vercel.app` | Production |
   | `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `mock-project` | Production |
   | `NEXT_PUBLIC_FIREBASE_API_KEY` | `mock-key` | Production |
   | `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `mock-domain.firebaseapp.com` | Production |
   | `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | `mock-bucket.appspot.com` | Production |
   | `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | `123456789` | Production |
   | `NEXT_PUBLIC_FIREBASE_APP_ID` | `1:123456789:web:abcdef123456` | Production |

   **Importante**: Reemplaza `https://tu-dominio.vercel.app` con tu URL real de Vercel

3. **OPCIÓN B: Usar el script de importación (más rápido)**

   Copia este bloque de texto completo y pégalo en la opción de importación masiva:

   ```
   NEXT_PUBLIC_DATA_SOURCE=mock
   NEXT_PUBLIC_STORAGE_STRATEGY=mock
   NEXT_PUBLIC_API_URL=https://tu-dominio.vercel.app
   NEXT_PUBLIC_APP_URL=https://tu-dominio.vercel.app
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=mock-project
   NEXT_PUBLIC_FIREBASE_API_KEY=mock-key
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=mock-domain.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=mock-bucket.appspot.com
   NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
   NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abcdef123456
   ```

4. Haz clic en **"Save"**

---

## 🔄 Paso 3: Forzar Redespliegue

Después de cambiar las variables de entorno:

1. Ve a la pestaña **"Deployments"**
2. Encuentra el último despliegue (el commit 3b9a951)
3. Haz clic en los tres puntos (**...**) al lado del despliegue
4. Selecciona **"Redeploy"** → **"Redeploy with existing build cache cleared"**

**Alternativamente**, puedes esperar el auto-despliegue si Vercel ya detectó el push de GitHub.

---

## ✅ Paso 4: Verificar el Despliegue

1. Una vez que el despliegue termine (verás un ✅ verde), haz clic en **"Visit"**
2. Abre las DevTools de tu navegador (F12)
3. Ve a la pestaña **Console**
4. Sube una imagen o completa el formulario
5. **Verifica que veas los mensajes de los estados con delays de 2-3 segundos cada uno:**
   - "Iniciando análisis de riesgo..." (2.1s)
   - "Extrayendo características visuales..." (2.7s)
   - "Consultando base de conocimientos (RAG)..." (2.3s)
   - "Evaluando políticas de e-commerce..." (2.5s)

---

## 🎬 Paso 5: ¡Grabar tu Demo!

Una vez verificado que todo funciona:

1. Abre OBS Studio o tu software de grabación preferido
2. Navega a tu aplicación en Vercel
3. Realiza el flujo completo:
   - Subir una imagen
   - Observar los estados progresivos (ahora con delays realistas)
   - Ver el resultado final
4. **¡Graba tu demo!** 🎥

---

## 🔄 Para Volver al Modo Production (Después de la Demo)

Cuando quieras volver a usar el backend real:

1. Ve a **Settings** → **Environment Variables** en Vercel
2. Cambia solo estas 2 variables:
   - `NEXT_PUBLIC_DATA_SOURCE` → `production` (o bórrala completamente)
   - `NEXT_PUBLIC_STORAGE_STRATEGY` → `signed_url`
3. Redespliega

---

## 🐛 Troubleshooting

### "Los estados siguen cambiando muy rápido"

Posibles causas:
- Las variables de entorno no se guardaron correctamente
- El redespliegue usó el cache (redespliega sin cache)
- Estás viendo una versión cacheada (Ctrl + F5 para forzar recarga)

### "No veo los datos mock"

Verifica en la consola del navegador que `NEXT_PUBLIC_DATA_SOURCE` esté seteado a `mock`:

```javascript
console.log(process.env.NEXT_PUBLIC_DATA_SOURCE);
// Debería mostrar: "mock"
```

### "Firebase está intentando conectar"

Es normal. El código inicializa Firebase pero no lo usa en modo mock. Ignora los warnings de Firebase en la consola.

---

## 📞 Próximos Pasos

1. ⏳ Configura las variables de entorno (5 minutos)
2. 🔄 Redespliega (2-3 minutos)
3. ✅ Verifica (1 minuto)
4. 🎬 Graba tu demo (tiempo variable)
5. 🎉 ¡Comparte tu video!

---

**¿Necesitas ayuda?** Avísame cuando hayas completado cada paso.
