# ============================================================
# config.py — Agente de Usados — Facebook Marketplace Curitiba
# Garimpagem: preço ≤ 50% do valor de referência → notifica
# ============================================================

import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FACEBOOK_EMAIL    = os.environ.get("FACEBOOK_EMAIL", "")
FACEBOOK_SENHA    = os.environ.get("FACEBOOK_SENHA", "")
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Parâmetros gerais ---
INTERVALO_HORAS      = 2
DESCONTO_MINIMO_PERC = 50    # notificar só se preço ≤ 50% do valor de referência
PRECO_MINIMO         = 100   # ignorar abaixo disso (bugigangas)
PRECO_MAXIMO         = 8000  # ignorar acima disso (evita carros, imóveis)
DIAS_ANUNCIADO       = 3     # só anúncios dos últimos X dias

# --- Categorias monitoradas no Facebook Marketplace ---
# Cada categoria tem: url_path, nome, palavras-chave aceitas, palavras proibidas
CATEGORIAS = [
    {
        "nome": "Eletrodomésticos",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=eletrodomestico&exact=false",
        "keywords": [
            "geladeira", "refrigerador", "fogão", "forno", "microondas",
            "máquina de lavar", "lavadora", "secadora", "lava louça",
            "ar condicionado", "ventilador", "purificador", "aspirador",
            "batedeira", "liquidificador", "cafeteira", "fritadeira",
            "churrasqueira", "televisão", "tv ", " tv", "monitor",
        ],
        "proibidos": ["celular", "notebook", "tablet", "iphone", "samsung galaxy",
                      "xiaomi", "motorola", "lenovo", "dell", "hp ", " hp"],
    },
    {
        "nome": "Ferramentas e Jardim",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=ferramenta+usada&exact=false",
        "keywords": [
            "motosserra", "moto serra", "roçadeira", "roçadeira",
            "furadeira", "parafusadeira", "esmerilhadeira", "lixadeira",
            "compressor", "gerador", "soldadora", "inversora",
            "betoneira", "cortador", "lavadora pressão", "karcher",
            "conjunto ferramenta", "caixa ferramenta",
        ],
        "proibidos": ["celular", "notebook", "peça", "cabo"],
    },
    {
        "nome": "Som e Áudio",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=som+automotivo+amplificador&exact=false",
        "keywords": [
            "amplificador", "caixa de som", "subwoofer", "falante",
            "receiver", "home theater", "soundbar", "módulo",
            "som automotivo", "toca discos", "vitrola",
            "fone de ouvido", "headphone", "caixa acústica",
        ],
        "proibidos": ["celular", "notebook", "peça avulsa"],
    },
    {
        "nome": "Prata e Joias",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=prata+925&exact=false",
        "keywords": [
            "prata 925", "prata sterling", "prata maciça",
            "corrente prata", "anel prata", "pulseira prata",
            "brinco prata", "pingente prata",
            "ouro", "18k", "750", "750ml",
        ],
        "proibidos": ["folheado", "banhado", "bijuteria", "imitação", "fake"],
    },
    {
        "nome": "Móveis e Decoração",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=sofa+mesa+guarda+roupa&exact=false",
        "keywords": [
            "sofá", "sofa", "guarda roupa", "roupeiro", "cama",
            "colchão", "mesa jantar", "mesa escritório", "cadeira",
            "armário", "estante", "cristaleira", "rack",
        ],
        "proibidos": ["celular", "notebook"],
    },
    {
        "nome": "Bicicletas e Esporte",
        "url":  "https://www.facebook.com/marketplace/curitiba/search?"
                "query=bicicleta+musculacao&exact=false",
        "keywords": [
            "bicicleta", "bike", "mtb", "speed", "elétrica",
            "musculação", "esteira", "bicicleta ergométrica",
            "elíptico", "prancha", "halteres", "anilhas",
        ],
        "proibidos": ["celular", "notebook", "peça"],
    },
]

# --- Produtos explicitamente proibidos (globais) ---
PROIBIDOS_GLOBAL = [
    "celular", "smartphone", "iphone", "samsung galaxy", "xiaomi redmi",
    "motorola moto", "notebook", "laptop", "macbook", "ipad", "tablet",
    "playstation", "xbox", "nintendo",  # games têm mercado próprio
]

# --- Mapa de referência de preços (valor médio de novo no Brasil) ---
# Usado quando ML não encontra — estimativa conservadora
# Fonte: pesquisa manual — atualizar periodicamente
PRECO_REFERENCIA = {
    # Eletrodomésticos
    "geladeira":         2500,
    "refrigerador":      2500,
    "fogão":             1200,
    "microondas":        600,
    "máquina de lavar":  2000,
    "ar condicionado":   1800,
    "televisão":         1500,
    "tv":                1500,
    # Ferramentas
    "motosserra":        1500,
    "moto serra":        1500,
    "roçadeira":         800,
    "furadeira":         400,
    "compressor":        1200,
    "gerador":           3000,
    "lavadora pressão":  1000,
    "karcher":           1000,
    # Som
    "amplificador":      800,
    "subwoofer":         600,
    "home theater":      1200,
    "soundbar":          800,
    # Prata (por grama ~R$8-12)
    "prata 925":         500,   # peça média
    # Móveis
    "sofá":              2000,
    "guarda roupa":      1500,
    "colchão":           1200,
    # Esporte
    "bicicleta":         1500,
    "esteira":           2000,
    "musculação":        800,
}
