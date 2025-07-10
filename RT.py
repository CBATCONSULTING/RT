import streamlit as st
import matplotlib.pyplot as plt
import math
from fpdf import FPDF
import datetime
import tempfile
import os

VERSION = "1972"
METREURS = ["Jean-Baptiste", "Julie", "Paul"]

st.set_page_config(page_title="Relevé technique", layout="centered")
st.title("📏 Relevé technique de pièce (angles intérieurs et extérieurs)")
st.caption(f"Version : {VERSION}")

client = st.text_input("Nom du client")
metreur = st.selectbox("Sélectionnez votre prénom", METREURS)
email_dest = st.text_input("Adresse email destinataire (optionnel)")

now = datetime.datetime.now()
date_str = now.strftime("%d-%m-%Y_%H-%M")

st.markdown("""
- Départ en bas à droite, premier mur vers la gauche.
- <span style="color:green">**Angle intérieur**</span> (case décochée), <span style="color:red">**extérieur**</span> (case cochée).
""", unsafe_allow_html=True)

nb_murs = st.number_input("Nombre de murs à tracer", min_value=3, max_value=20, value=4, step=1)

longueurs = []
angles = []
exterieurs = []

for i in range(nb_murs):
    mur_id = chr(ord('A') + i)
    cols = st.columns([1,1,1])
    longueur = cols[0].number_input(f"Mur {mur_id} (cm)", min_value=1.0, max_value=10000.0, value=100.0, step=1.0, key=f"l{i}")
    longueurs.append(longueur)
    if i < nb_murs - 1:
        angle = cols[1].number_input(f"Angle après {mur_id} (°)", min_value=1.0, max_value=359.9, value=90.0, step=0.1, key=f"a{i}")
        angles.append(angle)
        ext = cols[2].checkbox("Extérieur", key=f"ext{i}")
        exterieurs.append(ext)

# === QUESTIONS SUPPLÉMENTAIRES ===

st.header("Informations complémentaires")

hsp = st.number_input("Hauteur sous plafond (HSP) en cm", min_value=100, max_value=400, value=250, step=1)

st.subheader("Évacuation finale")
mur_choix = [chr(ord('A')+i) for i in range(nb_murs)]
evac_mur = st.selectbox("Mur support de l'évacuation finale", mur_choix)
evac_pos = st.number_input("Position depuis la gauche (cm)", min_value=0.0, max_value=10000.0, value=0.0)
evac_largeur = st.number_input("Largeur (cm)", min_value=1.0, max_value=500.0, value=10.0)
evac_epaisseur = st.number_input("Épaisseur (cm)", min_value=1.0, max_value=200.0, value=5.0)
evac_hauteur = st.number_input("Hauteur depuis le sol (cm)", min_value=0.0, max_value=500.0, value=10.0)

st.subheader("Contraintes")
nb_contraintes = st.number_input("Nombre de contraintes à déclarer", min_value=0, max_value=20, value=0, step=1)

CONTRAINTES_CHOIX = [
    "Porte", "Fenêtre", "Socle", "Coffrage", "Poteau", "Trappe",
    "VMC", "Gaz", "Interrupteur", "Autre (Préciser)"
]
contraintes = []
for i in range(int(nb_contraintes)):
    st.markdown(f"**Contrainte n°{i+1:02d}**")
    c_type = st.selectbox(f"Type de contrainte n°{i+1}", CONTRAINTES_CHOIX, key=f"type_{i}")
    c_type_precise = ""
    if c_type == "Autre (Préciser)":
        c_type_precise = st.text_input(f"Précisez la contrainte n°{i+1}", key=f"precise_{i}")
    c_mur = st.selectbox(f"Mur support", mur_choix, key=f"cmur_{i}")
    c_pos = st.number_input("Position depuis la gauche (cm)", min_value=0.0, max_value=10000.0, value=0.0, key=f"cpos_{i}")
    c_larg = st.number_input("Largeur (cm)", min_value=1.0, max_value=500.0, value=10.0, key=f"clarg_{i}")
    c_epais = st.number_input("Épaisseur (cm)", min_value=1.0, max_value=200.0, value=5.0, key=f"cepais_{i}")
    c_haut = st.number_input("Hauteur depuis le sol (cm)", min_value=0.0, max_value=500.0, value=10.0, key=f"chaut_{i}")
    contraintes.append({
        "type": c_type if c_type != "Autre (Préciser)" else c_type_precise,
        "mur": c_mur,
        "pos": c_pos,
        "larg": c_larg,
        "epais": c_epais,
        "haut": c_haut
    })

# === BLOC TABLEAU ELECTRIQUE ===

st.subheader("Emplacement du tableau de répartition")
tableau_emplacement = st.selectbox(
    "Où est situé le tableau ?",
    ["Cuisine", "Couloir", "Autre"]
)
if tableau_emplacement == "Autre":
    tableau_emplacement_precise = st.text_input("Précisez l'emplacement", "")
else:
    tableau_emplacement_precise = ""

tableau_developpe = st.number_input("Développé linéaire depuis le centre de la cuisine (mètres)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
tableau_cloisons = st.radio("Y a-t-il des cloisons à traverser ?", ("Non", "Oui"))
tableau_place_deux = st.radio("Y a-t-il de la place pour un second coffret si nécessaire ?", ("Non", "Oui"))

commentaire = st.text_area("Commentaire (optionnel)", "")

# === SCHÉMA TECHNIQUE (Lettres décalées) ===

x, y = 0, 0
points = [(x, y)]
direction = 180  # Vers la gauche

for i in range(len(longueurs)):
    rad = math.radians(direction)
    x += longueurs[i] * math.cos(rad)
    y += longueurs[i] * math.sin(rad)
    points.append((x, y))
    if i < len(angles):
        if exterieurs[i]:
            angle_to_turn = -(180 - angles[i])
        else:
            angle_to_turn = 180 - angles[i]
        direction += angle_to_turn

fig, ax = plt.subplots(figsize=(6, 8))
x_coords, y_coords = zip(*points)
ax.plot(x_coords, y_coords, marker='o', color='blue', linewidth=2)

# Dimensions sur chaque mur
for i in range(1, len(points)):
    x1, y1 = points[i-1]
    x2, y2 = points[i]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx, my, f"{longueurs[i-1]:.0f} cm", fontsize=12, color='red', ha='center', va='bottom',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

# Angles aux sommets
for i in range(1, len(points)-1):
    x, y = points[i]
    color = 'red' if exterieurs[i-1] else 'green'
    ax.text(x, y, f"{angles[i-1]:.0f}°", fontsize=11, color=color, ha='left', va='top',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

# Lettres décalées à l'intérieur du polygone
for i in range(nb_murs):
    x1, y1 = points[i]
    x2, y2 = points[i+1]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    norm = math.hypot(dx, dy)
    # Vecteur perpendiculaire, direction vers l'intérieur
    if norm == 0:
        perp_x, perp_y = 0, 0
    else:
        perp_x = -dy / norm
        perp_y = dx / norm
    decal = 8  # Ajuste le décalage ici
    label_x = mx + perp_x * decal
    label_y = my + perp_y * decal
    ax.text(label_x, label_y, chr(ord('A')+i), fontsize=16, color='black', fontweight='bold', ha='center', va='center')

ax.scatter(points[0][0], points[0][1], s=120, color='purple', zorder=5)
ax.text(points[0][0], points[0][1], "Départ", fontsize=13, color='purple', va='bottom', ha='right')
ax.set_title("Relevé technique (intérieur/extérieur)")
ax.axis('equal')
ax.grid(True)
ax.invert_yaxis()
st.pyplot(fig)

# === PDF ===

if st.button("Générer et télécharger le PDF"):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    titre = f"Relevé - {client or 'Client'} - {date_str}"
    pdf.cell(0, 10, titre, 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Nom du client : {client}", 0, 1)
    pdf.cell(0, 10, f"Prénom du métreur : {metreur}", 0, 1)
    pdf.cell(0, 10, f"Date : {now.strftime('%d/%m/%Y à %H:%M')}", 0, 1)
    pdf.cell(0, 10, f"Murs saisis : {nb_murs}", 0, 1)
    pdf.cell(0, 10, f"Hauteur sous plafond : {hsp} cm", 0, 1)
    pdf.cell(0, 10, f"Version : {VERSION}", 0, 1)
    if email_dest:
        pdf.cell(0, 10, f"Email destinataire : {email_dest}", 0, 1)

    # Schéma technique
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        fig.savefig(tmpfile.name, format="png", bbox_inches='tight')
        pdf.image(tmpfile.name, x=10, y=None, w=190)
        image_path = tmpfile.name

    # Tableau murs
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(15, 8, "Mur", 1)
    pdf.cell(35, 8, "Longueur (cm)", 1)
    pdf.cell(35, 8, "Angle (°)", 1)
    pdf.cell(25, 8, "Extérieur", 1)
    pdf.ln()
    pdf.set_font("Arial", '', 12)
    for i in range(nb_murs):
        mur_nom = chr(ord('A')+i)
        pdf.cell(15, 8, f"{mur_nom}", 1)
        pdf.cell(35, 8, f"{longueurs[i]:.0f}", 1)
        if i < nb_murs-1:
            pdf.cell(35, 8, f"{angles[i]:.1f}", 1)
            pdf.cell(25, 8, "Oui" if exterieurs[i] else "Non", 1)
        else:
            pdf.cell(35, 8, "-", 1)
            pdf.cell(25, 8, "-", 1)
        pdf.ln()

    # Infos évacuation
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Evacuation finale :", 0, 1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Mur : {evac_mur}", 0, 1)
    pdf.cell(0, 8, f"Position depuis la gauche : {evac_pos} cm", 0, 1)
    pdf.cell(0, 8, f"Largeur : {evac_largeur} cm", 0, 1)
    pdf.cell(0, 8, f"Epaisseur : {evac_epaisseur} cm", 0, 1)
    pdf.cell(0, 8, f"Hauteur depuis le sol : {evac_hauteur} cm", 0, 1)

    # Bloc tableau de répartition
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "Tableau de répartition :", 0, 1)
    pdf.set_font("Arial", '', 12)
    if tableau_emplacement == "Autre":
        pdf.cell(0, 8, f"Emplacement : {tableau_emplacement_precise}", 0, 1)
    else:
        pdf.cell(0, 8, f"Emplacement : {tableau_emplacement}", 0, 1)
    pdf.cell(0, 8, f"Développé linéaire depuis centre cuisine : {tableau_developpe:.2f} m", 0, 1)
    pdf.cell(0, 8, f"Cloisons à traverser : {tableau_cloisons}", 0, 1)
    pdf.cell(0, 8, f"Place pour second coffret : {tableau_place_deux}", 0, 1)

    # Contraintes
    if contraintes:
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Contraintes :", 0, 1)
        pdf.set_font("Arial", '', 12)
        for idx, c in enumerate(contraintes):
            pdf.cell(0, 8, f"{idx+1:02d}. {c['type']} - Mur {c['mur']} | Pos : {c['pos']} cm | Larg : {c['larg']} cm | Epais : {c['epais']} cm | Haut : {c['haut']} cm", 0, 1)

    # Commentaire
    if commentaire.strip():
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "Commentaire :", 0, 1)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 8, commentaire)

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button(
        label="📥 Télécharger le PDF",
        data=pdf_bytes,
        file_name=f"{client or 'client'}_{date_str}.pdf",
        mime="application/pdf"
    )

    os.remove(image_path)
