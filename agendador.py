# ============================================================
# agendador.py — Orquestra o agente de usados
# ============================================================

import time
import schedule
from datetime import datetime
from scraper import coletar
from avaliador import avaliar_anuncio
from banco import criar_tabelas, ja_avaliado, salvar, total_avaliados
from notificador import notificar_oportunidade, notificar_resumo, notificar_inicio, notificar_erro
from config import INTERVALO_HORAS, DESCONTO_MINIMO_PERC


def executar_rodada():
    print(f"\n{'='*50}")
    print(f"⏰ NOVA RODADA — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")

    total_analisados = 0
    oportunidades    = 0

    try:
        anuncios = coletar()
        if not anuncios:
            print("⚠️  Nenhum anúncio coletado.")
            return

        print(f"\n📊 Avaliando {len(anuncios)} anúncios...")

        for an in anuncios:
            id_fb = an.get("id_facebook")
            if ja_avaliado(id_fb):
                continue

            print(f"\n🔍 {an['titulo'][:55]} — R${an['preco']:,} [{an['categoria']}]")

            av = avaliar_anuncio(an)

            if not av:
                print(f"  ↩️  Descartado")
                continue

            total_analisados += 1
            salvar(av)

            desc = av.get("desconto", 0) or 0
            print(f"  📊 Score: {av['score']}/10 | {av['recomendacao']} | {desc:.0f}% abaixo do novo")

            if desc >= DESCONTO_MINIMO_PERC and av["recomendacao"] in ("COMPRAR", "INVESTIGAR"):
                oportunidades += 1
                notificar_oportunidade(av)
                print(f"  📱 Notificação enviada!")

            time.sleep(0.5)

        print(f"\n✅ Rodada concluída:")
        print(f"   • Avaliados:      {total_analisados}")
        print(f"   • Oportunidades:  {oportunidades}")
        print(f"   • Total no banco: {total_avaliados()}")
        notificar_resumo(total_analisados, oportunidades)

    except Exception as e:
        import traceback
        msg = f"Erro: {str(e)}"
        print(f"❌ {msg}")
        traceback.print_exc()
        notificar_erro(msg)


def iniciar():
    print("🛍️  Agente de Usados — Curitiba FB Marketplace")
    print(f"⏱  A cada {INTERVALO_HORAS}h | Notifica com ≥{DESCONTO_MINIMO_PERC}% de desconto")
    criar_tabelas()
    notificar_inicio()
    executar_rodada()
    schedule.every(INTERVALO_HORAS).hours.do(executar_rodada)
    print(f"\n⏳ Próxima rodada em {INTERVALO_HORAS}h. Rodando...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    iniciar()
