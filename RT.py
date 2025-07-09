import streamlit as st
import matplotlib.pyplot as plt
import math
from fpdf import FPDF
from io import BytesIO
import datetime
import tempfile
import os

VERSION = "1972"  # Modifie à chaque nouvelle version

st.set_page_config(page_title="Relevé technique", layout="centered")

st.title("📏 Relevé technique de pièce (angles intérieurs et extérieurs)")
st.caption(f"Version : {VERSION}")

client = st.text_input("Nom du client")
email_dest = st.text_input("Adresse email destinataire (optionnel)")

now = datetime.datetime.now()
date_str = now.strftime("%d-%m-%Y_%H-%M")  # Format français pour nom du fichier PDF

st.markdown("""
- Départ en bas à droite, premier mur vers la gauche.
- <span style="color:green">**Angle intérieur**</span> (case décochée), <span style="color:red">**extérieur**</span> (case cochée).
""", unsafe_allow_html=True)

nb_murs = st.number_input("Nombre de murs à tracer", min_value=3, max_value=20, value=4, step=1)

longueurs = []
angles = []
exterieurs = []

for i in range(nb_murs):
    cols = st.columns([1,1,1])
    longueur = cols[0].number_input(f"L{i+1} (cm)", min_value=1.0, max_value=10000.0, value=100.0, step=1.0, key=f"l{i}")
    longueurs.append(longueur)
    if i < nb_murs - 1:
        angle = cols[1].number_input(f"A{i+1} (°)", min_value=1.0, max_value=359.9, value=90.0, step=0.1, key=f"a{i}")
        angles.append(angle)
        ext = cols[2].checkbox("Extérieur", key=f"ext{i}")
        exterieurs.append(ext)

# Calcul des points
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
for i in range(1, len(points)):
    x1, y1 = points[i-1]
    x2, y2 = points[i]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx, my, f"{longueurs[i-1]:.0f} cm", fontsize=12, color='red', ha='center', va='bottom',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
for i in range(1, len(points)-1):
    x, y = points[i]
    color = 'red' if exterieurs[i-1] else 'green'
    ax.text(x, y, f"{angles[i-1]:.0f}°", fontsize=11, color=color, ha='left', va='top',
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))
ax.scatter(points[0][0], points[0][1], s=120, color='purple', zorder=5)
ax.text(points[0][0], points[0][1], "Départ", fontsize=13, color='purple', va='bottom', ha='right')
ax.set_title("Relevé technique (intérieur/extérieur)")
ax.axis('equal')
ax.grid(True)
ax.invert_yaxis()
st.pyplot(fig)

# -- Génération PDF --
if st.button("Générer et télécharger le PDF"):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    titre = f"Relevé - {client or 'Client'} - {date_str}"
    pdf.cell(0, 10, titre, 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Nom du client : {client}", 0, 1)
    pdf.cell(0, 10, f"Date : {now.strftime('%d/%m/%Y à %H:%M')}", 0, 1)
    pdf.cell(0, 10, f"Murs saisis : {nb_murs}", 0, 1)
    if email_dest:
        pdf.cell(0, 10, f"Email destinataire : {email_dest}", 0, 1)
    pdf.cell(0, 10, f"Version : {VERSION}", 0, 1)

    # Ajout du schéma (tempfile obligatoire pour FPDF)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        fig.savefig(tmpfile.name, format="png", bbox_inches='tight')
        pdf.image(tmpfile.name, x=10, y=None, w=190)
        image_path = tmpfile.name

    # Ajout du tableau mesures
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 8, "Mur", 1)
    pdf.cell(40, 8, "Longueur (cm)", 1)
    pdf.cell(40, 8, "Angle (°)", 1)
    pdf.cell(40, 8, "Extérieur", 1)
    pdf.ln()
    pdf.set_font("Arial", '', 12)
    for i in range(nb_murs):
        pdf.cell(40, 8, f"L{i+1}", 1)
        pdf.cell(40, 8, f"{longueurs[i]:.0f}", 1)
        if i < nb_murs-1:
            pdf.cell(40, 8, f"{angles[i]:.1f}", 1)
            pdf.cell(40, 8, "Oui" if exterieurs[i] else "Non", 1)
        else:
            pdf.cell(40, 8, "-", 1)
            pdf.cell(40, 8, "-", 1)
        pdf.ln()

    # Export PDF en bytes pour Streamlit (UTF-8 safe)
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    st.download_button(
        label="📥 Télécharger le PDF",
        data=pdf_bytes,
        file_name=f"{client or 'client'}_{date_str}.pdf",
        mime="application/pdf"
    )

    # Nettoyage du fichier temporaire
    os.remove(image_path)
