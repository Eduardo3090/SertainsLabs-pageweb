"""
SertainsBot — agente de WhatsApp para Sertains Labs.
Se agrega al sitio Flask existente como Blueprint (no necesita otro servidor).

Todo se configura con variables de entorno en Render:
- Cambiar de IA gratis (Gemini) a pagada (OpenRouter) = cambiar LLM_BASE_URL, LLM_API_KEY y LLM_MODEL.
- Cal.com es opcional: si no hay CALCOM_API_KEY, el bot funciona sin agendar.
"""
import os
import json
import hmac
import hashlib
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from flask import Blueprint, request, abort

bot_bp = Blueprint("sertainsbot", __name__)

# ---------- Configuración ----------
WA_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WA_PHONE_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WA_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
GRAPH_VERSION = os.environ.get("GRAPH_VERSION", "v23.0")

# IA: por defecto Gemini (gratis). Para OpenRouter: LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-2.5-flash")

CAL_KEY = os.environ.get("CALCOM_API_KEY", "")
CAL_EVENT_ID = os.environ.get("CALCOM_EVENT_TYPE_ID", "")

TZ_NAME = "America/Santiago"
TZ = ZoneInfo(TZ_NAME)
DB_PATH = os.environ.get("BOT_DB_PATH", "sertainsbot.db")
MAX_HISTORIAL = 15

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sertainsbot_prompt.txt"), encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

db_lock = threading.Lock()


# ---------- Memoria ----------
def init_db():
    with db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, wa_id TEXT, rol TEXT, contenido TEXT, ts TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS procesados (msg_id TEXT PRIMARY KEY)")


def guardar(wa_id, rol, contenido):
    with db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO mensajes (wa_id, rol, contenido, ts) VALUES (?, ?, ?, ?)",
                  (wa_id, rol, contenido, datetime.now(timezone.utc).isoformat()))


def historial(wa_id):
    with db_lock, sqlite3.connect(DB_PATH) as c:
        filas = c.execute("SELECT rol, contenido FROM mensajes WHERE wa_id = ? ORDER BY id DESC LIMIT ?",
                          (wa_id, MAX_HISTORIAL)).fetchall()
    return [{"role": r, "content": t} for r, t in reversed(filas)]


def borrar_historial(wa_id):
    with db_lock, sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM mensajes WHERE wa_id = ?", (wa_id,))


def ya_procesado(msg_id):
    with db_lock, sqlite3.connect(DB_PATH) as c:
        cur = c.execute("INSERT OR IGNORE INTO procesados (msg_id) VALUES (?)", (msg_id,))
        return cur.rowcount == 0


init_db()


# ---------- WhatsApp ----------
def enviar_whatsapp(wa_id, texto):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{WA_PHONE_ID}/messages"
    r = requests.post(url, headers={"Authorization": f"Bearer {WA_TOKEN}"}, json={
        "messaging_product": "whatsapp",
        "to": wa_id,
        "type": "text",
        "text": {"body": texto[:4000]},
    }, timeout=20)
    if r.status_code >= 300:
        print("[SertainsBot] Error enviando WhatsApp:", r.status_code, r.text)


def firma_valida(req):
    if not META_APP_SECRET:
        return True
    firma = req.headers.get("X-Hub-Signature-256", "")
    esperada = "sha256=" + hmac.new(META_APP_SECRET.encode(), req.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma, esperada)


# ---------- Agenda (Cal.com, opcional) ----------
def ver_disponibilidad(fecha):
    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {"error": "Formato de fecha inválido, usa AAAA-MM-DD"}
    r = requests.get("https://api.cal.com/v2/slots", headers={
        "Authorization": f"Bearer {CAL_KEY}",
        "cal-api-version": "2024-09-04",
    }, params={
        "eventTypeId": CAL_EVENT_ID,
        "start": fecha,
        "end": (dia + timedelta(days=1)).strftime("%Y-%m-%d"),
        "timeZone": TZ_NAME,
    }, timeout=20)
    if r.status_code >= 300:
        return {"error": f"Cal.com respondió {r.status_code}: {r.text[:300]}"}
    data = r.json().get("data", {})
    return {"fecha": fecha, "horarios_disponibles": [s.get("start") for s in data.get(fecha, [])][:12]}


def reservar_reunion(inicio, nombre, email, negocio, necesidad, wa_id):
    try:
        inicio_utc = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return {"error": "Horario inválido; usa uno de los que entregó ver_disponibilidad"}
    r = requests.post("https://api.cal.com/v2/bookings", headers={
        "Authorization": f"Bearer {CAL_KEY}",
        "cal-api-version": "2024-08-13",
    }, json={
        "start": inicio_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "eventTypeId": int(CAL_EVENT_ID),
        "attendee": {"name": nombre, "email": email, "timeZone": TZ_NAME,
                     "phoneNumber": "+" + wa_id, "language": "es"},
        "metadata": {"negocio": str(negocio)[:400], "necesidad": str(necesidad)[:400], "origen": "whatsapp"},
    }, timeout=20)
    if r.status_code >= 300:
        return {"error": f"No se pudo reservar ({r.status_code}): {r.text[:300]}"}
    return {"ok": True}


HERRAMIENTAS = [
    {"type": "function", "function": {
        "name": "ver_disponibilidad",
        "description": "Consulta horarios disponibles para una reunión de diagnóstico en una fecha.",
        "parameters": {"type": "object", "properties": {
            "fecha": {"type": "string", "description": "Fecha en formato AAAA-MM-DD"}},
            "required": ["fecha"]}}},
    {"type": "function", "function": {
        "name": "reservar_reunion",
        "description": "Reserva la reunión. Úsala solo cuando el cliente confirmó horario y entregó todos los datos.",
        "parameters": {"type": "object", "properties": {
            "inicio": {"type": "string", "description": "Horario exacto tal como lo entregó ver_disponibilidad"},
            "nombre": {"type": "string"},
            "email": {"type": "string"},
            "negocio": {"type": "string", "description": "Nombre y rubro del negocio del cliente"},
            "necesidad": {"type": "string", "description": "Resumen de lo que necesita"}},
            "required": ["inicio", "nombre", "email", "negocio", "necesidad"]}}},
]


def ejecutar_herramienta(nombre, args, wa_id):
    try:
        if nombre == "ver_disponibilidad":
            return ver_disponibilidad(args.get("fecha", ""))
        if nombre == "reservar_reunion":
            return reservar_reunion(args.get("inicio", ""), args.get("nombre", ""), args.get("email", ""),
                                    args.get("negocio", ""), args.get("necesidad", ""), wa_id)
        return {"error": f"Herramienta desconocida: {nombre}"}
    except Exception as e:
        return {"error": str(e)}


# ---------- IA (Gemini u OpenRouter, mismo formato) ----------
def llamar_llm(mensajes):
    cuerpo = {"model": LLM_MODEL, "messages": mensajes}
    if CAL_KEY and CAL_EVENT_ID:
        cuerpo["tools"] = HERRAMIENTAS
    r = requests.post(f"{LLM_BASE_URL}/chat/completions", headers={
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }, json=cuerpo, timeout=90)
    if r.status_code >= 300:
        raise RuntimeError(f"IA respondió {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]


def generar_respuesta(wa_id, texto):
    ahora = datetime.now(TZ).strftime("%A %Y-%m-%d %H:%M")
    sistema = SYSTEM_PROMPT + f"\n\nFecha y hora actual en Chile: {ahora}"
    if not (CAL_KEY and CAL_EVENT_ID):
        sistema += "\nLa agenda automática no está activa: si quieren reunión, pide nombre, email y horario preferido y di que el equipo confirmará."
    mensajes = [{"role": "system", "content": sistema}] + historial(wa_id) + [{"role": "user", "content": texto}]

    for _ in range(5):
        msg = llamar_llm(mensajes)
        llamadas = msg.get("tool_calls")
        if not llamadas:
            return (msg.get("content") or "").strip() or "¿Me lo puedes repetir? 🙏"
        mensajes.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": llamadas})
        for tc in llamadas:
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            resultado = ejecutar_herramienta(tc["function"]["name"], args, wa_id)
            mensajes.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                             "content": json.dumps(resultado, ensure_ascii=False)})
    return "Te voy a derivar con alguien del equipo para ayudarte mejor 🙌"


def procesar(wa_id, texto):
    try:
        if texto.strip().lower() == "reiniciar":
            borrar_historial(wa_id)
            enviar_whatsapp(wa_id, "Listo, empezamos de nuevo 🚀 ¿En qué te ayudo?")
            return
        respuesta = generar_respuesta(wa_id, texto)
        guardar(wa_id, "user", texto)
        guardar(wa_id, "assistant", respuesta)
        enviar_whatsapp(wa_id, respuesta)
    except Exception as e:
        print("[SertainsBot] Error procesando mensaje:", repr(e))
        enviar_whatsapp(wa_id, "Tuve un problema técnico 😅 Intenta de nuevo en un momento.")


# ---------- Rutas ----------
@bot_bp.get("/whatsapp/webhook")
def verificar_webhook():
    if (request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == WA_VERIFY_TOKEN):
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@bot_bp.post("/whatsapp/webhook")
def recibir_webhook():
    if not firma_valida(request):
        abort(403)
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []):
                if ya_procesado(m.get("id", "")):
                    continue
                wa_id = m.get("from")
                if m.get("type") == "text":
                    threading.Thread(target=procesar, args=(wa_id, m["text"]["body"]), daemon=True).start()
                else:
                    threading.Thread(target=enviar_whatsapp, args=(
                        wa_id, "Por ahora solo puedo leer mensajes de texto ✍️"), daemon=True).start()
    return "ok", 200
