# ============================================================
# notificador.py — Envia alertas no Telegram
# ============================================================

import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def _enviar(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM] {texto[:100]}")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": texto,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️  Telegram erro: {e}")
        return False


def notificar_oportunidade(av):
    desc = av.get("desconto", 0)
    emoji_desc = "🔥" if desc >= 60 else "💰" if desc >= 50 else "👀"

    alertas = av.get("alertas", [])
    alertas_txt = "\n".join(f"  ⚠️ {a}" for a in alertas[:3]) if alertas else "  ✅ Sem alertas"

    positivos = av.get("pontos_positivos", [])
    pos_txt = "\n".join(f"  ✅ {p}" for p in positivos[:2]) if positivos else ""

    msg = (
        f"{emoji_desc} <b>GARIMPO — {av.get('categoria','').upper()}</b>\n\n"
        f"📦 <b>{av.get('titulo','')[:60]}</b>\n"
        f"💵 <b>R$ {av.get('preco',0):,}</b> "
        f"(ref: R$ {av.get('preco_ref',0):,.0f} novo)\n"
        f"📉 <b>{desc:.0f}% abaixo do novo</b>\n\n"
        f"⭐ Score: {av.get('score',0)}/10 | {av.get('recomendacao','')}\n"
        f"💬 {av.get('justificativa','')}\n\n"
        f"<b>Alertas:</b>\n{alertas_txt}\n"
        f"{pos_txt}\n\n"
        f"🔗 {av.get('link','')}"
    )
    return _enviar(msg)


def notificar_resumo(total, oportunidades):
    msg = (
        f"📊 <b>Resumo — Agente Usados</b>\n\n"
        f"🔍 Analisados: {total}\n"
        f"💰 Oportunidades (≥50% desc): {oportunidades}\n"
    )
    return _enviar(msg)


def notificar_inicio():
    return _enviar("🛍️ <b>Agente Usados iniciado!</b>\nMonitorando FB Marketplace Curitiba...")


def notificar_erro(msg):
    return _enviar(f"❌ <b>Erro Agente Usados:</b>\n{msg[:300]}")
