# SubnAnalysis

Biblioteca local de subtítulos de YouTube — standalone HTML + ingesta automática vía GitHub Actions.  
Sin servidor. Sin instalación. Sin Python local.

## ¿Qué es?

Un único fichero `index.html` que funciona como biblioteca completa de transcripciones de YouTube.  
La ingesta (descarga de subtítulos) se ejecuta en la nube via **GitHub Actions**, usando `yt-dlp`.  
El resultado es un `verbatube.json` con todo el texto indexado que el viewer carga directamente.

---

## Arquitectura

```
Usuario (browser)
   │
   ├── Abre GitHub Pages URL  ──→  index.html carga verbatube.json automáticamente
   │
   └── Tab "Descargar"
         │
         ├── Introduce URL de YouTube + GitHub Token
         │
         └── GitHub API dispatch ──→ GitHub Actions runner
                                         │
                                         ├── yt-dlp descarga VTTs (solo texto, no vídeo)
                                         ├── indexer.py construye verbatube.json
                                         └── git commit + push del JSON al repo
                                               │
                                               └── Usuario recarga → biblioteca actualizada
```

**Los VTTs son temporales** — se descargan, se procesan y el JSON resultante contiene todo el texto.  
Una vez generado el JSON, los VTTs no son necesarios para el uso normal.

---

## Estructura del repositorio

```
SubnAnalysis/
├── index.html                        # App completa (viewer + descarga + IA)
├── indexer.py                        # Parser VTT → verbatube.json (corre en Actions)
├── verbatube.json                    # Índice generado automáticamente
├── .github/
│   └── workflows/
│       └── ingest.yml                # Workflow de GitHub Actions
└── README.md
```

---

## Formato del índice (verbatube.json)

```json
{
  "version": "1.1",
  "generated_at": "2026-03-16T...",
  "total_videos": 42,
  "channels": [
    { "name": "Canal Ejemplo", "count": 42 }
  ],
  "videos": [
    {
      "video_id": "dQw4w9WgXcQ",
      "title": "Título del vídeo",
      "channel": "Canal Ejemplo",
      "published": "20240115",
      "duration_s": 3600,
      "duration_fmt": "1:00:00",
      "thumbnail": "https://i.ytimg.com/...",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "language": "es",
      "cues": [
        { "start": 12.3, "end": 15.1, "text": "texto del cue con timestamp" }
      ],
      "full_text": "transcripción completa limpia sin duplicados...",
      "text_preview": "primeros 280 caracteres..."
    }
  ]
}
```

El campo `cues` incluye timestamps en segundos para la vista sincronizada con YouTube.

---

## Funcionalidades del viewer

### Biblioteca
- Lista de vídeos con thumbnail, canal, fecha, duración, idioma
- Búsqueda full-text en todas las transcripciones simultáneamente
- Filtro por canal (tags clickables)
- Filtro por idioma (es / en / todos)
- Highlight de términos buscados en los snippets

### Viewer de transcripciones
- **Modo limpio** — texto agrupado en párrafos por pausas (gap > 2.5s, máx 8 líneas)
- **Modo timestamps** — cada cue enlazado a YouTube en ese segundo exacto
- Búsqueda interna con navegación entre coincidencias (Enter / Shift+Enter)
- Enlace directo "Ver en YouTube" en el header

### Exportación
- **Markdown** — con frontmatter YAML (título, canal, fecha, URL, tags)
- **PDF** — layout tipográfico con html2pdf.js

### Preguntas IA
Llamadas directas desde el browser (sin proxy) a:
- **Anthropic Claude** — `claude-sonnet-4-5`, `claude-3-5-sonnet`, `claude-3-opus`
- **OpenAI** — `gpt-4o-mini`, `gpt-4o`
- **Google Gemini** — `gemini-2.0-flash`, `gemini-1.5-flash`

Contexto automático:
- Si hay vídeo seleccionado → transcripción completa de ese vídeo
- Si no → búsqueda por relevancia (keyword scoring) entre todos los vídeos, top 5

Las claves API se usan solo en sesión — no se almacenan en disco ni en el repo.

### Descarga (tab "+ Descargar")
Dispara el workflow de GitHub Actions vía API. Muestra en tiempo real:
- Estado del dispatch
- Número y URL del run
- Polling del estado (queued → in_progress → completed)
- Aviso de recarga al terminar

---

## Setup inicial (una sola vez)

### 1. Fork o usa este repo directamente

El repo es público: `https://github.com/eduardoddddddd/SubnAnalysis`

### 2. Activa GitHub Pages

Settings → Pages → Branch: `master` → Folder: `/ (root)` → Save

URL resultante: `https://eduardoddddddd.github.io/SubnAnalysis/`

### 3. Genera un GitHub Token

https://github.com/settings/tokens → "Generate new token (classic)"  
Scope necesario: solo **`workflow`**

El token se introduce en la tab "Descargar" en cada sesión — no se almacena.

---

## Uso normal

### Descargar un canal / playlist

1. Abre la URL de GitHub Pages
2. Tab **"+ Descargar"**
3. Introduce tu GitHub Token y la URL de YouTube
4. Pulsa **"▶ Iniciar descarga"**
5. Espera ~10-25 min para canales grandes (solo descarga texto, no vídeo)
6. Recarga cuando el workflow termine → biblioteca actualizada

### Cargar un JSON externo

Botón **📂 JSON** en el topbar → abre cualquier `verbatube.json` generado por VerbaSant o SubnAnalysis.

Compatible con el JSON generado por VerbaSant v1.0 (sin campo `cues` → se muestra `full_text` sin timestamps).

---

## Compatibilidad de browsers

| Browser | Carga JSON automática (Pages) | Cargar JSON manual | Llamadas LLM |
|---|---|---|---|
| Chrome / Edge | ✅ fetch desde Pages | ✅ File System Access API | ✅ |
| Firefox | ✅ fetch desde Pages | ✅ Drag & drop / input file | ✅ |
| Safari | ✅ fetch desde Pages | ✅ input file | ✅ |
| Abierto en local (`file://`) | ⚠ Necesita botón manual | ✅ | ✅ |

---

## GitHub Actions — detalles técnicos

**Workflow:** `.github/workflows/ingest.yml`  
**Trigger:** `repository_dispatch` con `event_type: ingest`  
**Runner:** `ubuntu-latest` (2 cores, 7GB RAM, gratuito en repos públicos — minutos ilimitados)

**Pasos del workflow:**
1. Checkout del repo
2. Setup Python 3.12
3. Instala `yt-dlp` via pip
4. Restaura caché de VTTs previos (incremental)
5. `yt-dlp --skip-download --write-auto-subs --write-subs` — solo texto
6. `python indexer.py` — genera `verbatube.json` con cues y full_text
7. `git commit && git push` del JSON actualizado

**Flags de yt-dlp usados:**
- `--skip-download` — no descarga el vídeo, solo subtítulos
- `--write-auto-subs` — subtítulos ASR automáticos de YouTube
- `--write-subs` — subtítulos manuales si existen
- `--no-overwrites` — no reprocesa lo ya descargado
- `--download-archive` — registro de vídeos ya procesados (incremental)
- `--sleep-requests 1` — pausa entre peticiones para evitar rate limiting

---

## Relación con VerbaSant

| | VerbaSant | SubnAnalysis |
|---|---|---|
| Ingesta | yt-dlp local + Python | yt-dlp en GitHub Actions |
| Viewer | `viewer.html` + `server.py` | `index.html` standalone |
| JSON | `verbatube.json` | `verbatube.json` (mismo formato) |
| Requiere Python local | ✅ | ❌ |
| Requiere servidor | ✅ | ❌ |
| LLM | Via `server.py` proxy | Llamadas directas desde browser |
| Timestamps en viewer | Via fetch de .vtt | Desde campo `cues` del JSON |

Los JSON son **intercambiables** — puedes cargar el JSON de VerbaSant en SubnAnalysis y viceversa.

---

## Licencia

MIT
