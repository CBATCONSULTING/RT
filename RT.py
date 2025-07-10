import streamlit as st
import matplotlib.pyplot as plt
import math
import datetime
import tempfile
import os
import requests
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from fpdf import FPDF

VERSION = "1007.01"
METREURS = ["Jean-Baptiste", "Julie", "Paul"]
EMAILS = [
    "support@challengebat.fr",
    "stevens@challengebat.fr",
    "autre..."
]
LOGO_URL = "https://static.wixstatic.com/media/9c09bd_194e3777ea134f9a99bc086cb7173909~mv2.png"

def get_smtp_password():
    url = "https://9c09bdff-4d5d-401b-9aa7-6e6874bb2cf7.usrfiles.com/ugd/9c09bd_f611b6e2d24e451080d57fe23b426b75.txt"
    resp = requests.get(url)
    return resp.text.strip()

def envoyer_gmail(destinataire, sujet, html_message, pdf_path, nom_pdf):
    smtp_user = "cbatconsulting@gmail.com"
    smtp_pass = get_smtp_password()
    expediteur = formataddr(("CHALLENGE BAT", smtp_user))
    msg = EmailMessage()
    msg["From"] = expediteur
    msg["To"] = destinataire
    msg["Subject"] = sujet
    msg.set_content("Relevé technique Challenge BAT en pièce jointe.")
    msg.add_alternative(html_message, subtype="html")
    with open(pdf_path, "rb") as pdf_file:
        pdf_data = pdf_file.read()
        msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=nom_pdf)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        return True, "Email envoyé"
    except Exception as e:
        return False, f"Erreur lors de l'envoi : {e}"

st.set_page_config(page_title="Relevé technique", layout="centered")
st.title("📏 Relevé technique de pièce (angles intérieurs et extérieurs)")
st.caption(f"Version : {VERSION}")

client = st.text_input("Nom du client")
metreur = st.selectbox("Sélectionnez votre prénom", METREURS)

email_choix = st.selectbox("Adresse email destinataire", EMAILS)
if email_choix == "autre...":
    email_dest = st.text_input("Saisissez une autre adresse email")
else:
    email_dest = email_choix

now = datetime.datetime.now()
date_str = now.strftime("%d-%m-%Y_%H-%M")
nom_pdf = f"RT_{client or 'client'}_{date_str}.pdf"

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
    c_haut_sol = st.number_input("Hauteur depuis le sol (cm)", min_value=0.0, max_value=500.0, value=10.0, key=f"chaut_sol_{i}")
    c_haut = st.number_input("Hauteur de la contrainte (cm)", min_value=1.0, max_value=500.0, value=50.0, key=f"chaut_{i}")
    contraintes.append({
        "type": c_type if c_type != "Autre (Préciser)" else c_type_precise,
        "mur": c_mur,
        "pos": c_pos,
        "larg": c_larg,
        "epais": c_epais,
        "haut_sol": c_haut_sol,
        "haut": c_haut
    })

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
tableau_cloisons = st.radio("Y a-t-il des cloisons à traverser ?", ("Pas de retirage nécessaire" , "Non", "Oui"))
tableau_place_deux = st.radio("Y a-t-il de la place pour un second coffret si nécessaire ?", ("Pas de retirage nécessaire" , "Non", "Oui"))

commentaire = st.text_area("Commentaire (optionnel)", "")

# ========== Générer le graphique du plan ==========

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

for i in range(nb_murs):
    x1, y1 = points[i]
    x2, y2 = points[i+1]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    norm = math.hypot(dx, dy)
    if norm == 0:
        perp_x, perp_y = 0, 0
    else:
        perp_x = -dy / norm
        perp_y = dx / norm
    decal = 8
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

# Sauvegarde temporaire de l'image du schéma
with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
    fig.savefig(tmpfile.name, format="png", bbox_inches='tight')
    image_path = tmpfile.name

def make_pdf_message(
    client, metreur, hsp, murs, angles, exterieurs, contraintes, commentaire, now,
    evac_mur, evac_pos, evac_largeur, evac_epaisseur, evac_hauteur,
    tableau_emplacement, tableau_emplacement_precise, tableau_developpe, tableau_cloisons, tableau_place_deux,
    email_dest, version, image_path
):
    pdf = FPDF()
    pdf.add_page()
    # Logo
    try:
        pdf.image(LOGO_URL, x=80, w=50)
        pdf.ln(2)
    except Exception:
        pass

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "RELEVÉ TECHNIQUE", ln=True, align="C")
    pdf.set_font("Arial", "", 13)
    pdf.cell(0, 8, f"Challenge BAT - {now.strftime('%d/%m/%Y')} (V{version})", ln=True, align="C")
    pdf.ln(2)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)

    # --- Bloc Identité ---
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 10, "Informations du relevé", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Nom du client : {client}", ln=True)
    pdf.cell(0, 8, f"Prénom du métreur : {metreur}", ln=True)
    pdf.cell(0, 8, f"Adresse email destinataire : {email_dest}", ln=True)
    pdf.cell(0, 8, f"Date : {now.strftime('%d/%m/%Y à %Hh%M')}", ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Résumé des murs", ln=True)
    pdf.set_font("Arial", "", 11)
    for i, l in enumerate(murs):
        a = angles[i] if i < len(angles) else "-"
        pdf.cell(0, 7, f"Mur {chr(65+i)} : {l:.0f} cm, angle intérieur {a}°", ln=1)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Hauteur sous plafond (HSP)", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"{hsp} cm", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Évacuation finale", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Mur : {evac_mur}, Position gauche : {evac_pos} cm, Largeur : {evac_largeur} cm, "
                   f"Épaisseur : {evac_epaisseur} cm, Hauteur sol : {evac_hauteur} cm", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Contraintes", ln=True)
    pdf.set_font("Arial", "", 11)
    if contraintes:
        for i, c in enumerate(contraintes, 1):
            pdf.cell(0, 7, f"{i:02d}. {c.get('type', '-')}"
                           f" - Mur {c.get('mur', '-')}"
                           f" | Pos : {c.get('pos', '-')} cm"
                           f" | Larg : {c.get('larg', '-')} cm"
                           f" | Epais : {c.get('epais', '-')} cm"
                           f" | Haut. sol : {c.get('haut_sol', '-')} cm"
                           f" | Haut. contrainte : {c.get('haut', '-')} cm", ln=1)
    else:
        pdf.cell(0, 7, "Aucune contrainte renseignée.", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Emplacement du tableau de répartition", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Emplacement : {tableau_emplacement} {tableau_emplacement_precise}", ln=True)
    pdf.cell(0, 7, f"Développé linéaire : {tableau_developpe} m", ln=True)
    pdf.cell(0, 7, f"Cloisons à traverser : {tableau_cloisons}", ln=True)
    pdf.cell(0, 7, f"Place pour second coffret : {tableau_place_deux}", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Commentaire", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 7, commentaire or "-")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Schéma du relevé technique", ln=True)
    try:
        pdf.image(image_path, x=20, w=170)
    except Exception:
        pass
    return pdf.output(dest='S').encode('latin1')

if st.button("Envoyer le relevé par email"):
    if not client or not metreur or not email_dest:
        st.error("Veuillez remplir tous les champs obligatoires.")
    else:
        pdf_bytes = make_pdf_message(
            client, metreur, hsp, longueurs, angles, exterieurs, contraintes, commentaire, now,
            evac_mur, evac_pos, evac_largeur, evac_epaisseur, evac_hauteur,
            tableau_emplacement, tableau_emplacement_precise, tableau_developpe, tableau_cloisons, tableau_place_deux,
            email_dest, VERSION, image_path
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(pdf_bytes)
            pdf_path = f.name
        sujet = f"RELEVÉ TECHNIQUE - {client} - {now.strftime('%d/%m/%Y %Hh%M')}"
        html_message = f"""
        <p>Bonjour,<br>Votre relevé technique est en pièce jointe.<br>
        <b>Nom du client :</b> {client}<br>
        <b>Métreur :</b> {metreur}</p>
        """
        ok, msg = envoyer_gmail(email_dest, sujet, html_message, pdf_path, nom_pdf)
        if ok:
            st.success("Email envoyé !")
            st.download_button("Télécharger le PDF", pdf_bytes, file_name=nom_pdf, mime="application/pdf")
        else:
            st.error(msg)
        os.unlink(pdf_path)
        os.unlink(image_path)
