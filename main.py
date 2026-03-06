from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import re

app = FastAPI(title="WA Product Search Mock API", version="1.0")

CATALOG = [
    {
        "id": "SKU-001",
        "name": "Jarabe Infantil Miel & Limón 120 ml",
        "price": 139.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-001",
        "tags": ["infantil", "jarabe", "garganta", "miel", "limon"],
        "reason": "Opción infantil con miel; suele preferirse por sabor y sensación de recubrimiento."
    },
    {
        "id": "SKU-002",
        "name": "Jarabe Infantil Garganta Suave 120 ml",
        "price": 129.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-002",
        "tags": ["infantil", "jarabe", "garganta"],
        "reason": "Jarabe infantil enfocado en molestias de garganta; buena opción si no necesitas miel."
    },
    {
        "id": "SKU-003",
        "name": "Jarabe Propóleo + Miel (Niños) 150 ml",
        "price": 159.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-003",
        "tags": ["infantil", "jarabe", "garganta", "miel", "propoleo"],
        "reason": "Alternativa con miel; útil cuando buscan ingredientes tipo propóleo (revisar alergias)."
    },
    {
        "id": "SKU-004",
        "name": "Jarabe Sabor Fresa (Niños) 100 ml",
        "price": 119.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-004",
        "tags": ["infantil", "jarabe", "garganta", "sabor"],
        "reason": "Pensado para tolerancia de sabor en niños."
    },
    {
        "id": "SKU-005",
        "name": "Jarabe Herbal con Miel (Infantil) 100 ml",
        "price": 129.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-005",
        "tags": ["infantil", "jarabe", "miel", "herbal"],
        "reason": "Opción herbal con miel (ver ingredientes específicos en el detalle)."
    },
    {
        "id": "SKU-006",
        "name": "Jarabe Tos y Garganta (Infantil) 120 ml",
        "price": 149.0,
        "currency": "MXN",
        "imageUrl": "https://via.placeholder.com/600x400.png?text=SKU-006",
        "tags": ["infantil", "jarabe", "garganta", "tos"],
        "reason": "Si además menciona tos, esta opción suele encajar mejor (según etiqueta)."
    },
]

DISCLAIMER_SYMPTOMS = (
    "Aviso importante: la información es orientativa y puede cambiar por disponibilidad. "
    "Si hay fiebre alta, dificultad para respirar, dolor intenso o síntomas >48–72h, "
    "consulta a un médico/pediatra."
)

def parse_age(text: str) -> Optional[int]:
    m = re.search(r"(\d{1,2})\s*(años|anios)", text.lower())
    if m:
        return int(m.group(1))
    m = re.search(r"edad\s*(\d{1,2})", text.lower())
    if m:
        return int(m.group(1))
    return None

def infer_tags_from_query(text: str) -> List[str]:
    t = text.lower()
    mapping = {
        "jarabe": ["jarabe"],
        "garganta": ["garganta"],
        "dolor de garganta": ["garganta"],
        "tos": ["tos"],
        "miel": ["miel"],
        "limón": ["limon"],
        "limon": ["limon"],
        "propóleo": ["propoleo"],
        "propoleo": ["propoleo"],
        "niño": ["infantil"],
        "nino": ["infantil"],
        "infantil": ["infantil"],
        "hijo": ["infantil"],
    }
    tags = []
    for k, v in mapping.items():
        if k in t:
            tags.extend(v)
    return sorted(set(tags))

def score_product(prod: Dict[str, Any], wanted: List[str]) -> int:
    prod_tags = set(prod.get("tags", []))
    return sum(1 for w in wanted if w in prod_tags)

class SearchRequest(BaseModel):
    query: str
    context: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 6

@app.get("/")
def health():
    return {"ok": True, "service": "wa-mock-product-search"}

@app.post("/mock/search")
def search(req: SearchRequest):
    query = req.query or ""
    ctx = req.context or {}
    limit = max(1, min(int(req.limit or 6), 6))

    wanted = set(infer_tags_from_query(query))

    if ctx.get("form"):
        wanted.add(str(ctx["form"]).lower())
    if ctx.get("segment"):
        wanted.add(str(ctx["segment"]).lower())
    if ctx.get("symptom"):
        s = str(ctx["symptom"]).lower()
        if "garganta" in s:
            wanted.add("garganta")
        if "tos" in s:
            wanted.add("tos")
    for item in (ctx.get("must_have") or []):
        wanted.add(str(item).lower())

    age = ctx.get("age") or parse_age(query)
    if isinstance(age, int) and age <= 12:
        wanted.add("infantil")

    wanted_list = sorted(wanted)

    ranked = []
    for p in CATALOG:
        sc = score_product(p, wanted_list)
        if len(wanted_list) == 0 or sc > 0:
            ranked.append((sc, p))

    ranked.sort(key=lambda x: x[0], reverse=True)
    products = [p for _, p in ranked[:limit]]

    symptom_trigger = any(k in query.lower() for k in ["dolor", "síntoma", "sintoma", "garganta", "tos", "fiebre"])
    disclaimer = DISCLAIMER_SYMPTOMS if symptom_trigger else None

    return {
        "filters_used": {
            "age": age,
            "wanted_tags": wanted_list
        },
        "products": [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "currency": p["currency"],
                "imageUrl": p["imageUrl"],
                "reason": p["reason"],
                "cta": {"view": "Ver detalle", "add": "Agregar al carrito"}
            } for p in products
        ],
        "disclaimer": disclaimer
    }
