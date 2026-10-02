"""Recetario local (cantidades para 4 personas).

Se usa para proponer cenas y menús de fin de semana sin IA y para generar
la lista de la compra. Puedes añadir tus propios platos aquí.

Formato: (nombre, grupos, momento, ingredientes)
  momento: "cena", "comida" o "ambas"
  ingredientes: "Sección:Ingrediente=cantidad; ..."
"""

F, C, P, H, D, PA, CO = "Frutería", "Carnicería", "Pescadería", "Huevos y lácteos", "Despensa", "Panadería", "Congelados"

_RAW = [
    # ---------- Cenas ligeras: verdura + pescado ----------
    ("Merluza al horno con calabacín", "pescado verdura", "cena",
     f"{P}:Merluza en lomos=600 g; {F}:Calabacín=2; {F}:Cebolla=1; {F}:Limón=1; {D}:Aceite de oliva=; {D}:Ajo=2 dientes"),
    ("Salmón a la plancha con judías verdes", "pescado verdura", "cena",
     f"{P}:Salmón en lomos=4; {F}:Judías verdes=500 g; {F}:Limón=1; {D}:Aceite de oliva="),
    ("Crema de calabacín y bacalao en papillote", "pescado verdura", "cena",
     f"{P}:Bacalao desalado=600 g; {F}:Calabacín=3; {F}:Puerro=1; {F}:Patata=1; {H}:Quesitos=4"),
    ("Pescadilla rebozada con ensalada", "pescado verdura", "cena",
     f"{P}:Pescadilla en filetes=600 g; {H}:Huevos=2; {D}:Harina=; {F}:Lechuga=1; {F}:Tomate=2; {F}:Zanahoria=2"),
    ("Brochetas de rape y langostinos con pisto", "pescado verdura", "cena",
     f"{P}:Rape=400 g; {P}:Langostinos=12; {F}:Pimiento rojo=1; {F}:Pimiento verde=1; {F}:Calabacín=1; {D}:Tomate triturado=400 g"),
    ("Hamburguesas de atún con verduras al horno", "pescado verdura", "cena",
     f"{D}:Atún en lata=4 latas; {H}:Huevos=1; {D}:Pan rallado=; {F}:Berenjena=1; {F}:Calabacín=1; {F}:Pimiento rojo=1"),
    ("Sopa de pescado con fideos", "pescado verdura pasta", "cena",
     f"{P}:Preparado para sopa de pescado=500 g; {D}:Fideos=150 g; {F}:Tomate=2; {F}:Cebolla=1; {F}:Pimiento verde=1"),
    ("Gallo a la plancha con puré de verduras", "pescado verdura", "cena",
     f"{P}:Gallo en filetes=8; {F}:Calabaza=500 g; {F}:Zanahoria=3; {F}:Puerro=1; {F}:Patata=1"),
    ("Sardinas al horno con ensalada de tomate", "pescado verdura", "cena",
     f"{P}:Sardinas=1 kg; {F}:Tomate=4; {F}:Cebolla=1; {D}:Aceite de oliva="),
    ("Ensalada de pasta con atún y huevo", "pescado huevo pasta verdura", "cena",
     f"{D}:Pasta (lazos o tornillos)=300 g; {D}:Atún en lata=3 latas; {H}:Huevos=3; {F}:Tomate cherry=250 g; {D}:Maíz dulce=1 lata"),

    # ---------- Cenas: verdura + huevo ----------
    ("Tortilla de calabacín con ensalada", "huevo verdura", "cena",
     f"{H}:Huevos=8; {F}:Calabacín=2; {F}:Cebolla=1; {F}:Lechuga=1; {F}:Tomate=2"),
    ("Tortilla de patata con pimientos asados", "huevo patata verdura", "cena",
     f"{H}:Huevos=8; {F}:Patata=800 g; {F}:Cebolla=1; {F}:Pimiento rojo=2"),
    ("Revuelto de champiñones y gambas con pan", "huevo verdura pescado", "cena",
     f"{H}:Huevos=8; {F}:Champiñones=300 g; {CO}:Gambas peladas=200 g; {PA}:Pan=1 barra"),
    ("Huevos rellenos con ensalada", "huevo verdura pescado", "cena",
     f"{H}:Huevos=8; {D}:Atún en lata=2 latas; {D}:Tomate frito=; {D}:Mayonesa=; {F}:Lechuga=1"),
    ("Crema de calabaza y tortilla francesa", "huevo verdura", "cena",
     f"{F}:Calabaza=800 g; {F}:Zanahoria=2; {F}:Cebolla=1; {H}:Huevos=6; {H}:Nata para cocinar=200 ml"),
    ("Pizza casera de verduras y huevo", "huevo verdura lacteo", "cena",
     f"{PA}:Masa de pizza=2; {D}:Tomate triturado=200 g; {H}:Mozzarella=250 g; {F}:Pimiento verde=1; {F}:Champiñones=200 g; {H}:Huevos=2"),
    ("Huevos al plato con pisto", "huevo verdura", "cena",
     f"{H}:Huevos=8; {F}:Calabacín=1; {F}:Pimiento rojo=1; {F}:Cebolla=1; {D}:Tomate triturado=400 g"),
    ("Quiche de espinacas y queso", "huevo verdura lacteo", "cena",
     f"{PA}:Masa quebrada=1; {CO}:Espinacas=400 g; {H}:Huevos=4; {H}:Nata para cocinar=200 ml; {H}:Queso rallado=150 g"),

    # ---------- Cenas: verdura + carne blanca ----------
    ("Pechuga de pollo a la plancha con verduras salteadas", "carne verdura", "cena",
     f"{C}:Pechuga de pollo fileteada=600 g; {F}:Brócoli=1; {F}:Zanahoria=2; {F}:Calabacín=1"),
    ("Wraps de pollo y verduras", "carne verdura", "cena",
     f"{PA}:Tortillas de trigo=8; {C}:Pechuga de pollo=500 g; {F}:Lechuga=1; {F}:Tomate=2; {F}:Pimiento rojo=1; {H}:Queso rallado=100 g"),
    ("Pavo al horno con puré de patata", "carne patata", "cena",
     f"{C}:Pechuga de pavo=600 g; {F}:Patata=800 g; {H}:Leche=200 ml; {H}:Mantequilla=30 g"),
    ("Albóndigas de pollo en salsa de tomate con verduras", "carne verdura", "cena",
     f"{C}:Carne picada de pollo=500 g; {H}:Huevos=1; {D}:Pan rallado=; {D}:Tomate triturado=400 g; {F}:Zanahoria=2; {F}:Guisantes=200 g"),
    ("Crema de verduras y sándwich de pavo y queso", "carne verdura lacteo", "cena",
     f"{F}:Puerro=2; {F}:Zanahoria=3; {F}:Calabacín=1; {PA}:Pan de molde=1 paquete; {C}:Pavo en lonchas=200 g; {H}:Queso en lonchas=200 g"),
    ("Sopa de pollo con verduras y estrellitas", "carne verdura pasta", "cena",
     f"{C}:Contramuslos de pollo=4; {F}:Zanahoria=2; {F}:Puerro=1; {F}:Apio=1 rama; {D}:Pasta estrellitas=150 g"),

    # ---------- Cenas: verdura + lácteo / ligeras ----------
    ("Crema de calabacín con quesitos y picatostes", "verdura lacteo", "cena",
     f"{F}:Calabacín=4; {F}:Cebolla=1; {F}:Patata=1; {H}:Quesitos=6; {PA}:Pan=1 barra"),
    ("Ensalada completa con queso fresco y nueces", "verdura lacteo", "cena",
     f"{F}:Lechuga=1; {F}:Tomate=3; {H}:Queso fresco=250 g; {D}:Nueces=100 g; {F}:Manzana=1"),
    ("Verduras al horno con yogur y hummus", "verdura legumbre lacteo", "cena",
     f"{F}:Calabaza=500 g; {F}:Zanahoria=3; {F}:Cebolla roja=1; {D}:Garbanzos cocidos=1 bote; {H}:Yogur natural=2; {D}:Tahini="),
    ("Coliflor gratinada con bechamel", "verdura lacteo", "cena",
     f"{F}:Coliflor=1; {H}:Leche=500 ml; {D}:Harina=; {H}:Mantequilla=40 g; {H}:Queso rallado=150 g"),

    # ---------- Platos de comida (fines de semana) ----------
    ("Lentejas estofadas con verduras", "legumbre verdura", "comida",
     f"{D}:Lentejas=400 g; {F}:Zanahoria=2; {F}:Patata=2; {F}:Pimiento verde=1; {F}:Cebolla=1; {D}:Pimentón dulce="),
    ("Garbanzos con espinacas y huevo", "legumbre verdura huevo", "comida",
     f"{D}:Garbanzos cocidos=2 botes; {CO}:Espinacas=400 g; {H}:Huevos=4; {D}:Comino=; {D}:Ajo=2 dientes"),
    ("Cocido madrileño", "legumbre carne verdura", "comida",
     f"{D}:Garbanzos=400 g; {C}:Morcillo de ternera=400 g; {C}:Gallina o pollo=1/2; {C}:Chorizo=1; {C}:Tocino=100 g; {F}:Repollo=1/2; {F}:Zanahoria=2; {F}:Patata=4; {D}:Fideos finos=150 g"),
    ("Alubias blancas con verduras", "legumbre verdura", "comida",
     f"{D}:Alubias blancas=400 g; {F}:Puerro=1; {F}:Zanahoria=2; {F}:Pimiento rojo=1; {F}:Cebolla=1"),
    ("Paella mixta", "arroz pescado carne verdura", "comida",
     f"{D}:Arroz bomba=400 g; {C}:Pollo troceado=500 g; {P}:Calamares=300 g; {P}:Gambas=300 g; {F}:Pimiento rojo=1; {F}:Judías verdes=200 g; {D}:Tomate triturado=200 g; {D}:Azafrán="),
    ("Arroz con pollo y verduras", "arroz carne verdura", "comida",
     f"{D}:Arroz=400 g; {C}:Muslos de pollo=6; {F}:Pimiento rojo=1; {F}:Guisantes=200 g; {F}:Cebolla=1"),
    ("Macarrones con tomate y carne picada", "pasta carne", "comida",
     f"{D}:Macarrones=400 g; {C}:Carne picada mixta=400 g; {D}:Tomate triturado=800 g; {F}:Cebolla=1; {H}:Queso rallado=100 g"),
    ("Espaguetis con salmón y nata", "pasta pescado lacteo", "comida",
     f"{D}:Espaguetis=400 g; {P}:Salmón fresco=300 g; {H}:Nata para cocinar=200 ml; {F}:Cebolla=1"),
    ("Lasaña de verduras y carne", "pasta carne verdura lacteo", "comida",
     f"{D}:Placas de lasaña=12; {C}:Carne picada de ternera=400 g; {F}:Calabacín=1; {F}:Berenjena=1; {D}:Tomate triturado=400 g; {H}:Leche=500 ml; {H}:Queso rallado=150 g"),
    ("Pollo asado con patatas panadera", "carne patata verdura", "comida",
     f"{C}:Pollo entero=1; {F}:Patata=1 kg; {F}:Cebolla=2; {F}:Pimiento verde=1; {F}:Limón=1"),
    ("Filetes de ternera con ensalada y patatas", "carne patata verdura", "comida",
     f"{C}:Filetes de ternera=600 g; {F}:Patata=800 g; {F}:Lechuga=1; {F}:Tomate=2"),
    ("Merluza en salsa verde con patatas", "pescado patata verdura", "comida",
     f"{P}:Merluza en rodajas=800 g; {F}:Patata=600 g; {P}:Almejas=250 g; {F}:Perejil=1 manojo; {D}:Harina=; {D}:Ajo=3 dientes"),
    ("Dorada a la sal con verduras asadas", "pescado verdura", "comida",
     f"{P}:Doradas=2; {D}:Sal gruesa=2 kg; {F}:Pimiento rojo=1; {F}:Berenjena=1; {F}:Cebolla=1"),
    ("Fideuá de marisco", "pasta pescado", "comida",
     f"{D}:Fideos gruesos=400 g; {P}:Gambas=300 g; {P}:Sepia=300 g; {P}:Mejillones=500 g; {D}:Tomate triturado=200 g; {D}:Alioli="),
    ("Hamburguesas caseras con ensalada", "carne verdura", "comida",
     f"{C}:Carne picada de ternera=600 g; {PA}:Pan de hamburguesa=4; {F}:Lechuga=1; {F}:Tomate=2; {H}:Queso en lonchas=4"),
    ("Pisto con huevo y arroz blanco", "verdura huevo arroz", "comida",
     f"{F}:Calabacín=2; {F}:Pimiento rojo=1; {F}:Pimiento verde=1; {F}:Cebolla=1; {D}:Tomate triturado=400 g; {H}:Huevos=4; {D}:Arroz=300 g"),
    ("Ensaladilla rusa y filetes de pollo empanados", "patata huevo carne verdura", "comida",
     f"{F}:Patata=800 g; {F}:Zanahoria=2; {CO}:Guisantes=150 g; {H}:Huevos=4; {D}:Atún en lata=2 latas; {D}:Mayonesa=; {C}:Pechuga de pollo=500 g; {D}:Pan rallado="),
    ("Lentejas con arroz", "legumbre arroz verdura", "comida",
     f"{D}:Lentejas=300 g; {D}:Arroz=150 g; {F}:Cebolla=1; {F}:Zanahoria=2; {F}:Pimiento verde=1"),
    ("Salmón al horno con patatas y brócoli", "pescado patata verdura", "comida",
     f"{P}:Salmón en lomos=4; {F}:Patata=600 g; {F}:Brócoli=1"),

    # ---------- Favoritos de los niños (verdura integrada en el plato) ----------
    ("Croquetas caseras de pollo con crema de calabaza", "carne verdura lacteo", "cena",
     f"{C}:Pechuga de pollo=300 g; {H}:Leche=750 ml; {D}:Harina=; {H}:Huevos=2; {D}:Pan rallado=; {F}:Calabaza=600 g; {F}:Zanahoria=2"),
    ("Nuggets caseros de pollo con puré de patata y zanahoria", "carne patata verdura", "cena",
     f"{C}:Pechuga de pollo=600 g; {H}:Huevos=2; {D}:Copos de maíz o pan rallado=; {F}:Patata=600 g; {F}:Zanahoria=3; {H}:Leche=200 ml"),
    ("Merluza rebozada con patatas al horno", "pescado patata", "cena",
     f"{P}:Merluza en filetes sin espinas=600 g; {H}:Huevos=2; {D}:Harina=; {F}:Patata=800 g; {F}:Limón=1"),
    ("Palitos de pescado caseros con puré de calabacín", "pescado verdura", "cena",
     f"{P}:Merluza o abadejo sin espinas=600 g; {H}:Huevos=2; {D}:Pan rallado=; {F}:Calabacín=3; {F}:Patata=1; {H}:Quesitos=4"),
    ("Hamburguesitas de pollo y calabacín con patatas", "carne verdura patata", "cena",
     f"{C}:Carne picada de pollo=500 g; {F}:Calabacín=1; {H}:Huevos=1; {D}:Pan rallado=; {F}:Patata=600 g"),
    ("Tortilla de patata y calabacín", "huevo patata verdura", "cena",
     f"{H}:Huevos=8; {F}:Patata=600 g; {F}:Calabacín=1; {F}:Cebolla=1"),
    ("Mini pizzas caseras de jamón, queso y verduras", "carne lacteo verdura", "cena",
     f"{PA}:Masa de pizza o pan de pita=4; {D}:Tomate triturado=200 g; {C}:Jamón cocido=150 g; {H}:Mozzarella=200 g; {F}:Champiñones=150 g; {F}:Pimiento rojo=1"),
    ("Quesadillas de pollo con pimiento y maíz", "carne verdura lacteo", "cena",
     f"{PA}:Tortillas de trigo=8; {C}:Pechuga de pollo=400 g; {F}:Pimiento rojo=1; {D}:Maíz dulce=1 lata; {H}:Queso rallado=200 g"),
    ("Empanadillas de atún y tomate con ensalada", "pescado verdura", "cena",
     f"{PA}:Obleas de empanadilla=16; {D}:Atún en lata=3 latas; {D}:Tomate frito=200 g; {H}:Huevos=2; {F}:Lechuga=1"),
    ("Sándwich caliente de pavo y queso con crema de verduras", "carne lacteo verdura", "cena",
     f"{PA}:Pan de molde=1 paquete; {C}:Pavo en lonchas=200 g; {H}:Queso en lonchas=200 g; {F}:Calabacín=2; {F}:Zanahoria=2; {F}:Puerro=1"),
    ("Crema suave de calabaza con huevo duro y picatostes", "verdura huevo", "cena",
     f"{F}:Calabaza=800 g; {F}:Zanahoria=2; {F}:Patata=1; {H}:Huevos=4; {PA}:Pan=1 barra"),
    ("Albóndigas de merluza en salsa de tomate con arroz", "pescado arroz verdura", "cena",
     f"{P}:Merluza sin espinas=500 g; {H}:Huevos=1; {D}:Pan rallado=; {D}:Tomate triturado=400 g; {D}:Arroz=200 g"),
    ("Espaguetis con atún y tomate", "pasta pescado verdura", "comida",
     f"{D}:Espaguetis=400 g; {D}:Atún en lata=3 latas; {D}:Tomate triturado=600 g; {F}:Cebolla=1"),
    ("Arroz a la cubana con huevo", "arroz huevo verdura", "comida",
     f"{D}:Arroz=350 g; {H}:Huevos=4; {D}:Tomate frito=400 g"),
    ("Macarrones con boloñesa de verduras", "pasta carne verdura", "comida",
     f"{D}:Macarrones=400 g; {C}:Carne picada mixta=400 g; {F}:Zanahoria=2; {F}:Calabacín=1; {D}:Tomate triturado=800 g; {H}:Queso rallado=100 g"),
    ("Lentejas con chorizo y verduras trituradas", "legumbre carne verdura", "comida",
     f"{D}:Lentejas=400 g; {C}:Chorizo=1; {F}:Zanahoria=2; {F}:Pimiento verde=1; {F}:Cebolla=1; {F}:Patata=2"),
    ("Pollo al horno con patatas y salsa de manzana", "carne patata fruta", "comida",
     f"{C}:Muslos de pollo=8; {F}:Patata=1 kg; {F}:Manzana=2; {F}:Cebolla=1"),
]

# Qué tal suelen gustar a los niños (1 = plato de adulto, 2 = normal, 3 = favorito). Por defecto 2.
KID_LOW = {
    "Ensalada completa con queso fresco y nueces", "Verduras al horno con yogur y hummus", "Coliflor gratinada con bechamel",
    "Sardinas al horno con ensalada de tomate", "Dorada a la sal con verduras asadas", "Brochetas de rape y langostinos con pisto",
    "Fideuá de marisco", "Merluza en salsa verde con patatas", "Gallo a la plancha con puré de verduras",
    "Crema de calabacín y bacalao en papillote", "Sopa de pescado con fideos", "Huevos al plato con pisto",
}
KID_HIGH = {
    "Tortilla de patata con pimientos asados", "Pizza casera de verduras y huevo", "Wraps de pollo y verduras",
    "Hamburguesas de atún con verduras al horno", "Pescadilla rebozada con ensalada", "Albóndigas de pollo en salsa de tomate con verduras",
    "Macarrones con tomate y carne picada", "Lasaña de verduras y carne", "Pollo asado con patatas panadera",
    "Hamburguesas caseras con ensalada", "Ensaladilla rusa y filetes de pollo empanados", "Crema de calabacín con quesitos y picatostes",
    "Croquetas caseras de pollo con crema de calabaza", "Nuggets caseros de pollo con puré de patata y zanahoria",
    "Merluza rebozada con patatas al horno", "Palitos de pescado caseros con puré de calabacín",
    "Hamburguesitas de pollo y calabacín con patatas", "Tortilla de patata y calabacín", "Mini pizzas caseras de jamón, queso y verduras",
    "Quesadillas de pollo con pimiento y maíz", "Empanadillas de atún y tomate con ensalada",
    "Sándwich caliente de pavo y queso con crema de verduras", "Espaguetis con atún y tomate", "Arroz a la cubana con huevo",
    "Macarrones con boloñesa de verduras", "Albóndigas de merluza en salsa de tomate con arroz", "Sopa de pollo con verduras y estrellitas",
}


def _parse_ings(s: str):
    out = []
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        section, rest = part.split(":", 1)
        name, _, qty = rest.partition("=")
        out.append({"name": name.strip(), "qty": qty.strip(), "section": section.strip()})
    return out


RECIPES = [
    {"name": n, "groups": g.split(), "when": w, "ingredients": _parse_ings(i),
     "kid": 1 if n in KID_LOW else 3 if n in KID_HIGH else 2}
    for n, g, w, i in _RAW
]
BY_NAME = {r["name"].lower(): r for r in RECIPES}


def find(name: str):
    return BY_NAME.get((name or "").strip().lower())
