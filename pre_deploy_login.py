#!/usr/bin/env python3
"""
pre_deploy_login.py — Roda antes do agendador no Railway.
Faz login no Facebook e salva cookies frescos no IP do Railway.
"""
import json, time, os
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("FACEBOOK_EMAIL", "")
SENHA = os.environ.get("FACEBOOK_SENHA", "")

if not EMAIL or not SENHA:
    print("⚠️  FACEBOOK_EMAIL/SENHA não definidos — pulando login")
    exit(0)

print(f"🔐 Pre-deploy: fazendo login no Facebook ({EMAIL[:15]}...)")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--no-sandbox","--disable-dev-shm-usage","--disable-gpu","--single-process"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        viewport={"width":1280,"height":900}, locale="pt-BR")
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

    try:
        page.goto("https://www.facebook.com/login/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Preencher email
        for sel in ['input[name="email"]', '#email', 'input[type="email"]']:
            if page.locator(sel).count() > 0:
                page.fill(sel, EMAIL)
                break

        time.sleep(0.5)

        # Preencher senha
        for sel in ['input[name="pass"]', '#pass', 'input[type="password"]']:
            if page.locator(sel).count() > 0:
                page.fill(sel, SENHA)
                break

        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(8)

        url = page.url.lower()
        print(f"URL pós-login: {url[:80]}")

        if "login" in url or "checkpoint" in url:
            print("❌ Login falhou — FB pode exigir verificação manual")
            exit(1)

        cookies = ctx.cookies()
        with open("cookies_fb.json", "w") as f:
            json.dump(cookies, f, indent=2)
        print(f"✅ {len(cookies)} cookies salvos em cookies_fb.json")

    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)
    finally:
        browser.close()
