# 🚀 Guía Completa: Configurar Vercel en Modo Mock

## 📋 Resumen
Esta guía te ayudará a configurar tu proyecto en Vercel para usar datos mock (sin backend real) para tu demo en video.

---

## ✅ Paso 1: Acceder al Dashboard de Vercel

1. Ve a https://vercel.com/dashboard
2. Busca tu proyecto (probablemente se llama similar a "ecommerce-police-portfolio" o "hybrid-shield")
3. Haz clic en el proyecto para abrirlo

---

## 🔧 Paso 2: Configurar Variables de Entorno

### 2.1 Ir a la sección de configuración

1. En la barra superior del proyecto, haz clic en **"Settings"**
2. En el menú lateral izquierdo, haz clic en **"Environment Variables"**

### 2.2 Limpiar variables existentes (Importante)

**ANTES de agregar las nuevas variables:**

Si hay variables existentes relacionadas con Firebase o datos:
- Haz clic en los tres puntos (**...**) al lado de cada variable
- Selecciona **"Delete"**
- Confirma la eliminación

**Variables que debes eliminar si existen:**
- `NEXT_PUBLIC_DATA_SOURCE` (cualquier valor anterior)
- `NEXT_PUBLIC_STORAGE_STRATEGY` (cualquier valor anterior)
- Variables de Firebase reales (si las hay)

### 2.3 Agregar las nuevas variables

**Copia y pega estas 10 variables una por una:**

| Variable Name | Value | Environment |
|---------------|-------|-------------|
| `NEXT_PUBLIC_DATA_SOURCE` | `mock` | ☑️ Production |
| `NEXT_PUBLIC_STORAGE_STRATEGY` | `mock` | ☑️ Production |
| `NEXT_PUBLIC_API_URL` | `https://TU-DOMINIO.vercel.app` | ☑️ Production |
| `NEXT_PUBLIC_APP_URL` | `https://TU-DOMINIO.vercel.app` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | `mock-project` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | `mock-key` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | `mock-domain.firebaseapp.com` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | `mock-bucket.appspot.com` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | `123456789` | ☑️ Production |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | `1:123456789:web:abcdef123456` | ☑️ Production |

**⚠️ IMPORTANTE:**
- Reemplaza `TU-DOMINIO.vercel.app` con tu URL real de Vercel (ejemplo: `hybrid-shield-abc123.vercel.app`)
- Para encontrar tu dominio, ve a la pestaña **"Deployments"** y copia la URL del último despliegue

### 2.4 Formato de importación masiva (Más rápido)

Alternativamente, puedes usar la opción de importación masiva:

1. En la página de Environment Variables, busca el botón **"Add Variable"**
2. Algunos dashboards tienen una opción **"Bulk Add"** o **"Import"**
3. Si existe, copia y pega este bloque completo:

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

4. Recuerda reemplazar `TU-DOMINIO.vercel.app` con tu URL real

---

## 🔄 Paso 3: Redesplegar el Proyecto

**CRÍTICO:** Las variables de entorno solo se aplican en nuevos despliegues.

### 3.1 Opción A: Redespliegue Manual (Recomendado)

1. Ve a la pestaña **"Deployments"**
2. Encuentra el despliegue más reciente (el primero de la lista)
3. Haz clic en los tres puntos (**...**) al lado derecho
4. Selecciona **"Redeploy"**
5. **MUY IMPORTANTE:** Marca la opción **"Use existing Build Cache"** como **DESMARCADA** o selecciona **"Rebuild"**
   - Esto asegura que se use el código más reciente con los nuevos delays
6. Haz clic en **"Redeploy"**
7. Espera 2-3 minutos a que termine el despliegue
8. Verás un ✅ verde cuando esté listo

### 3.2 Opción B: Push a Git (Alternativa)

Si prefieres, puedes hacer un push vacío para forzar un redespliegue:

```bash
git commit --allow-empty -m "chore: trigger vercel redeploy with mock env"
git push origin main
```

Vercel detectará el push automáticamente y desplegará.

---

## ✅ Paso 4: Verificar el Despliegue

### 4.1 Acceder a tu aplicación

1. Una vez que el despliegue termine (✅ verde), haz clic en **"Visit"** o en la URL del despliegue
2. Esto abrirá tu aplicación en una nueva pestaña

### 4.2 Verificación técnica (Consola del navegador)

1. Con la aplicación abierta, presiona **F12** para abrir las DevTools
2. Ve a la pestaña **"Console"**
3. Escribe y ejecuta:
   ```javascript
   console.log(process.env.NEXT_PUBLIC_DATA_SOURCE);
   ```
4. Debería mostrar: `"mock"` ✅
5. Si muestra `undefined` o cualquier otra cosa, las variables no se cargaron correctamente

### 4.3 Verificación visual

**En la página principal (`/`):**
1. Completa el formulario con cualquier dato
2. Sube una imagen
3. Haz clic en "Iniciar Evaluación"
4. **Deberías ver:**
   - "Iniciando análisis de riesgo..." (2.1 segundos)
   - "Extrayendo características visuales..." (2.7 segundos)
   - "Consultando base de conocimientos (RAG)..." (2.3 segundos)
   - "Evaluando políticas de e-commerce..." (2.5 segundos)
5. Luego verás un resultado mock (Approve, Block, o Human Review)

**En la página HITL (`/hitl`):**
1. Ve a `https://tu-dominio.vercel.app/hitl`
2. **Deberías ver:**
   - **5 trabajos en "Pendientes"** (con status "Human Review")
   - **17 trabajos en "Historial"** (8 Approve + 7 Block + 2 otros)
   - Todos con títulos, descripciones y precios correctos

### 4.4 Si algo no funciona

**Síntoma:** No ves datos mock / La página está vacía
- **Causa:** Las variables no se cargaron correctamente
- **Solución:** 
  1. Vuelve a Settings → Environment Variables
  2. Verifica que `NEXT_PUBLIC_DATA_SOURCE=mock` exista
  3. Redespliega nuevamente **sin cache**

**Síntoma:** Los estados cambian muy rápido (menos de 2 segundos)
- **Causa:** Vercel está usando el build anterior (con delays de 1.4s)
- **Solución:**
  1. Ve a Deployments
  2. Redespliega marcando **"Clear cache"** o **"Rebuild"**

**Síntoma:** Errores de Firebase en la consola
- **Causa:** Es normal, Firebase intenta inicializarse pero no se usa en modo mock
- **Solución:** Ignora esos warnings, no afectan la funcionalidad

---

## 🎬 Paso 5: Grabar tu Demo

Una vez verificado que todo funciona:

1. **Prepara tu software de grabación** (OBS Studio, QuickTime, etc.)
2. **Abre tu aplicación en Vercel** (usa la URL de producción)
3. **Graba el flujo completo:**
   - Subir una imagen de producto
   - Completar formulario
   - Ver los estados progresivos (ahora realistas con delays 2-3s)
   - Ver el resultado final
   - Navegar a `/hitl` y mostrar la lista de pendientes y historial
4. **Edita y publica tu video** 🎥

---

## 🔄 Para Volver al Modo Production (Después de la Demo)

Cuando quieras usar el backend real de nuevo:

1. Ve a **Settings** → **Environment Variables** en Vercel
2. Cambia solo estas 2 variables:
   - `NEXT_PUBLIC_DATA_SOURCE` → bórrala o cámbiala a `production`
   - `NEXT_PUBLIC_STORAGE_STRATEGY` → cámbiala a `signed_url`
3. Agrega las variables reales de Firebase (si es necesario)
4. Redespliega

---

## 📞 Checklist Final

Antes de grabar, verifica:

- [ ] Variables de entorno configuradas en Vercel (10 variables)
- [ ] `NEXT_PUBLIC_DATA_SOURCE=mock` está presente
- [ ] URL de Vercel actualizada en `NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_APP_URL`
- [ ] Redespliegue completado sin cache
- [ ] Verificado en consola: `process.env.NEXT_PUBLIC_DATA_SOURCE` = "mock"
- [ ] Página principal muestra delays de 2-3 segundos entre estados
- [ ] Página `/hitl` muestra 5 pendientes y 17 históricos
- [ ] Todos los productos tienen título, descripción y precio
- [ ] Listo para grabar 🎬

---

## 🆘 ¿Necesitas Ayuda?

Si algo no funciona después de seguir estos pasos, verifica:

1. **¿Las 10 variables están en Production?** (no en Preview o Development)
2. **¿Hiciste el redespliegue sin cache?**
3. **¿Reemplazaste TU-DOMINIO.vercel.app con tu URL real?**
4. **¿La consola muestra `mock` al revisar la variable?**

Si todo lo anterior está correcto y sigue sin funcionar, avísame con capturas de pantalla de:
- Las variables de entorno en Vercel
- La consola del navegador
- Lo que ves en la aplicación

---

**¡Listo para grabar tu demo profesional!** 🎥✨
