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

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from streamlit_image_coordinates import streamlit_image_coordinates
except Exception:
    streamlit_image_coordinates = None

VERSION = "V2.7"
METREURS = ["-- Sélectionnez --", "Jean-Baptiste", "Maxime", "Mohamed", "Autre prénom à saisir"]
SUPPORT_EMAIL = "support@challengebat.fr"
TABLEAU_CHOIX = ["-- Sélectionnez --", "Cuisine", "Couloir", "Autre"]
LOGO_URL = "https://static.wixstatic.com/media/9c09bd_194e3777ea134f9a99bc086cb7173909~mv2.png"
SMTP_USER = "cbatconsulting@gmail.com"
SMTP_PASSWORD_URL = "https://9c09bdff-4d5d-401b-9aa7-6e6874bb2cf7.usrfiles.com/ugd/9c09bd_f611b6e2d24e451080d57fe23b426b75.txt"

st.set_page_config(page_title="Relevé technique", layout="centered")

if "form_submitted" not in st.session_state:
    st.session_state["form_submitted"] = False

# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------
def clean_pdf_text(value):
    """FPDF classique supporte mal certains caractères Unicode."""
    if value is None:
        return ""
    text = str(value)
    replacements = {
        "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...",
        "É": "E", "È": "E", "Ê": "E", "À": "A", "Ç": "C",
        "✅": "OK", "⚠️": "ATTENTION", "📷": "PHOTO", "🔗": "Lien",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def pdf_cell(pdf, h, text, ln=True, bold=False):
    pdf.set_font("Arial", "B" if bold else "", 11)
    pdf.multi_cell(0, h, clean_pdf_text(text))
    if ln:
        pdf.ln(1)


def get_smtp_password():
    # Priorité à Streamlit secrets si configuré : SMTP_PASSWORD = "..."
    try:
        if "SMTP_PASSWORD" in st.secrets:
            return st.secrets["SMTP_PASSWORD"]
    except Exception:
        pass
    # Compatibilité avec l'ancien fonctionnement
    resp = requests.get(SMTP_PASSWORD_URL, timeout=10)
    resp.raise_for_status()
    return resp.text.strip()


def envoyer_gmail(destinataire, sujet, html_message, pdf_path, nom_pdf, cc=None):
    smtp_pass = get_smtp_password()
    expediteur = formataddr(("CHALLENGE BAT", SMTP_USER))
    msg = EmailMessage()
    msg["From"] = expediteur
    msg["To"] = destinataire
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = sujet
    msg.set_content("Releve technique en piece jointe.")
    msg.add_alternative(html_message, subtype="html")
    with open(pdf_path, "rb") as pdf_file:
        pdf_data = pdf_file.read()
        msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=nom_pdf)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SMTP_USER, smtp_pass)
            smtp.send_message(msg)
        return True, "Email envoyé"
    except Exception as e:
        return False, f"Erreur lors de l'envoi : {e}"


def uploaded_image_to_temp(uploaded_file):
    if uploaded_file is None:
        return None
    suffix = os.path.splitext(uploaded_file.name)[1].lower() or ".jpg"
    raw = uploaded_file.getvalue()
    if Image is None:
        if suffix not in [".jpg", ".jpeg", ".png"]:
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(raw)
        tmp.close()
        return tmp.name
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            img = Image.open(uploaded_file)
            img = img.convert("RGB")
            img.thumbnail((1600, 1600))
            img.save(tmp.name, "JPEG", quality=85)
            return tmp.name
    except Exception:
        return None


def render_plan(longueurs, angles, exterieurs):
    x, y = 0, 0
    points = [(x, y)]
    direction = 180  # départ vers la gauche

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
    ax.plot(x_coords, y_coords, marker='o', linewidth=2)

    # Etiquettes séparées volontairement :
    # - la cote du mur est placée au-dessus du segment
    # - la lettre du mur est placée en dessous
    # Les décalages sont exprimés en points d'affichage, pas en cm,
    # donc ils restent lisibles même sur de grandes pièces ou des murs courts.
    for i in range(1, len(points)):
        x1, y1 = points[i-1]
        x2, y2 = points[i]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.annotate(
            f"{longueurs[i-1]:.0f} cm",
            (mx, my),
            textcoords="offset points",
            xytext=(0, 16),
            fontsize=11,
            ha='center',
            va='center',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=2.5),
            zorder=4,
        )

    for i in range(1, len(points)-1):
        x0, y0 = points[i]
        angle_type = "ext" if exterieurs[i-1] else "int"
        ax.annotate(
            f"{angles[i-1]:.0f}° {angle_type}",
            (x0, y0),
            textcoords="offset points",
            xytext=(10, -10),
            fontsize=9,
            ha='left',
            va='center',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=2.0),
            zorder=4,
        )

    for i in range(len(longueurs)):
        x1, y1 = points[i]
        x2, y2 = points[i+1]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.annotate(
            chr(ord('A')+i),
            (mx, my),
            textcoords="offset points",
            xytext=(0, -20),
            fontsize=16,
            fontweight='bold',
            ha='center',
            va='center',
            bbox=dict(facecolor='white', alpha=0.95, edgecolor='none', pad=2.5),
            zorder=5,
        )

    ax.scatter(points[0][0], points[0][1], s=120, zorder=5)
    ax.text(points[0][0], points[0][1], "Départ", fontsize=12, va='bottom', ha='right')
    ax.set_title("Plan simplifié du relevé")
    ax.axis('equal')
    ax.grid(True)
    ax.invert_yaxis()
    return fig



def euclidean_distance(p1, p2):
    return math.hypot(float(p2["x"]) - float(p1["x"]), float(p2["y"]) - float(p1["y"]))


def round_cm(value):
    try:
        return round(float(value), 1)
    except Exception:
        return 0.0


def draw_measure_points(display_img, points, labels=None):
    """Retourne une copie annotée de l'image affichée."""
    if Image is None or ImageDraw is None:
        return display_img
    img = display_img.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    labels = labels or []
    # Couleurs volontairement simples, la lisibilité prime.
    for idx, pt in enumerate(points):
        x, y = int(pt["x"]), int(pt["y"])
        r = 7
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 0, 0), outline=(255, 255, 255), width=2)
        txt = str(idx + 1)
        if idx < len(labels):
            txt = f"{idx + 1}"
        draw.rectangle((x+9, y-11, x+31, y+11), fill=(255, 255, 255), outline=(255, 0, 0))
        draw.text((x+14, y-8), txt, fill=(0, 0, 0))
    return img


def save_pil_temp_jpg(img, suffix=".jpg"):
    if Image is None or img is None:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    img.convert("RGB").save(tmp.name, "JPEG", quality=88)
    return tmp.name


def photo_measurement_assistant(uploaded_file, prefix):
    """
    Petit module de mesure assistée par clics.
    Hypothèse volontairement simple : photo prise le plus possible de face.
    Les distances sont estimées à partir d'un repère connu visible sur la photo.
    """
    result = {
        "complete": False,
        "known_cm": 0.0,
        "scale_px_per_cm": 0.0,
        "pos": 0.0,
        "larg": 0.0,
        "haut_sol": 0.0,
        "haut": 0.0,
        "annotated_path": None,
        "points_count": 0,
    }

    if uploaded_file is None:
        st.info("Ajoutez une photo pour activer le repérage assisté.")
        return result

    if Image is None:
        st.warning("Le module image n'est pas disponible. Vérifiez que Pillow est bien installé.")
        return result

    if streamlit_image_coordinates is None:
        st.warning("Le module de clic sur image n'est pas disponible. Vérifiez que `streamlit-image-coordinates` est bien présent dans requirements.txt.")
        return result

    st.markdown("##### Repérage assisté sur photo")
    st.caption("Prenez la photo le plus possible de face. Le calcul reste une aide terrain : le technicien peut corriger ensuite si besoin.")

    ref_type = st.selectbox(
        "Repère utilisé pour l'échelle",
        ["Feuille A4 - grand côté 29,7 cm", "Feuille A4 - petit côté 21 cm", "Mètre / distance connue", "Autre distance connue"],
        key=f"{prefix}_ref_type",
    )
    default_known = 29.7
    if "petit côté" in ref_type:
        default_known = 21.0
    elif "Mètre" in ref_type:
        default_known = 100.0
    known_cm = st.number_input(
        "Longueur réelle du repère visible (cm)",
        min_value=1.0,
        max_value=1000.0,
        value=float(default_known),
        step=0.1,
        key=f"{prefix}_known_cm",
    )
    result["known_cm"] = known_cm

    steps = [
        "Début du repère connu",
        "Fin du repère connu",
        "Bord gauche du mur / origine 0",
        "Bord gauche de la contrainte",
        "Bord droit de la contrainte",
        "Niveau du sol",
        "Bas de la contrainte",
        "Haut de la contrainte",
    ]

    points_key = f"{prefix}_measure_points"
    last_key = f"{prefix}_last_click"
    if points_key not in st.session_state:
        st.session_state[points_key] = []
    if last_key not in st.session_state:
        st.session_state[last_key] = None

    cols_reset = st.columns([1, 2])
    if cols_reset[0].button("Réinitialiser les points", key=f"{prefix}_reset_points"):
        st.session_state[points_key] = []
        st.session_state[last_key] = None
        st.rerun()

    points = st.session_state[points_key]
    result["points_count"] = len(points)
    if len(points) < len(steps):
        st.info(f"Cliquez le point {len(points)+1}/8 : {steps[len(points)]}")
    else:
        st.success("Tous les points nécessaires sont placés.")

    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file).convert("RGB")
    except Exception:
        st.warning("Impossible de lire cette photo.")
        return result

    display_img = img.copy()
    display_img.thumbnail((760, 760))
    annotated = draw_measure_points(display_img, points, steps)

    coords = streamlit_image_coordinates(annotated, key=f"{prefix}_coords")
    if coords and len(points) < len(steps):
        click = {"x": int(coords["x"]), "y": int(coords["y"])}
        if click != st.session_state[last_key]:
            points.append(click)
            st.session_state[points_key] = points
            st.session_state[last_key] = click
            st.rerun()

    if points:
        st.caption("Points posés : " + " | ".join([f"{i+1}. {steps[i]}" for i in range(len(points))]))

    if len(points) >= 2:
        ref_px = euclidean_distance(points[0], points[1])
        if ref_px > 0 and known_cm > 0:
            scale = ref_px / known_cm
            result["scale_px_per_cm"] = scale
            st.caption(f"Échelle calculée : {scale:.2f} px/cm")

    if len(points) >= 8 and result["scale_px_per_cm"] > 0:
        scale = result["scale_px_per_cm"]
        p_ref1, p_ref2, p_origin, p_left, p_right, p_floor, p_bottom, p_top = points[:8]
        result["pos"] = round_cm(abs(float(p_left["x"]) - float(p_origin["x"])) / scale)
        result["larg"] = round_cm(abs(float(p_right["x"]) - float(p_left["x"])) / scale)
        result["haut_sol"] = round_cm(abs(float(p_floor["y"]) - float(p_bottom["y"])) / scale)
        result["haut"] = round_cm(abs(float(p_bottom["y"]) - float(p_top["y"])) / scale)
        result["complete"] = True
        annotated_final = draw_measure_points(display_img, points, steps)
        result["annotated_path"] = save_pil_temp_jpg(annotated_final)
        st.success(
            f"Estimation : position {result['pos']} cm | largeur {result['larg']} cm | "
            f"hauteur depuis sol {result['haut_sol']} cm | hauteur {result['haut']} cm"
        )

    return result

def make_pdf_message(data, image_path, photo_paths):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    try:
        pdf.image(LOGO_URL, x=82, w=46)
        pdf.ln(2)
    except Exception:
        pass

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean_pdf_text("RELEVÉ TECHNIQUE CUISINE"), ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, clean_pdf_text(f"Challenge BAT - {data['now'].strftime('%d/%m/%Y à %Hh%M')} - {VERSION}"), ln=True, align="C")
    pdf.ln(3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf_cell(pdf, 7, "1. Informations générales", bold=True)
    pdf_cell(pdf, 6, f"Client : {data['client']}")
    pdf_cell(pdf, 6, f"Métreur : {data['metreur']}")
    pdf_cell(pdf, 6, f"Destinataire : {data['email_dest']}")
    if data.get('email_cc'):
        pdf_cell(pdf, 6, f"Copie : {data['email_cc']}")
    pdf_cell(pdf, 6, f"Type de pièce : {data['type_piece']}")
    pdf_cell(pdf, 6, f"Hauteur sous plafond : {data['hsp']} cm")
    pdf_cell(pdf, 6, f"Terre : {data['valeur_terre']}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "2. Murs relevés", bold=True)
    for i, longueur in enumerate(data['longueurs']):
        mur = chr(ord('A') + i)
        angle_txt = ""
        if i < len(data['angles']):
            angle_txt = f" - angle après mur : {data['angles'][i]}° {'extérieur' if data['exterieurs'][i] else 'intérieur'}"
        pdf_cell(pdf, 6, f"Mur {mur} : {longueur} cm{angle_txt}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "3. Évacuation finale", bold=True)
    pdf_cell(pdf, 6, f"Mur : {data['evac']['mur']}")
    pdf_cell(pdf, 6, f"Position depuis la gauche : {data['evac']['pos']} cm")
    pdf_cell(pdf, 6, f"Hauteur depuis le sol : {data['evac']['hauteur']} cm")
    pdf_cell(pdf, 6, f"Largeur : {data['evac']['largeur']} cm - Épaisseur : {data['evac']['epaisseur']} cm")
    pdf_cell(pdf, 6, f"Photo : {data['evac']['photo_nom'] or 'Non jointe'}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "4. Contraintes par mur", bold=True)
    if data['contraintes']:
        for idx, c in enumerate(data['contraintes'], 1):
            pdf_cell(pdf, 6, f"{idx:02d}. {c['type']} - Mur {c['mur']}", bold=True)
            pdf_cell(pdf, 6, f"Mode : {c['mode']}")
            if c['mode'].startswith("Mesure"):
                pdf_cell(pdf, 6, f"Position gauche : {c['pos']} cm | Largeur : {c['larg']} cm | Hauteur sol : {c['haut_sol']} cm | Hauteur : {c['haut']} cm | Épaisseur : {c['epais']} cm")
            else:
                pdf_cell(pdf, 6, f"Référence photo : {c['reference']}")
                pdf_cell(pdf, 6, f"Mesure connue : {c['mesure_connue']} cm | Commentaire repère : {c['commentaire_photo'] or '-'}")
                if c.get('calc_complete'):
                    pdf_cell(pdf, 6, f"Estimation depuis photo : Pos gauche {c.get('pos', 0)} cm | Larg {c.get('larg', 0)} cm | Haut. sol {c.get('haut_sol', 0)} cm | Haut {c.get('haut', 0)} cm | Epais {c.get('epais', 0)} cm")
                else:
                    pdf_cell(pdf, 6, "Estimation depuis photo : non complète / non utilisée")
            if c.get('commentaire'):
                pdf_cell(pdf, 6, f"Commentaire : {c['commentaire']}")
            pdf_cell(pdf, 6, f"Photo : {c['photo_nom'] or 'Non jointe'}")
    else:
        pdf_cell(pdf, 6, "Aucune contrainte complémentaire déclarée.")
    pdf.ln(2)

    pdf_cell(pdf, 7, "5. Tableau de répartition", bold=True)
    pdf_cell(pdf, 6, f"Emplacement : {data['tableau_emplacement']} {data['tableau_emplacement_precise']}")
    pdf_cell(pdf, 6, f"Développé linéaire depuis le centre cuisine : {data['tableau_developpe']} m")
    pdf_cell(pdf, 6, f"Cloisons à traverser : {data['tableau_cloisons']}")
    pdf_cell(pdf, 6, f"Place pour second coffret : {data['tableau_place_deux']}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "6. Photos de contrôle", bold=True)
    for label, checked in data['photos_checked'].items():
        pdf_cell(pdf, 6, f"{'OK' if checked else 'NON'} - {label}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "7. TVA réduite", bold=True)
    pdf_cell(pdf, 6, f"Éligibilité : {data['tva_reduite']}")
    if data['tva_reduite'] == "Oui":
        pdf_cell(pdf, 6, f"Attestation signée : {data['attestation_signee']}")
        if data.get('raison_non_signature'):
            pdf_cell(pdf, 6, f"Raison : {data['raison_non_signature']} {data.get('raison_autre_detail','')}")
    else:
        pdf_cell(pdf, 6, f"Justification : {data['justif_non']}")
    pdf.ln(2)

    pdf_cell(pdf, 7, "8. Commentaire général", bold=True)
    pdf_cell(pdf, 6, data['commentaire'] or "-")

    if data['alertes']:
        pdf.ln(2)
        pdf_cell(pdf, 7, "Alertes automatiques", bold=True)
        for alerte in data['alertes']:
            pdf_cell(pdf, 6, f"- {alerte}")

    pdf.add_page()
    pdf_cell(pdf, 7, "Schéma du relevé", bold=True)
    try:
        pdf.image(image_path, x=15, w=180)
    except Exception:
        pdf_cell(pdf, 6, "Schéma non disponible.")

    # Ajout des photos utiles dans le PDF, si compatibles
    added_title = False
    for label, path in photo_paths:
        if not path or not os.path.exists(path):
            continue
        if not added_title:
            pdf.add_page()
            pdf_cell(pdf, 7, "Photos jointes", bold=True)
            added_title = True
        try:
            if pdf.get_y() > 210:
                pdf.add_page()
            pdf_cell(pdf, 6, label, bold=True)
            pdf.image(path, x=15, w=180)
            pdf.ln(4)
        except Exception:
            pdf_cell(pdf, 6, f"Photo non intégrée : {label}")

    return pdf.output(dest='S').encode('latin1', errors='replace')

# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div style='width:100%; text-align:center; margin-bottom:12px;'>
        <div style="font-size:2.4rem; font-weight:800; line-height:1.12; text-align:center;">
            Relevé Technique<br><span style="white-space:nowrap;">CHALLENGE BAT</span>
        </div>
        <img src="{LOGO_URL}" alt="Logo Challenge BAT" style="width:78px; margin:14px auto 4px auto; display:block;" />
        <div style="font-size:0.95rem; color:#666;">Version : {VERSION}</div>
        <div style="color:#e74c3c; font-size:1rem; font-weight:600; margin-top:4px;">* Champs obligatoires</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info("Méthode terrain : relevez chaque mur de gauche à droite au télémètre, puis rattachez chaque contrainte au mur concerné. L'évacuation finale est volontairement traitée à part : c'est le point critique cuisine.")

# Étape 1
st.markdown("## 1. Informations du relevé")
client = st.text_input("Nom du client *", value="", key="client")
st.caption("Si le prénom n’est pas dans la liste, cochez ‘Autre prénom à saisir’, puis tapez-le dans le champ qui apparaît.")
metreur = st.radio("Sélectionnez votre prénom *", METREURS, key="metreur", horizontal=False)
if metreur == "Autre prénom à saisir":
    metreur_autre = st.text_input("Prénom du métreur *", key="metreur_autre", placeholder="Prénom")
    metreur_final = metreur_autre.strip()
else:
    metreur_autre = ""
    metreur_final = metreur
type_piece = st.selectbox(
    "Configuration de la pièce *",
    ["-- Sélectionnez --", "1 mur linéaire", "2 murs en L", "3 murs en U", "4 murs", "Pièce irrégulière / autre"],
    key="type_piece",
)

# Étape 2
st.markdown("## 2. Construction de la pièce")
st.markdown("**Départ conseillé :** en bas à droite, premier mur vers la gauche. Les murs sont nommés A, B, C... dans le sens du relevé.")
st.markdown(
    "Mesure angle sans rapporteur : "
    "[ouvrir l'aide](https://cbatconsulting.github.io/ANGLE/)",
    unsafe_allow_html=True,
)

nb_murs_default = {
    "1 mur linéaire": 1,
    "2 murs en L": 2,
    "3 murs en U": 3,
    "4 murs": 4,
}.get(type_piece, 3)

nb_murs = st.number_input("Nombre de murs à mesurer *", min_value=1, max_value=20, value=nb_murs_default, step=1, key="nb_murs")

longueurs = []
angles = []
exterieurs = []
with st.container(border=True):
    st.markdown("### Saisie des murs")
    for i in range(int(nb_murs)):
        mur_id = chr(ord('A') + i)
        cols = st.columns([1, 1, 1])
        longueur = cols[0].number_input(f"Mur {mur_id} - longueur (cm) *", min_value=0.0, max_value=10000.0, value=0.0, step=1.0, key=f"l{i}")
        longueurs.append(longueur)
        if i < int(nb_murs) - 1:
            angle = cols[1].number_input(f"Angle après mur {mur_id} (°)", min_value=1.0, max_value=359.9, value=90.0, step=0.1, key=f"a{i}")
            angles.append(angle)
            ext = cols[2].checkbox("Angle extérieur", key=f"ext{i}")
            exterieurs.append(ext)

hsp = st.number_input("Hauteur sous plafond (HSP) en cm *", min_value=0, max_value=500, value=0, step=1, key="hsp")

# Schéma en direct
if any(l > 0 for l in longueurs):
    fig = render_plan([max(l, 1) for l in longueurs], angles, exterieurs)
    st.pyplot(fig)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        fig.savefig(tmpfile.name, format="png", bbox_inches='tight')
        image_path = tmpfile.name
else:
    image_path = None

mur_choix = ["-- Sélectionnez --"] + [chr(ord('A')+i) for i in range(int(nb_murs))]
photo_paths = []

# Étape 3
st.markdown("## 3. Évacuation finale")
st.warning("Point prioritaire : l'évacuation finale conditionne l'évier, le lave-vaisselle et le lave-linge. Elle doit être localisée clairement.")
with st.container(border=True):
    evac_mur = st.selectbox("Mur support de l'évacuation finale *", mur_choix, key="evac_mur")
    c1, c2 = st.columns(2)
    evac_pos = c1.number_input("Position depuis la gauche du mur (cm) *", min_value=0.0, max_value=10000.0, value=0.0, step=1.0, key="evac_pos")
    evac_hauteur = c2.number_input("Hauteur depuis le sol (cm) *", min_value=0.0, max_value=500.0, value=0.0, step=1.0, key="evac_hauteur")
    c3, c4 = st.columns(2)
    evac_largeur = c3.number_input("Largeur visible (cm)", min_value=0.0, max_value=500.0, value=10.0, step=1.0, key="evac_largeur")
    evac_epaisseur = c4.number_input("Épaisseur / sortie murale (cm)", min_value=0.0, max_value=200.0, value=5.0, step=1.0, key="evac_epaisseur")
    evac_photo = st.file_uploader("Photo de l'évacuation finale", type=["jpg", "jpeg", "png"], key="evac_photo")
    evac_photo_path = uploaded_image_to_temp(evac_photo)
    if evac_photo_path:
        photo_paths.append(("Évacuation finale", evac_photo_path))

# Étape 4
st.markdown("## 4. Contraintes par mur")
st.markdown("Ajoutez uniquement les contraintes utiles. Pour chaque contrainte : choisissez le mur, puis soit vous saisissez les mesures, soit vous joignez une photo avec repère.")

CONTRAINTES_CHOIX = [
    "Porte", "Fenêtre", "Regroupement plomberie", "Arrivée eau", "Prise / sortie câble", "Interrupteur",
    "Socle", "Coffrage", "Poteau", "Trappe", "VMC / hotte", "Gaz", "Radiateur",
    "Faïence (si HS < 92 cm)", "Plinthes (si épaisseur > 1 cm ET hauteur > 8 cm)", "Autre (Préciser)"
]
nb_contraintes = st.number_input("Nombre de contraintes complémentaires à déclarer", min_value=0, max_value=30, value=0, step=1, key="nb_contraintes")
contraintes = []

for i in range(int(nb_contraintes)):
    with st.expander(f"Contrainte n°{i+1:02d}", expanded=True):
        c_type = st.selectbox(f"Type de contrainte n°{i+1}", CONTRAINTES_CHOIX, key=f"type_{i}")
        c_type_precise = ""
        if c_type == "Autre (Préciser)":
            c_type_precise = st.text_input(f"Précisez la contrainte n°{i+1}", key=f"precise_{i}")
        c_mur = st.selectbox("Mur support *", mur_choix, key=f"cmur_{i}")
        mode = st.radio(
            "Mode de positionnement",
            ["Mesure directe", "Photo avec repère A4 / mètre"],
            horizontal=True,
            key=f"mode_{i}",
        )
        c_data = {
            "type": c_type if c_type != "Autre (Préciser)" else c_type_precise,
            "mur": c_mur,
            "mode": mode,
            "pos": 0.0, "larg": 0.0, "epais": 0.0, "haut_sol": 0.0, "haut": 0.0,
            "reference": "", "mesure_connue": 0.0, "commentaire_photo": "", "commentaire": "", "photo_nom": "",
            "calc_complete": False, "calc_points": 0,
        }
        c_photo = st.file_uploader("Photo de la contrainte", type=["jpg", "jpeg", "png"], key=f"photo_contrainte_{i}")
        c_data["photo_nom"] = c_photo.name if c_photo else ""
        c_path = uploaded_image_to_temp(c_photo)
        if c_path:
            photo_paths.append((f"Contrainte {i+1:02d} - {c_data['type']} - Mur {c_mur}", c_path))

        if mode == "Mesure directe":
            d1, d2 = st.columns(2)
            c_data["pos"] = d1.number_input("Position depuis la gauche (cm)", min_value=0.0, max_value=10000.0, value=0.0, step=1.0, key=f"cpos_{i}")
            c_data["haut_sol"] = d2.number_input("Hauteur depuis le sol (cm)", min_value=0.0, max_value=500.0, value=0.0, step=1.0, key=f"chaut_sol_{i}")
            d3, d4, d5 = st.columns(3)
            c_data["larg"] = d3.number_input("Largeur (cm)", min_value=0.0, max_value=500.0, value=0.0, step=1.0, key=f"clarg_{i}")
            c_data["haut"] = d4.number_input("Hauteur de la contrainte (cm)", min_value=0.0, max_value=500.0, value=0.0, step=1.0, key=f"chaut_{i}")
            c_data["epais"] = d5.number_input("Épaisseur (cm)", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key=f"cepais_{i}")
        else:
            st.caption("Photo de face conseillée. Placez une feuille A4 ou un mètre visible, puis cliquez les points demandés pour obtenir une estimation.")
            c_data["reference"] = st.selectbox("Repère visible sur la photo", ["Feuille A4", "Mètre", "Distance connue", "Autre"], key=f"ref_{i}")
            c_data["mesure_connue"] = st.number_input("Mesure connue visible sur la photo (cm)", min_value=0.0, max_value=1000.0, value=29.7, step=0.1, key=f"mes_connue_{i}")
            c_data["commentaire_photo"] = st.text_input("Commentaire repère / position", placeholder="Précision utile sur la photo", key=f"comment_photo_{i}")
            calc = photo_measurement_assistant(c_photo, f"contrainte_{i}")
            c_data["calc_complete"] = calc.get("complete", False)
            c_data["calc_points"] = calc.get("points_count", 0)
            if calc.get("complete"):
                use_calc = st.checkbox("Utiliser cette estimation dans le rapport", value=True, key=f"use_calc_{i}")
                if use_calc:
                    c_data["pos"] = calc.get("pos", 0.0)
                    c_data["larg"] = calc.get("larg", 0.0)
                    c_data["haut_sol"] = calc.get("haut_sol", 0.0)
                    c_data["haut"] = calc.get("haut", 0.0)
                if calc.get("annotated_path"):
                    photo_paths.append((f"Repérage photo {i+1:02d} - {c_data['type']} - Mur {c_mur}", calc.get("annotated_path")))
            c_data["epais"] = st.number_input("Épaisseur à reporter (cm)", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key=f"cepais_photo_{i}")
        c_data["commentaire"] = st.text_area("Commentaire contrainte", key=f"comment_contrainte_{i}")
        contraintes.append(c_data)

# Étape 5
st.markdown("## 5. Électricité / tableau")
with st.container(border=True):
    st.markdown(
        "[Aide mesure valeur de terre](https://www.challengebat.fr/valeur-mesure-terre)",
        unsafe_allow_html=True,
    )
    valeur_terre = st.radio(
        "Mesure valeur mise à la terre *",
        ["Valeur ok", "Valeur pas ok", "Impossible à mesurer"],
        key="valeur_terre",
        index=None,
        horizontal=True,
    )
    tableau_emplacement = st.selectbox("Où est situé le tableau ? *", TABLEAU_CHOIX, key="tableau_emplacement")
    tableau_emplacement_precise = st.text_input("Précisez l'emplacement", "", key="tableau_emplacement_precise") if tableau_emplacement == "Autre" else ""
    tableau_developpe = st.number_input("Développé linéaire depuis le centre de la cuisine (mètres)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
    tableau_cloisons = st.radio("Y a-t-il des cloisons à traverser ? *", ("Non", "Oui"), key="tableau_cloisons", index=None, horizontal=True)
    tableau_place_deux = st.radio("Y a-t-il de la place pour un second coffret si nécessaire ? *", ("Non", "Oui"), key="tableau_place_deux", index=None, horizontal=True)

# Étape 6
st.markdown("## 6. Photos de contrôle")
st.caption("Cochez les photos réellement prises. L'objectif est de ne pas oublier les points bloquants.")
photo_options = [
    "Pièce entière",
    "Pièce de gauche à droite",
    "Regroupement plomberie",
    "Évacuation finale",
    "Tableau de répartition",
    "Appareil mesure terre si valeur pas OK / impossible",
]
photos_checked = {opt: st.checkbox(opt, key=f"photo_check_{opt}") for opt in photo_options}

# Étape 7
st.markdown("## 7. TVA réduite")
st.markdown("<i>(logement de plus de 2 ans)</i>", unsafe_allow_html=True)
tva_reduite = st.radio("Le logement est-il éligible à la TVA réduite ?", ["Oui", "Non"], horizontal=True)
raison_non_signature = ""
raison_autre_detail = ""
justif_non = ""
if tva_reduite == "Oui":
    st.success("Remplir l'attestation sur l'honneur TVA réduite ici :")
    st.markdown("[Accéder au formulaire TVA réduite](https://www.challengebat.fr/tva-reduite)", unsafe_allow_html=True)
    attestation_signee = st.radio("Attestation signée", options=["Oui", "Non"], key="attestation_signee_radio", horizontal=True)
    if attestation_signee == "Non":
        raison_non_signature = st.selectbox("Raison *", ["-- Sélectionnez --", "Client absent", "Problème informatique", "Autre"], key="raison_non_signature")
        if raison_non_signature == "Autre":
            raison_autre_detail = st.text_input("Précisez la raison")
else:
    attestation_signee = None
    justif_non = st.selectbox("Justification du refus TVA réduite :", ["Client absent", "Logement moins de 2 ans", "Entreprise"])

commentaire = st.text_area("Commentaire général", "")

# Étape 8
st.markdown("## 8. Envoi")
st.info(f"Le relevé sera envoyé par défaut à **{SUPPORT_EMAIL}**.")
email_dest = SUPPORT_EMAIL

st.markdown("**Mettre en copie**")
cc_maxime = st.checkbox("Maxime — maxime@challengebat.fr", key="cc_maxime")
cc_mohamed = st.checkbox("Mohamed — mohamed@challengebat.fr", key="cc_mohamed")
cc_autre = st.checkbox("Autre technicien / autre adresse à saisir", key="cc_autre")

email_cc_list = []
if cc_maxime:
    email_cc_list.append("maxime@challengebat.fr")
if cc_mohamed:
    email_cc_list.append("mohamed@challengebat.fr")

cc_autre_email = ""
if cc_autre:
    libelle_email_autre = f"Adresse email de {metreur_final} *" if metreur_final and metreur_final != "-- Sélectionnez --" else "Adresse email du technicien à mettre en copie *"
    cc_autre_email = st.text_input(
        libelle_email_autre,
        key="cc_autre_email",
        placeholder="prenom@challengebat.fr",
    ).strip()
    if cc_autre_email:
        email_cc_list.append(cc_autre_email)

email_cc = ", ".join(email_cc_list)

# Alertes automatiques
alertes = []
if evac_mur == "-- Sélectionnez --":
    alertes.append("Évacuation finale non localisée.")
if not evac_photo:
    alertes.append("Photo de l'évacuation finale non jointe.")
if not photos_checked.get("Tableau de répartition", False):
    alertes.append("Photo du tableau de répartition non cochée.")
if valeur_terre in ["Valeur pas ok", "Impossible à mesurer"] and not photos_checked.get("Appareil mesure terre si valeur pas OK / impossible", False):
    alertes.append("Mesure de terre non OK ou impossible : photo du mesureur conseillée.")
for c in contraintes:
    if c["mur"] == "-- Sélectionnez --":
        alertes.append(f"Contrainte '{c['type']}' sans mur support.")
    if c.get("mode") == "Photo avec repère A4 / mètre" and c.get("photo_nom") and not c.get("calc_complete"):
        alertes.append(f"Contrainte '{c['type']}' avec photo repère : calcul par points non complet.")

if alertes:
    with st.expander("Alertes du relevé", expanded=True):
        for alerte in alertes:
            st.warning(alerte)

now = datetime.datetime.now()
date_str = now.strftime("%d-%m-%Y_%H-%M")
nom_pdf = f"RT_{client or 'client'}_{date_str}.pdf"

if st.button("Envoyer le relevé par email", type="primary"):
    st.session_state["form_submitted"] = True

    cc_autre_incomplet = cc_autre and (not cc_autre_email or "@" not in cc_autre_email)

    champs_vides = (
        not client
        or metreur_final == "-- Sélectionnez --" or not metreur_final
        or type_piece == "-- Sélectionnez --"
        or not email_dest
        or hsp <= 0
        or not valeur_terre
        or evac_mur == "-- Sélectionnez --"
        or any(l <= 0 for l in longueurs)
        or tableau_emplacement == "-- Sélectionnez --"
        or tableau_cloisons is None
        or tableau_place_deux is None
        or image_path is None
    )

    if tva_reduite == "Oui" and (
        attestation_signee is None or
        (attestation_signee == "Non" and (
            not raison_non_signature or raison_non_signature == "-- Sélectionnez --" or
            (raison_non_signature == "Autre" and not raison_autre_detail)
        ))
    ):
        st.error("Veuillez soit signer l'attestation TVA réduite, soit indiquer une raison valable.", icon="🚫")
    elif champs_vides:
        st.error("Veuillez remplir tous les champs obligatoires.", icon="🚫")
    elif cc_autre_incomplet:
        st.error("Veuillez renseigner l’adresse email de l’autre technicien à mettre en copie.", icon="🚫")
    else:
        evac = {
            "mur": evac_mur,
            "pos": evac_pos,
            "largeur": evac_largeur,
            "epaisseur": evac_epaisseur,
            "hauteur": evac_hauteur,
            "photo_nom": evac_photo.name if evac_photo else "",
        }
        data = {
            "now": now,
            "client": client,
            "metreur": metreur_final,
            "type_piece": type_piece,
            "email_dest": email_dest,
            "email_cc": email_cc,
            "hsp": hsp,
            "valeur_terre": valeur_terre,
            "longueurs": longueurs,
            "angles": angles,
            "exterieurs": exterieurs,
            "evac": evac,
            "contraintes": contraintes,
            "tableau_emplacement": tableau_emplacement,
            "tableau_emplacement_precise": tableau_emplacement_precise,
            "tableau_developpe": tableau_developpe,
            "tableau_cloisons": tableau_cloisons,
            "tableau_place_deux": tableau_place_deux,
            "photos_checked": photos_checked,
            "tva_reduite": tva_reduite,
            "attestation_signee": attestation_signee,
            "raison_non_signature": raison_non_signature,
            "raison_autre_detail": raison_autre_detail,
            "justif_non": justif_non,
            "commentaire": commentaire,
            "alertes": alertes,
        }
        pdf_bytes = make_pdf_message(data, image_path, photo_paths)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(pdf_bytes)
            pdf_path = f.name
        sujet = f"RELEVÉ TECHNIQUE - {client} - {now.strftime('%d/%m/%Y %Hh%M')}"
        html_message = f"""
        <p>Bonjour,<br>Relevé technique en pièce jointe.<br>
        <b>Nom du client :</b> {client}<br>
        <b>Métreur :</b> {metreur_final}<br>
        <b>Version :</b> {VERSION}<br>
        <b>Copie :</b> {email_cc or "-"}</p>
        """
        ok, msg = envoyer_gmail(email_dest, sujet, html_message, pdf_path, nom_pdf, cc=email_cc)
        if ok:
            st.success("Email envoyé !")
            st.download_button("Télécharger le PDF", pdf_bytes, file_name=nom_pdf, mime="application/pdf")
            st.session_state["form_submitted"] = False
        else:
            st.error(msg)
        try:
            os.unlink(pdf_path)
        except Exception:
            pass

# Nettoyage best effort des fichiers temporaires à la fin du run
# Streamlit relance souvent le script : on évite de supprimer image_path avant génération PDF.
