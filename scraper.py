# ============================================================
# scraper.py — Coleta anúncios do Facebook Marketplace
# Busca por múltiplas categorias de produtos usados
# v4 — login limpo sem JS, prioridade cookies disco
# ============================================================

import re
import json
import time
import random
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from config import (
    FACEBOOK_EMAIL, FACEBOOK_SENHA,
    CATEGORIAS, PROIBIDOS_GLOBAL,
    PRECO_MINIMO, PRECO_MAXIMO, DIAS_ANUNCIADO,
)

ARQUIVO_COOKIES = "cookies_fb.json"
ARQUIVO_SESSAO  = "sessao_facebook.json"
TIMEOUT         = 30000


def pausa(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))


def extrair_preco(txt):
    m = re.search(r'R\$\s*([\d\.]+)', txt)
    if m:
        try:
            return int(m.group(1).replace(".", ""))
        except Exception:
            return 0
    return 0


def is_proibido(texto):
    txt = texto.lower()
    for p in PROIBIDOS_GLOBAL:
        if p.lower() in txt:
            return True
    return False


def categoria_match(texto, categoria):
    txt = texto.lower()
    for p in categoria.get("proibidos", []):
        if p.lower() in txt:
            return False
    for kw in categoria["keywords"]:
        if kw.lower() in txt:
            return True
    return False


def _carregar_lista_cookies():
    """
    Prioridade:
    1. cookies_fb.json no disco (gerado pelo pre-deploy no IP do Railway)
    2. sessao_facebook.json no disco
    3. Variável FB_COOKIES_JSON (fallback — IP pode ser diferente)
    """
    # 1. Arquivos no disco — gerados pelo pre_deploy_login.py no mesmo IP
    for arq in [ARQUIVO_COOKIES, ARQUIVO_SESSAO]:
        if os.path.exists(arq):
            try:
                with open(arq) as f:
                    data = json.load(f)
                lista = data.get("cookies", data) if isinstance(data, dict) else data
                if isinstance(lista, list) and len(lista) >= 3:
                    tem_xs = any(c.get("name") == "xs" for c in lista if isinstance(c, dict))
                    print(f"🍪 Cookies de {arq} ({len(lista)} cookies, xs={'presente' if tem_xs else 'ausente'})")
                    return lista
            except Exception as e:
                print(f"⚠️  Erro ao ler {arq}: {e}")

    # 2. Variável de ambiente (fallback)
    env_cookies = os.environ.get("FB_COOKIES_JSON", "")
    if env_cookies:
        try:
            data = json.loads(env_cookies)
            lista = data.get("cookies", data) if isinstance(data, dict) else data
            if isinstance(lista, list) and lista:
                print(f"🍪 Cookies da env FB_COOKIES_JSON ({len(lista)} cookies) [fallback]")
                return lista
        except Exception as e:
            print(f"⚠️  Erro ao ler FB_COOKIES_JSON: {e}")
    return []


def fazer_login_e_salvar_cookies():
    print("🔐 Fazendo login no Facebook...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width":1280,"height":900}, locale="pt-BR")
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        try:
            page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=TIMEOUT)
            pausa(2,3)
            if page.locator('input[name="email"]').count():
                page.fill('input[name="email"]', FACEBOOK_EMAIL)
                pausa(0.5,1)
                page.fill('input[name="pass"]', FACEBOOK_SENHA)
                pausa(0.5,1)
                page.keyboard.press("Enter")
                pausa(4,6)
            cookies = ctx.cookies()
            with open(ARQUIVO_COOKIES, "w") as f:
                json.dump(cookies, f, indent=2)
            print(f"✅ {len(cookies)} cookies salvos")
            return cookies
        except Exception as e:
            print(f"❌ Login falhou: {e}")
            return []
        finally:
            browser.close()


def _extrair_cards(page):
    """Extrai cards da página atual do Marketplace."""
    return page.evaluate(r"""() => {
        const cards = document.querySelectorAll('a[href*="/marketplace/item/"]');
        const vistos = new Set();
        const result = [];
        for (const a of cards) {
            const m = (a.href||'').match(/\/marketplace\/item\/(\d+)\//);
            if (!m) continue;
            const id = m[1];
            if (vistos.has(id)) continue;
            vistos.add(id);
            let node = a;
            for (let j=0; j<8; j++) {
                if (!node.parentElement) break;
                node = node.parentElement;
                const txt = node.innerText||'';
                if (txt.includes('R$') && txt.length > 10 && txt.length < 400) {
                    result.push({id, txt: txt.substring(0,250)});
                    break;
                }
            }
            if (!result.find(r=>r.id===id))
                result.push({id, txt:(a.innerText||'').substring(0,250)});
        }
        return result;
    }""")


def buscar_categoria(page, categoria):
    """Busca anúncios de uma categoria específica."""
    url = categoria["url"]
    nome_cat = categoria["nome"]
    encontrados = {}

    try:
        print(f"  📂 {nome_cat}: {url[:80]}...")
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
        pausa(5, 8)  # pausa maior — FB pode redirecionar e voltar

        url_atual = page.url.lower()
        print(f"    URL atual: {url_atual[:80]}")

        # Verificar login de forma mais robusta
        if "login" in url_atual or "checkpoint" in url_atual:
            # Tentar aguardar mais — às vezes FB redireciona e volta
            pausa(3, 5)
            url_atual = page.url.lower()
            if "login" in url_atual or "checkpoint" in url_atual:
                print("  ❌ Sessão expirada — redirecionado para login")
                return {}

        # Scroll para carregar mais
        ultimo = 0
        sem_novo = 0
        for i in range(40):
            if i % 3 == 0:
                page.evaluate("window.scrollBy({top:1500,behavior:'smooth'})")
            else:
                page.mouse.wheel(0, random.randint(800, 2000))
            pausa(0.7, 1.3)
            n = page.locator('a[href*="/marketplace/item/"]').count()
            if i % 10 == 9:
                print(f"    Scroll {i+1}: {n} cards")
            if n > ultimo:
                ultimo = n
                sem_novo = 0
            else:
                sem_novo += 1
                if sem_novo >= 8:
                    break

        cards = _extrair_cards(page)
        for item in cards:
            id_fb = item["id"]
            txt   = item["txt"]
            preco = extrair_preco(txt)

            if not preco or preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                continue
            if is_proibido(txt):
                continue
            if not categoria_match(txt, categoria):
                continue

            # Título: primeira linha substancial
            linhas = [l.strip() for l in txt.split("\n") if l.strip() and "R$" not in l]
            titulo = linhas[0][:120] if linhas else txt[:80]

            encontrados[id_fb] = {
                "id_facebook":    id_fb,
                "link":           f"https://www.facebook.com/marketplace/item/{id_fb}/",
                "titulo":         titulo,
                "preco":          preco,
                "categoria":      nome_cat,
                "texto_completo": txt,
                "fotos":          [],
                "descricao":      "",
                "data_coleta":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        print(f"    ✅ {len(encontrados)} anúncios válidos em {nome_cat}")

    except Exception as e:
        print(f"  ❌ Erro em {nome_cat}: {e}")

    return encontrados


def coletar_detalhes(anuncios, page):
    """Abre cada PDP para pegar descrição e fotos."""
    print(f"\n🔍 Coletando detalhes de {len(anuncios)} anúncios...")
    for i, an in enumerate(anuncios):
        try:
            print(f"  [{i+1}/{len(anuncios)}] {an['titulo'][:50]}")
            page.goto(an["link"], wait_until="domcontentloaded", timeout=TIMEOUT)
            pausa(1.5, 2.5)

            # Descrição
            for sel in ['[data-testid="marketplace-pdp-seller-description"]',
                        '[class*="description"]']:
                el = page.locator(sel).first
                try:
                    txt = el.inner_text(timeout=3000)
                    if len(txt) > 30:
                        an["descricao"] = txt[:1500]
                        break
                except Exception:
                    pass

            # Fotos
            try:
                fotos = page.evaluate("""() => {
                    const urls = new Set();
                    document.querySelectorAll('img').forEach(img => {
                        const src = img.src||'';
                        if (!src.includes('fbcdn')) return;
                        if (src.includes('_s.')||src.includes('_t.')||src.includes('emoji')) return;
                        if ((img.naturalWidth||img.width||0) >= 200) urls.add(src);
                    });
                    return [...urls].slice(0,5);
                }""")
                if fotos:
                    an["fotos"] = fotos
                    print(f"    📸 {len(fotos)} fotos")
            except Exception:
                pass

        except Exception as e:
            print(f"    ⚠️  {e}")
        pausa(0.8, 1.5)
    return anuncios


def coletar():
    print("\n" + "="*50)
    print(f"🛍️  Iniciando coleta — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*50)

    cookies_list = _carregar_lista_cookies()
    if not cookies_list:
        print("🔐 Sem cookies — fazendo login...")
        fazer_login_e_salvar_cookies()
        cookies_list = _carregar_lista_cookies()
        if not cookies_list:
            print("❌ Sem cookies. Encerrando.")
            return []

    todos = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
            "--single-process","--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width":1280,"height":900},
            locale="pt-BR", timezone_id="America/Sao_Paulo",
            extra_http_headers={"Accept-Language":"pt-BR,pt;q=0.9"})
        ctx.add_cookies(cookies_list)
        page = ctx.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
            Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
            Object.defineProperty(navigator,'languages',{get:()=>['pt-BR','pt']});
            window.chrome={runtime:{}};
            Object.defineProperty(navigator,'platform',{get:()=>'Win32'});
        """)

        # Aquecer sessão: navegar ao FB e fazer login se necessário
        # Verificar sessão — se inválida, fazer login direto
        try:
            print("🔥 Verificando sessão FB...")
            page.goto("https://www.facebook.com/marketplace/curitiba/",
                      wait_until="domcontentloaded", timeout=TIMEOUT)
            pausa(5, 7)
            url_home = page.url.lower()
            print(f"  URL: {url_home[:80]}")

            if "login" in url_home or "checkpoint" in url_home:
                print("⚠️  Sessão inválida — fazendo login com email/senha...")
                # Usar a função de login já existente no módulo
                page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=TIMEOUT)
                pausa(2, 3)
                logou = False
                for email_sel in ['input[name="email"]', '#email', 'input[type="email"]']:
                    if page.locator(email_sel).count() > 0:
                        page.fill(email_sel, FACEBOOK_EMAIL)
                        pausa(0.5, 1)
                        for pass_sel in ['input[name="pass"]', '#pass', 'input[type="password"]']:
                            if page.locator(pass_sel).count() > 0:
                                page.fill(pass_sel, FACEBOOK_SENHA)
                                pausa(0.5, 1)
                                page.keyboard.press("Enter")
                                pausa(7, 10)
                                logou = True
                                break
                        break
                url_pos = page.url.lower()
                print(f"  URL pós-login: {url_pos[:80]}")
                if "login" in url_pos or not logou:
                    print("❌ Login falhou — encerrando")
                    browser.close()
                    return []
                print("✅ Login realizado!")
                novos = ctx.cookies()
                with open(ARQUIVO_COOKIES, "w") as f:
                    json.dump(novos, f, indent=2)
                print(f"  💾 {len(novos)} cookies salvos")
            else:
                print("✅ Sessão válida!")
        except Exception as e:
            print(f"⚠️  Erro ao verificar sessão: {e}")

        for cat in CATEGORIAS:
            novos = buscar_categoria(page, cat)
            antes = len(todos)
            todos.update(novos)
            print(f"  +{len(todos)-antes} novos (total acumulado: {len(todos)})")
            pausa(2, 4)

        # Coletar detalhes dos melhores
        lista = list(todos.values())
        print(f"\n📦 {len(lista)} anúncios únicos coletados")

        if lista:
            lista = coletar_detalhes(lista, page)

        browser.close()

    print(f"\n✅ Coleta finalizada: {len(lista)} anúncios")
    return lista
