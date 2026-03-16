# SubnAnalysis

Biblioteca local de subtítulos de YouTube — 100% standalone, sin servidor, sin instalación.

## ¿Qué es?

Un único fichero `index.html` que carga un `verbatube.json` generado por [VerbaSant](https://github.com/EduardoAbdulMalik/VerbaSant) y permite:

- **Explorar** todos los vídeos indexados por canal, idioma y búsqueda full-text
- **Leer** las transcripciones completas con búsqueda en el texto del vídeo activo
- **Consultar con IA** (Anthropic Claude, OpenAI, Gemini) usando el corpus como contexto
- **Exportar** transcripciones y respuestas IA a Markdown o PDF

## Uso

1. Genera tu `verbatube.json` con VerbaSant (`python indexer.py`)
2. Abre `index.html` en tu navegador (doble clic)
3. Pulsa **"Abrir verbatube.json"** o arrastra el fichero a la zona indicada
4. Listo — no necesita Python, Node, ni ningún servidor

## Compatibilidad

| Browser | Cargar JSON | Llamadas LLM |
|---|---|---|
| Chrome / Edge | ✅ File System Access API | ✅ |
| Firefox | ✅ Drag & drop | ✅ |
| Safari | ✅ Drag & drop | ✅ |

## Proveedores LLM soportados

- **Anthropic Claude** — requiere API key `sk-ant-…`
- **OpenAI** — requiere API key `sk-…`
- **Google Gemini** — requiere API key `AIza…`

Las claves se usan solo en la sesión activa y no se almacenan en ningún sitio.

## Sobre los timestamps

Si el `verbatube.json` incluye el campo `cues` (versión futura del indexer), los subtítulos
se mostrarán con timestamps enlazados a YouTube. En la versión actual del indexer, se muestra
el `full_text` formateado en párrafos sin timestamps.

## Relación con VerbaSant

SubnAnalysis es el **viewer standalone** de VerbaSant. VerbaSant (con su `server.py` e `indexer.py`)
hace la ingesta y generación del JSON. SubnAnalysis consume ese JSON sin dependencias.

## Licencia

MIT
