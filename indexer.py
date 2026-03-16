#!/usr/bin/env python3
"""
SubnAnalysis - Indexer para GitHub Actions
Lee VTTs del directorio vtts/ y genera verbatube.json
Compatible con el formato de VerbaSant
"""
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR     = Path(__file__).parent
SUBTITLES_DIR = BASE_DIR / "vtts"
INDEX_FILE   = BASE_DIR / "verbatube.json"
PREVIEW_LEN  = 280

def parse_vtt(path):
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] {path.name}: {e}")
        return [], ""

    lines = content.split("\n")
    cues, seen = [], set()
    start = end = None
    current_lines, in_cue = [], False

    TS_RE  = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})")
    TAG_RE = re.compile(r"<[^>]+>")
    ENTITY = {"&amp;":"&","&lt;":"<","&gt;":">","&nbsp;":" ","&#39;":"'"}

    def ts(h,m,s,ms): return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
    def clean(l):
        l = TAG_RE.sub("", l)
        for k,v in ENTITY.items(): l = l.replace(k, v)
        return re.sub(r"\s+", " ", l).strip()

    def save_cue():
        if current_lines:
            t = current_lines[-1] if len(current_lines) > 1 else " ".join(current_lines)
            t = re.sub(r"\s+", " ", t).strip()
            if t and t not in seen:
                cues.append({"start": start, "end": end, "text": t})
                seen.add(t)

    for line in lines:
        m = TS_RE.match(line.rstrip())
        if m:
            if start is not None: save_cue()
            start = ts(m.group(1),m.group(2),m.group(3),m.group(4))
            end   = ts(m.group(5),m.group(6),m.group(7),m.group(8))
            current_lines = []; in_cue = True; continue
        if in_cue:
            if line.strip() == "":
                save_cue(); in_cue = False; current_lines = []; start = None
            else:
                c = clean(line.rstrip())
                if c and not re.match(r"^\d+$", c): current_lines.append(c)
    if start is not None: save_cue()

    full_text = re.sub(r"\s+", " ", " ".join(c["text"] for c in cues)).strip()
    return cues, full_text

def extract_id(path):
    stem = path.stem
    parts = stem.split("_")
    if len(parts) >= 2 and re.match(r"^\d{8}$", parts[0]):
        return parts[1] if parts[1] else "_" + parts[2]
    return stem.split(".")[0]

def fmt_duration(s):
    s = int(s); h,r = divmod(s,3600); m,sec = divmod(r,60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def load_meta(video_id, vtt_path):
    for d in [vtt_path.parent, SUBTITLES_DIR]:
        for f in d.glob(f"*{video_id}*.info.json"):
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except: pass
    # Fallback: parsear del nombre de fichero
    stem = vtt_path.stem
    parts = stem.split("_")
    meta = {"channel": vtt_path.parent.name if vtt_path.parent != SUBTITLES_DIR else "Desconocido"}
    if len(parts) >= 3 and re.match(r"^\d{8}$", parts[0]):
        meta["upload_date"] = parts[0]
        raw = "_".join(parts[2:])
        raw = re.sub(r"\.[a-z]{2}(-[a-z]+)?$", "", raw)
        meta["title"] = raw.replace("_", " ").strip()
    return meta

def build_index():
    if not SUBTITLES_DIR.exists():
        print(f"[ERROR] No existe {SUBTITLES_DIR}"); sys.exit(1)

    vtts = list(SUBTITLES_DIR.rglob("*.vtt"))
    if not vtts:
        print("[ERROR] No hay ficheros .vtt"); sys.exit(1)

    # Cargar índice existente para actualización incremental
    existing = {}
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            for v in data.get("videos", []):
                existing[v["video_id"]] = v
            print(f"[INFO] Índice previo: {len(existing)} vídeos")
        except: pass

    # Agrupar por video_id
    by_id = {}
    for vtt in vtts:
        vid = extract_id(vtt)
        if vid: by_id.setdefault(vid, []).append(vtt)

    print(f"[INFO] VTTs: {len(vtts)} de {len(by_id)} vídeos")

    videos = []; new_c = updated_c = 0

    for vid, vtts_list in sorted(by_id.items()):
        def lang_pri(p):
            s = p.stem
            if ".es" in s: return 0
            if ".en" in s: return 1
            return 2
        primary = sorted(vtts_list, key=lang_pri)[0]
        mtime = primary.stat().st_mtime

        # Incremental: saltar si no cambió
        if vid in existing and existing[vid].get("_vtt_mtime") == mtime:
            videos.append(existing[vid]); continue

        print(f"  Indexando: {vid} ({primary.name})")
        cues, full_text = parse_vtt(primary)
        if not full_text:
            print(f"    [WARN] Sin texto, omitiendo"); continue

        meta = load_meta(vid, primary)
        lang_part = primary.stem.replace(vid + ".", "")
        lang = lang_part.split("-")[0] if lang_part else "unknown"

        entry = {
            "video_id":  vid,
            "title":     meta.get("title", vid),
            "channel":   meta.get("channel", meta.get("uploader", "Desconocido")),
            "channel_id":  meta.get("channel_id", ""),
            "channel_url": meta.get("channel_url", ""),
            "published":   meta.get("upload_date", ""),
            "duration_s":  meta.get("duration", 0),
            "duration_fmt": fmt_duration(meta.get("duration", 0)),
            "thumbnail":   meta.get("thumbnail", ""),
            "url":         f"https://www.youtube.com/watch?v={vid}",
            "language":    lang,
            "languages_available": [p.stem.replace(vid+".","").split("-")[0] for p in vtts_list],
            "cues":        cues,
            "cue_count":   len(cues),
            "text_preview": full_text[:PREVIEW_LEN] + ("…" if len(full_text) > PREVIEW_LEN else ""),
            "full_text":   full_text,
            "indexed_at":  datetime.now(timezone.utc).isoformat(),
            "_vtt_mtime":  mtime,
        }
        if vid in existing: updated_c += 1
        else: new_c += 1
        videos.append(entry)

    videos.sort(key=lambda v: v.get("published","") or "", reverse=True)

    channels = {}
    for v in videos:
        ch = v["channel"]
        if ch not in channels:
            channels[ch] = {"name": ch, "channel_id": v.get("channel_id",""), "url": v.get("channel_url",""), "count": 0}
        channels[ch]["count"] += 1

    index = {
        "version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_videos": len(videos),
        "channels": list(channels.values()),
        "videos": videos
    }
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    size = INDEX_FILE.stat().st_size / 1024
    print(f"\n[DONE] {INDEX_FILE} — {len(videos)} vídeos ({size:.0f} KB)")
    print(f"  Nuevos: {new_c} | Actualizados: {updated_c} | Canales: {len(channels)}")

if __name__ == "__main__":
    build_index()
