"""Génère les données fictives du SAV : manuel PX-200, figures, photo client et registre des garanties."""
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SAV = ROOT / "data" / "sav"
FIGURES = SAV / "figures"
IMAGES = SAV / "images"
FIGURES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ---------- 1. Le manuel (une section = un passage) ----------
MANUEL = """# Manuel d'utilisation — Imprimante PX-200

## 1. Présentation du panneau de contrôle
Le panneau de contrôle de la PX-200 comporte un écran LCD, un bouton Marche, un bouton Annuler
et un voyant d'état multicolore. L'écran affiche un pictogramme lorsque l'imprimante a besoin
d'une intervention. La signification de chaque pictogramme est donnée dans la figure 1.

## 2. Voyant d'état et pictogrammes
Voyant vert fixe : l'imprimante est prête.
Voyant vert clignotant : impression ou initialisation en cours, aucune action n'est nécessaire.
Voyant orange clignotant accompagné du pictogramme en forme de goutte : le niveau d'encre d'une
cartouche est bas. L'impression reste possible mais la cartouche doit être remplacée rapidement
(voir section 4 et figure 2).
Voyant rouge fixe accompagné du pictogramme de feuille barrée : bourrage papier
(voir section 5 et figure 3).
Voyant rouge clignotant accompagné du pictogramme triangle : erreur matérielle. Éteignez
l'imprimante, attendez 30 secondes puis rallumez-la. Si l'erreur persiste, contactez le SAV.

## 3. Chargement du papier
Le bac accepte jusqu'à 150 feuilles A4 de 80 g/m². Ajustez les guides latéraux contre la pile
de papier sans la plier. N'ajoutez pas de papier pendant une impression.

## 4. Remplacement d'une cartouche d'encre
Ouvrez le capot avant : le chariot se place automatiquement en position de remplacement.
Appuyez sur la languette de la cartouche vide, retirez-la, puis insérez la cartouche neuve
jusqu'au déclic (figure 2). Refermez le capot : le voyant orange s'éteint après l'initialisation.
Utilisez uniquement des cartouches PX-INK d'origine.

## 5. Résolution d'un bourrage papier
Éteignez l'imprimante. Retirez le bac arrière puis tirez doucement la feuille coincée dans le
sens de défilement du papier, à deux mains (figure 3). Vérifiez qu'aucun morceau de papier ne
reste dans l'imprimante, remettez le bac puis rallumez l'imprimante.

## 6. Entretien
Nettoyez les têtes d'impression depuis le menu Maintenance si les impressions présentent des
traînées. Ne nettoyez jamais l'intérieur de l'imprimante avec un liquide.
"""
(SAV / "manuel_px200.md").write_text(MANUEL, encoding="utf-8")

# ---------- 2. Les figures du manuel ----------
def police(taille):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            pass
    return ImageFont.load_default()

def goutte(d, x, y, couleur):
    d.ellipse([x - 22, y - 5, x + 22, y + 40], fill=couleur)
    d.polygon([(x, y - 40), (x - 20, y + 5), (x + 20, y + 5)], fill=couleur)

def feuille_barree(d, x, y):
    d.rectangle([x - 22, y - 30, x + 22, y + 30], outline="black", width=4)
    d.line([x - 32, y - 38, x + 32, y + 38], fill="red", width=6)

def triangle(d, x, y):
    d.polygon([(x, y - 35), (x - 35, y + 30), (x + 35, y + 30)], outline="black", fill="yellow")
    d.text((x - 5, y - 15), "!", fill="black", font=police(36))

# Figure 1 : tableau des pictogrammes
img = Image.new("RGB", (900, 420), "white")
d = ImageDraw.Draw(img)
d.text((20, 15), "Figure 1 — Pictogrammes du panneau PX-200", fill="black", font=police(28))
lignes = [("Encre faible (voyant orange clignotant)", goutte),
          ("Bourrage papier (voyant rouge fixe)", feuille_barree),
          ("Erreur matérielle (voyant rouge clignotant)", triangle)]
for i, (texte, dessin) in enumerate(lignes):
    y = 120 + i * 105
    if dessin is goutte:
        goutte(d, 80, y, "orange")
    else:
        dessin(d, 80, y)
    d.text((160, y - 15), texte, fill="black", font=police(26))
img.save(FIGURES / "fig1_pictogrammes.png")

# Figure 2 : remplacement de cartouche
img = Image.new("RGB", (700, 400), "white")
d = ImageDraw.Draw(img)
d.text((20, 15), "Figure 2 — Remplacement d'une cartouche", fill="black", font=police(26))
d.rectangle([100, 120, 600, 330], outline="black", width=4)
d.rectangle([260, 160, 360, 290], fill="#3a7bd5")
d.line([310, 110, 310, 160], fill="red", width=6)
d.polygon([(295, 140), (325, 140), (310, 165)], fill="red")
d.text((380, 200), "Insérer jusqu'au déclic", fill="black", font=police(22))
img.save(FIGURES / "fig2_cartouche.png")

# Figure 3 : bourrage papier
img = Image.new("RGB", (700, 400), "white")
d = ImageDraw.Draw(img)
d.text((20, 15), "Figure 3 — Retirer une feuille coincée", fill="black", font=police(26))
d.rectangle([120, 150, 580, 320], outline="black", width=4)
d.rectangle([280, 90, 420, 190], fill="white", outline="black", width=3)
d.line([350, 80, 350, 30], fill="red", width=6)
d.polygon([(335, 50), (365, 50), (350, 25)], fill="red")
d.text((430, 100), "Tirer à deux mains", fill="black", font=police(22))
img.save(FIGURES / "fig3_bourrage.png")

FIGURES_INFO = [
    {"id": "fig1", "fichier": "fig1_pictogrammes.png", "section": "2. Voyant d'état et pictogrammes",
     "legende": "Figure 1 — Pictogrammes du panneau PX-200",
     "description": "Tableau des pictogrammes : goutte orange = encre faible avec voyant orange clignotant ; "
                    "feuille barrée = bourrage papier avec voyant rouge fixe ; triangle jaune avec point "
                    "d'exclamation = erreur matérielle avec voyant rouge clignotant."},
    {"id": "fig2", "fichier": "fig2_cartouche.png", "section": "4. Remplacement d'une cartouche d'encre",
     "legende": "Figure 2 — Remplacement d'une cartouche",
     "description": "Schéma du chariot ouvert : une cartouche bleue est insérée par le haut jusqu'au déclic."},
    {"id": "fig3", "fichier": "fig3_bourrage.png", "section": "5. Résolution d'un bourrage papier",
     "legende": "Figure 3 — Retirer une feuille coincée",
     "description": "Schéma de l'imprimante avec une feuille coincée que l'on tire vers le haut, à deux mains."},
]
(FIGURES / "figures.json").write_text(json.dumps(FIGURES_INFO, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- 3. La photo envoyée par le client (img_px200_01) ----------
img = Image.new("RGB", (640, 420), "#2b2b2b")
d = ImageDraw.Draw(img)
d.rounded_rectangle([60, 60, 580, 300], radius=20, fill="#cfe8d0", outline="black", width=4)
goutte(d, 320, 160, "orange")
d.text((215, 230), "PX-200", fill="black", font=police(34))
d.ellipse([290, 330, 350, 390], fill="orange", outline="white", width=3)   # voyant orange
d.text((370, 345), "voyant", fill="white", font=police(24))
img.save(IMAGES / "img_px200_01.png")

# ---------- 4. Le registre des garanties ----------
with open(SAV / "garanties.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["numero_serie", "modele", "date_achat", "duree_garantie_mois", "client"])
    w.writerow(["PX200-0042", "PX-200", "2025-06-15", "24", "Client A"])
    w.writerow(["PX200-0007", "PX-200", "2023-01-10", "24", "Client B"])
    w.writerow(["PX200-0108", "PX-200", "2026-03-02", "12", "Client C"])

print("Données SAV créées dans", SAV)