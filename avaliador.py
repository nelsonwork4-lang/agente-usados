# ============================================================
# avaliador.py — Avalia anúncios de usados
# Lógica: preço anunciado vs preço de referência (novo no ML)
# Notifica se ≤ 50% do valor de referência
# ============================================================

import anthropic
import json
import re
import base64
import requests
from config import (
    ANTHROPIC_API_KEY,
    DESCONTO_MINIMO_PERC,
    PRECO_REFERENCIA,
    PROIBIDOS_GLOBAL,
)

cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def buscar_preco_referencia_ml(titulo):
    """
    Busca o preço médio do produto NOVO no Mercado Livre.
    Retorna o preço médio ou None.
    """
    # Limpar o título para busca
    query = re.sub(r'\b(usado|usada|semi novo|seminovo|conservado)\b', '', titulo, flags=re.IGNORECASE)
    query = query.strip()[:60]

    try:
        url = "https://api.mercadolibre.com/sites/MLB/search"
        params = {"q": query, "condition": "new", "limit": 5}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        resultados = r.json().get("results", [])
        precos = [x["price"] for x in resultados if x.get("price", 0) > 0]
        if not precos:
            return None
        return round(sum(precos) / len(precos), 2)
    except Exception:
        return None


def buscar_preco_referencia_local(titulo):
    """Fallback: busca no mapa estático de preços."""
    titulo_lower = titulo.lower()
    for chave, preco in PRECO_REFERENCIA.items():
        if chave in titulo_lower:
            return preco
    return None


def calcular_desconto(preco_anuncio, preco_referencia):
    """Retorna % de desconto em relação ao preço de referência."""
    if not preco_referencia or preco_referencia <= 0:
        return None
    return round((1 - preco_anuncio / preco_referencia) * 100, 1)


def baixar_foto_base64(url):
    try:
        r = requests.get(url, timeout=12,
            headers={"User-Agent": "Mozilla/5.0 Chrome/124.0.0.0"})
        if r.status_code == 200:
            ct = r.headers.get("content-type", "image/jpeg")
            mt = "image/png" if "png" in ct else "image/webp" if "webp" in ct else "image/jpeg"
            return {"data": base64.standard_b64encode(r.content).decode(), "media_type": mt}
    except Exception:
        pass
    return None


def avaliar_anuncio(anuncio):
    """
    Avalia um anúncio de produto usado.
    Retorna dict com score e recomendação, ou None se não for oportunidade.
    """
    titulo     = anuncio.get("titulo", "")
    preco      = anuncio.get("preco", 0)
    descricao  = anuncio.get("descricao", "")
    fotos      = anuncio.get("fotos", [])
    categoria  = anuncio.get("categoria", "")

    # Verificação global de proibidos (segunda camada)
    texto_completo = titulo + " " + descricao
    for p in PROIBIDOS_GLOBAL:
        if p.lower() in texto_completo.lower():
            return None

    # Buscar preço de referência (novo)
    preco_ref = buscar_preco_referencia_ml(titulo)
    fonte_ref = "ML"
    if not preco_ref:
        preco_ref = buscar_preco_referencia_local(titulo)
        fonte_ref = "tabela"

    desconto = calcular_desconto(preco, preco_ref)

    # Montar prompt para Claude
    tem_fotos = len(fotos) > 0
    conteudo = []

    prompt = f"""Você é um especialista em avaliação de produtos usados em Curitiba/PR.

Avalie este anúncio do Facebook Marketplace.

DADOS DO ANÚNCIO:
- Título: {titulo}
- Preço pedido: R$ {preco:,}
- Categoria: {categoria}
- Descrição: {descricao[:600] or 'Sem descrição'}

REFERÊNCIA DE PREÇO:
- Preço médio novo ({fonte_ref}): R$ {preco_ref:,.0f} {'(não encontrado)' if not preco_ref else ''}
- Desconto estimado: {f'{desconto:.0f}% abaixo do novo' if desconto else 'não calculado'}

{'''ANALISE AS FOTOS COM ATENÇÃO:
- Estado de conservação geral (0=destruído, 10=como novo)
- Sinais de uso excessivo, ferrugem, amassados, quebrados
- Partes faltando ou danificadas
- Se produto parece funcional
- Se condiz com o preço pedido''' if tem_fotos else ''}

Responda SOMENTE com JSON válido:
{{
  "score": <0-10 considerando preço + estado>,
  "estado_conservacao": <0-10 baseado nas fotos, null se sem fotos>,
  "preco_justo": <true se preço está bom para o estado>,
  "preco_referencia_estimado": <sua estimativa do valor de novo em R$>,
  "desconto_real_estimado": <% que está abaixo do valor de novo>,
  "recomendacao": <"COMPRAR", "INVESTIGAR" ou "IGNORAR">,
  "justificativa": "<1-2 frases>",
  "alertas": ["<problema 1>", "<problema 2>"],
  "pontos_positivos": ["<ponto 1>"],
  "potencial_revenda": <true se vale revender com lucro>
}}"""

    conteudo.append({"type": "text", "text": prompt})

    # Adicionar fotos
    fotos_carregadas = 0
    for url in fotos[:3]:
        foto = baixar_foto_base64(url)
        if foto:
            conteudo.append({
                "type": "image",
                "source": {"type": "base64", "media_type": foto["media_type"], "data": foto["data"]}
            })
            fotos_carregadas += 1

    if fotos_carregadas > 0:
        conteudo.append({"type": "text",
            "text": f"Analise as {fotos_carregadas} foto(s) e retorne o JSON."})
    else:
        conteudo.append({"type": "text",
            "text": "Sem fotos disponíveis. Avalie pelo texto e retorne o JSON."})

    try:
        modelo  = "claude-sonnet-4-6" if fotos_carregadas > 0 else "claude-haiku-4-5-20251001"
        max_tok = 1500 if fotos_carregadas > 0 else 900
        print(f"  🤖 IA | {fotos_carregadas} foto(s) | ref: R${preco_ref:,.0f} | desconto: {desconto or '?'}%")

        msg = cliente.messages.create(
            model=modelo, max_tokens=max_tok,
            messages=[{"role": "user", "content": conteudo}])

        txt = msg.content[0].text.strip()
        txt = re.sub(r'```json|```', '', txt).strip()

        # Parser robusto — repara JSON truncado
        try:
            resultado = json.loads(txt)
        except json.JSONDecodeError:
            # Tentar extrair objeto JSON completo
            m = re.search(r'\{.*\}', txt, re.DOTALL)
            if m:
                try:
                    resultado = json.loads(m.group(0))
                except Exception:
                    raise
            else:
                raise

        # Enriquecer resultado
        resultado["titulo"]      = titulo
        resultado["preco"]       = preco
        resultado["preco_ref"]   = preco_ref
        resultado["fonte_ref"]   = fonte_ref
        resultado["desconto"]    = desconto or resultado.get("desconto_real_estimado", 0)
        resultado["categoria"]   = categoria
        resultado["link"]        = anuncio.get("link", "")
        resultado["fotos"]       = fotos
        resultado["id_facebook"] = anuncio.get("id_facebook", "")

        # Filtro final: só retorna se desconto >= DESCONTO_MINIMO_PERC
        desc_final = resultado.get("desconto", 0) or 0
        if isinstance(desc_final, str):
            desc_final = float(re.sub(r'[^\d.]', '', desc_final) or 0)

        if desc_final < DESCONTO_MINIMO_PERC and resultado.get("recomendacao") == "IGNORAR":
            print(f"  ↩️  Desconto insuficiente ({desc_final:.0f}%) — IGNORAR")
            return None

        return resultado

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON inválido: {e}")
    except Exception as e:
        print(f"  ⚠️  Erro IA: {e}")
    return None
