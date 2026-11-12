import os
import json
import time
import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------------------
# FYM Hospitality Group | Internal workplace conflict-style assessment
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "FYM_Logo_3_Black(1).png"
DB_PATH = os.getenv("FYM_DB_PATH", str(BASE_DIR / "fym_assessments.db"))
DURATION_SECONDS = 15 * 60
RETENTION_DAYS = 5 * 365

st.set_page_config(
    page_title="FYM Hospitality Group | Թեստի Հարթակ",
    page_icon="F",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Clean, responsive, black-and-white presentation with white input backgrounds.
st.markdown("""
<style>
:root { color-scheme: light; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #ffffff !important; color: #171717 !important;
}
[data-testid="stHeader"] { background: #ffffff !important; }
.block-container { max-width: 900px; padding-top: 1.15rem; padding-bottom: 3rem; }
h1, h2, h3, p, label, span, div { color: #171717; }
.fym-logo-wrap { width: 100%; display:flex; justify-content:center; align-items:center;
                 padding: 0.55rem 0 0 0; margin-bottom: 0; }
div[data-testid="stImage"] { display:flex; justify-content:center; margin-top:.2rem;
                            margin-bottom:-.15rem; }
.fym-kicker { text-align:center; color:#555; font-size:.8rem; letter-spacing:.13em;
              text-transform:uppercase; margin-bottom:.1rem; }
.fym-title { text-align:center; font-size:1.45rem; font-weight:700; margin:.1rem 0 .3rem; }
.fym-subtitle { text-align:center; color:#555; margin-bottom:1rem; }
hr { border:0; border-top:1px solid #dedede; margin:0.8rem 0; }

/* Force white background and dark text on all input boxes, text areas, and select boxes across the app */
input[type="text"], input[type="password"], textarea, 
[data-baseweb="input"] input, [data-baseweb="base-input"] input,
[data-testid="stTextInput"] input, [data-testid="stPasswordInput"] input,
[data-baseweb="select"] div, [data-testid="stSelectbox"] div {
    background-color: #ffffff !important;
    color: #171717 !important;
}
[data-baseweb="select"] > div, [data-testid="stSelectbox"] > div > div {
    background-color: #ffffff !important;
    border-color: #cccccc !important;
}
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"],
[role="option"], [data-baseweb="menu"] li {
    background-color: #ffffff !important;
    color: #171717 !important;
}

div.stButton > button, div.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button, [data-testid="stButton"] button {
    border:1px solid #171717 !important; border-radius:7px !important;
    background:#ffffff !important; color:#171717 !important;
    min-height:2.65rem; font-weight:600; width:100%;
    opacity:1 !important; pointer-events:auto !important;
}
div.stButton > button:hover, div.stButton > button:active,
div.stButton > button:focus, div.stButton > button:focus-visible,
div.stDownloadButton > button:hover, div.stDownloadButton > button:active,
div.stDownloadButton > button:focus, div.stDownloadButton > button:focus-visible,
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stFormSubmitButton"] button:active,
[data-testid="stFormSubmitButton"] button:focus,
[data-testid="stFormSubmitButton"] button:focus-visible,
[data-testid="stButton"] button:hover, [data-testid="stButton"] button:active,
[data-testid="stButton"] button:focus, [data-testid="stButton"] button:focus-visible {
    background:#ffffff !important; border-color:#171717 !important;
    color:#171717 !important; box-shadow:0 0 0 .12rem #d5d5d5 !important;
}
div.stButton > button:disabled { opacity:.45 !important; }
[data-testid="stRadio"], [data-testid="stRadio"] *,
[data-testid="stRadio"] label, [data-testid="stRadio"] input {
    pointer-events:auto !important;
}
[data-testid="stRadio"] label { color:#171717 !important; cursor:pointer !important; }
[data-testid="stRadio"] input[type="radio"] {
    accent-color:#171717 !important; background:#ffffff !important;
}
[data-testid="stProgressBar"] > div > div { background:#171717 !important; }
[data-testid="stMetric"] { border:1px solid #e5e5e5; border-radius:8px; padding:.8rem; }
.fym-card { border:1px solid #e2e2e2; border-radius:9px; padding:1rem 1.1rem;
            margin:.65rem 0; background:#fff; }
.fym-muted { color:#626262 !important; font-size:.9rem; }
.fym-timer { border:1px solid #222; border-radius:8px; padding:.45rem .8rem;
             text-align:center; font-weight:700; font-size:1.15rem; margin-top: 0.2rem; }
.small-note { font-size:.82rem; color:#666; }
@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .fym-title { font-size:1.25rem; }
}
</style>
""", unsafe_allow_html=True)

def render_header():
    st.markdown('<div class="fym-logo-wrap">', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=380)
    else:
        st.markdown("**FYM HOSPITALITY GROUP**", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="fym-kicker">FYM HOSPITALITY GROUP</div>', unsafe_allow_html=True)
    st.markdown('<div class="fym-title">Թեստի Հարթակ</div>', unsafe_allow_html=True)

render_header()

# Database: SQLite by default.
def db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            position TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            completed_at TEXT, status TEXT NOT NULL, answers TEXT NOT NULL,
            scores TEXT, dominant TEXT, duration_seconds INTEGER DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        con.commit()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    with db() as con:
        con.execute("DELETE FROM candidates WHERE created_at < ?", (cutoff,))
        con.commit()

init_db()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_setting(key):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, value):
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        con.commit()

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()
    return f"{salt}${digest}"

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)
    except Exception:
        return False

if not get_setting("admin_password_hash"):
    try:
        secret_password = st.secrets.get("FYM_HR_PASSWORD", "")
    except Exception:
        secret_password = ""
    initial = os.getenv("FYM_HR_PASSWORD") or secret_password
    if initial:
        set_setting("admin_password_hash", hash_password(initial))
    else:
        set_setting("admin_password_hash", hash_password("1234"))

STYLE_INFO = {
    "M": {
        "name": "Մրցակցություն",
        "meaning": "Մարդը հակված է վճռականորեն պաշտպանելու իր դիրքորոշումը և հետամուտ լինելու իր նպատակներին։ Այս մոտեցումը շեշտադրում է սեփական շահերի պաշտպանությունը։",
        "strengths": ["Արագ և վճռական որոշումներ կայացնելու պատրաստակամություն", "Սեփական դիրքորոշումը հստակ ներկայացնելու կարողություն", "Կարևոր սկզբունքներն ու չափանիշները պաշտպանելու հաստատակամություն"],
        "risks": ["Կարող է նվազեցնել մյուս կողմի ներգրավվածությունը", "Չափազանց հաճախ կիրառելիս կարող է սրել հարաբերությունները", "Կարող է սահմանափակել այլընտրանքային լուծումների քննարկումը"],
        "work": "Ղեկավարման ընթացքում կարող է դրսևորվել որպես ուղղակի և որոշումակենտրոն մոտեցում։ Թիմում օգտակար է հրատապության կամ հստակ չափանիշների դեպքում, սակայն կարևոր է լսել հակառակ կարծիքները։",
        "coaching": "Զարգացնել ակտիվ լսումը, հարցեր տալու և սեփական դիրքորոշումը հիմնավորելու՝ առանց մյուս կողմին անտեսելու հմտությունները։"
    },
    "G": {
        "name": "Համագործակցություն",
        "meaning": "Մարդը ձգտում է բացահայտել երկու կողմերի մտահոգություններն ու շահերը և գտնել լուծում, որը հնարավորինս ամբողջականորեն հաշվի է առնում դրանք։",
        "strengths": ["Խնդրի խորքային պատճառները բացահայտելու կարողություն", "Վստահության և թիմային ներգրավվածության խթանում", "Երկարաժամկետ և փոխշահավետ լուծումների որոնում"],
        "risks": ["Քննարկումը կարող է երկար տևել", "Բոլոր կողմերի համաձայնությունը միշտ չէ, որ իրատեսական է", "Ժամանակի ճնշման պայմաններում կարող է դժվարանալ արագ որոշում կայացնելը"],
        "work": "Թիմում նպաստում է կարծիքների փոխանակմանը և համատեղ պատասխանատվությանը։ Ղեկավարման մեջ կարող է խրախուսել մասնակցային որոշումների կայացումը։",
        "coaching": "Սովորել սահմանել քննարկման ժամանակային սահմաններ և տարբերակել այն իրավիճակները, երբ անհրաժեշտ է արագ որոշում։"
    },
    "P": {
        "name": "Փոխզիջում",
        "meaning": "Մարդը փնտրում է միջանկյալ լուծում, որի դեպքում երկու կողմերն էլ որոշ չափով զիջում են և ստանում իրենց համար կարևոր արդյունքի մի մասը։",
        "strengths": ["Գործնական և համեմատաբար արագ համաձայնության հասնելու կարողություն", "Երկու կողմերի կարիքները հաշվի առնելու պատրաստակամություն", "Փակուղուց դուրս գալու և աշխատանքը շարունակելու հմտություն"],
        "risks": ["Լուծումը կարող է չանդրադառնալ խնդրի խորքային պատճառներին", "Երկու կողմերն էլ կարող են մասամբ դժգոհ մնալ", "Կարևոր սկզբունքները երբեմն կարող են զիջվել արագ համաձայնության համար"],
        "work": "Օգտակար է ռեսուրսների, ժամանակացույցերի կամ առաջնահերթությունների շուրջ բանակցություններում։ Թիմում օգնում է առաջ շարժվել, երբ ամբողջական համաձայնությունը դժվար է։",
        "coaching": "Մինչև զիջումների գնալը հստակեցնել՝ որոնք են չզիջվող պահանջները և արդյոք հնարավոր է ավելի ամբողջական լուծում։"
    },
    "X": {
        "name": "Խուսափում",
        "meaning": "Մարդը կարող է հետաձգել կամ չմտնել տարաձայնության քննարկման մեջ՝ ժամանակ շահելու, լարվածությունը նվազեցնելու կամ տվյալ պահին հարցը երկրորդական համարելու նպատակով։",
        "strengths": ["Անհարկի սրացումից խուսափելու կարողություն", "Զգացմունքները կարգավորելու և մտածելու ժամանակ ստեղծելու հնարավորություն", "Երկրորդական հարցերի վրա ավելորդ ռեսուրս չծախսելու հմտություն"],
        "risks": ["Կարևոր խնդիրները կարող են մնալ չլուծված", "Հետաձգումը կարող է մեծացնել անորոշությունը", "Մյուս կողմը կարող է դա ընկալել որպես անտարբերություն կամ անհասանելիություն"],
        "work": "Կարճ դադարն օգտակար է բարձր լարվածության պահին։ Սակայն չքննարկված աշխատանքային խնդիրները կարող են ազդել համագործակցության և ծառայության որակի վրա։",
        "coaching": "Հետաձգելիս պայմանավորվել քննարկման հստակ ժամկետի շուրջ և վերադառնալ խնդրին՝ պատրաստված ու փաստերի հիման վրա։"
    },
    "H": {
        "name": "Հարմարվողականություն",
        "meaning": "Մարդը կարևորում է դիմացինի կարիքներն ու հարաբերությունների պահպանումը և որոշ իրավիճակներում պատրաստ է զիջել սեփական նախընտրությունը։",
        "strengths": ["Հարաբերությունները պահպանելու և լարվածությունը մեղմելու կարողություն", "Ճկունություն և դիմացինի կարիքների նկատմամբ զգայունություն", "Համագործակցային միջավայրին նպաստելու պատրաստակամություն"],
        "risks": ["Կարող է անտեսել սեփական կարևոր կարիքները", "Կրկնվող զիջումները կարող են առաջացնել դժգոհություն", "Մյուսները կարող են չհասկանալ մարդու իրական դիրքորոշումը"],
        "work": "Թիմում կարող է աջակցել փոխօգնությանը և հաճախորդակենտրոն մոտեցմանը։ Կարևոր է, որ զիջումները չխաթարեն աշխատանքի չափանիշները կամ դերային պատասխանատվությունը։",
        "coaching": "Զարգացնել հարգալից սահմաններ դնելու և սեփական կարիքները հանգիստ ու հստակ արտահայտելու կարողությունը։"
    }
}

KEY = {
 1:("X","H"), 2:("P","G"), 3:("M","X"), 4:("P","H"), 5:("G","X"),
 6:("X","M"), 7:("X","P"), 8:("M","G"), 9:("X","M"), 10:("M","P"),
 11:("G","H"), 12:("X","P"), 13:("P","M"), 14:("G","M"), 15:("H","X"),
 16:("H","M"), 17:("M","X"), 18:("H","P"), 19:("G","X"), 20:("G","P"),
 21:("H","G"), 22:("P","M"), 23:("X","G"), 24:("H","P"), 25:("M","H"),
 26:("P","G"), 27:("X","H"), 28:("M","G"), 29:("P","X"), 30:("H","G")
}
QUESTIONS = [
("Երբեմն ես թույլ եմ տալիս, որ ուրիշներն իրենց վրա վերցնեն խնդրի լուծման պատասխանատվությունը։",
 "Տարաձայնությունների շուրջ բանակցելու փոխարեն՝ ես փորձում եմ շեշտադրել այն հարցերը, որոնց շուրջ մենք համակարծիք ենք։"),
("Ես փորձում եմ գտնել փոխզիջումային լուծում։",
 "Ես փորձում եմ հաշվի առնել թե՛ դիմացինի, թե՛ իմ բոլոր մտահոգություններն ու շահերը։"),
("Ես սովորաբար հաստատակամորեն հետամուտ եմ լինում իմ նպատակներին։",
 "Երբեմն փորձում եմ մեղմել դիմացինի բացասական զգացմունքները և պահպանել մեր հարաբերությունները։"),
("Ես փորձում եմ գտնել փոխզիջումային լուծում։",
 "Երբեմն իմ ցանկությունները զիջում եմ դիմացինի ցանկություններին։"),
("Ես մշտապես դիմում եմ դիմացինին՝ խնդրի լուծման տարբերակ գտնելու հարցում նրա օգնությունը ստանալու համար։",
 "Ես փորձում եմ անել անհրաժեշտ ամեն ինչ՝ անիմաստ լարվածությունից խուսափելու համար։"),
("Ես փորձում եմ խուսափել այնպիսի իրավիճակներից, որոնք կարող են ինձ համար տհաճություն ստեղծել։",
 "Ես փորձում եմ հասնել նրան, որ իմ դիրքորոշումը հաղթի։"),
("Ես փորձում եմ հետաձգել հարցի քննարկումը, մինչև որոշ ժամանակ ունենամ այն մտածելու համար։",
 "Որոշ հարցերում զիջում եմ՝ փոխարենը մյուս հարցերում զիջումներ ստանալու համար։"),
("Ես սովորաբար հաստատակամորեն հետամուտ եմ լինում իմ նպատակներին։",
 "Ես փորձում եմ անմիջապես բաց քննարկման դնել բոլոր մտահոգություններն ու խնդիրները։"),
("Կարծում եմ՝ տարաձայնությունները միշտ չէ, որ արժե մտահոգիչ համարել։",
 "Ես որոշակի ջանքեր եմ գործադրում իմ ուզածին հասնելու համար։"),
("Ես հաստատակամորեն հետամուտ եմ լինում իմ նպատակներին։",
 "Ես փորձում եմ գտնել փոխզիջումային լուծում։"),
("Ես փորձում եմ անմիջապես բաց քննարկման դնել բոլոր մտահոգություններն ու խնդիրները։",
 "Երբեմն փորձում եմ մեղմել դիմացինի բացասական զգացմունքները և պահպանել մեր հարաբերությունները։"),
("Երբեմն խուսափում եմ այնպիսի դիրքորոշում արտահայտելուց, որը կարող է տարաձայնություններ առաջացնել։",
 "Ես պատրաստ եմ որոշ հարցերում զիջել դիմացինին, եթե նա էլ իր հերթին որոշ հարցերում զիջի ինձ։"),
("Ես առաջարկում եմ միջանկյալ լուծում, որը հաշվի է առնում երկու կողմերի դիրքորոշումները։",
 "Ես պնդում եմ, որ իմ տեսակետը նույնպես հաշվի առնվի։"),
("Ես ներկայացնում եմ դիմացինին իմ գաղափարները և հարցնում նրա կարծիքը։",
 "Ես փորձում եմ ներկայացնել իմ դիրքորոշման տրամաբանությունն ու առավելությունները։"),
("Երբեմն փորձում եմ մեղմել դիմացինի բացասական զգացմունքները և պահպանել մեր հարաբերությունները։",
 "Ես փորձում եմ անել անհրաժեշտ ամեն ինչ՝ անիմաստ լարվածությունից խուսափելու համար։"),
("Ես փորձում եմ չվիրավորել դիմացինի զգացմունքները։",
 "Ես փորձում եմ համոզել դիմացինին իմ դիրքորոշման առավելություններում։"),
("Ես սովորաբար հաստատակամորեն հետամուտ եմ լինում իմ նպատակներին։",
 "Ես փորձում եմ անել անհրաժեշտ ամեն ինչ՝ անիմաստ լարվածությունից խուսափելու համար։"),
("Եթե դա կուրախացնի դիմացինին, ես կարող եմ թույլ տալ, որ նա մնա իր տեսակետին։",
 "Ես պատրաստ եմ որոշ հարցերում զիջել դիմացինին, եթե նա էլ իր հերթին որոշ հարցերում զիջի ինձ։"),
("Ես փորձում եմ անմիջապես բաց քննարկման դնել բոլոր մտահոգություններն ու խնդիրները։",
 "Ես փորձում եմ հետաձգել հարցի քննարկումը, մինչև որոշ ժամանակ ունենամ այն վերանայելու և մտածելու համար։"),
("Ես փորձում եմ անմիջապես քննարկել և լուծել մեր միջև առկա տարաձայնությունները։",
 "Ես փորձում եմ գտնել արդարացի լուծում, որի դեպքում երկու կողմերն էլ և՛ զիջումներ են անում, և՛ որոշակի օգուտներ ստանում։"),
("Բանակցությունների ընթացքում փորձում եմ հաշվի առնել դիմացինի զգացմունքները։",
 "Ես միշտ նախընտրում եմ խնդրի շուրջ անմիջական և բաց քննարկումը։"),
("Ես փորձում եմ գտնել այնպիսի դիրքորոշում, որը միջանկյալ տարբերակ կլինի իմ և դիմացինի դիրքորոշումների միջև։",
 "Ես պնդում եմ իմ ցանկությունների իրականացումը։"),
("Ինձ համար հաճախ կարևոր է, որ իմ բոլոր ցանկությունները բավարարվեն։",
 "Երբեմն թույլ եմ տալիս, որ ուրիշներն իրենց վրա վերցնեն խնդիրների լուծման պատասխանատվությունը։"),
("Եթե դիմացինի դիրքորոշումը նրա համար կարևոր է թվում, ես փորձում եմ հաշվի առնել և բավարարել նրա ցանկությունները։",
 "Ես փորձում եմ հասնել նրան, որ դիմացինը համաձայնի փոխզիջումային լուծման։"),
("Ես փորձում եմ դիմացինին ներկայացնել իմ դիրքորոշման տրամաբանությունն ու առավելությունները։",
 "Բանակցությունների ընթացքում փորձում եմ հաշվի առնել դիմացինի ցանկությունները։"),
("Ես առաջարկում եմ միջանկյալ լուծում, որը հաշվի է առնում երկու կողմերի դիրքորոշումները։",
 "Ինձ համար գրեթե միշտ կարևոր է, որ իմ բոլոր ցանկությունները բավարարվեն։"),
("Երբեմն խուսափում եմ այնպիսի դիրքորոշում արտահայտելուց, որը կարող է տարաձայնություններ առաջացնել։",
 "Եթե դա կուրախացնի դիմացինին, ես կարող եմ թույլ տալ, որ նա մնա իր տեսակետին։"),
("Ես սովորաբար հաստատակամորեն հետամուտ եմ լինում իմ նպատակներին։",
 "Կարծում եմ՝ տարաձայնությունները միշտ չէ, որ արժե մտահոգիչ համարել։"),
("Ես առաջարկում եմ միջանկյալ լուծում, որը հաշվի է առնում երկու կողմերի դիրքորոշումները։",
 "Կարծում եմ՝ տարաձայնությունները միշտ չէ, որ արժե մտահոգիչ համարել։"),
("Ես փորձում եմ չվիրավորել դիմացինի զգացմունքները։",
 "Ես միշտ դիմացինի հետ կիսում եմ խնդիրը, որպեսզի միասին գտնենք դրա լուծումը։")
]

def score_answers(answers):
    scores = {k: 0 for k in STYLE_INFO}
    for qnum, choice in answers.items():
        if choice in ("A", "B"):
            scores[KEY[int(qnum)][0 if choice == "A" else 1]] += 1
    total = sum(scores.values()) or 1
    percentages = {k: round(v / total * 100, 1) for k, v in scores.items()}
    highest = max(scores.values()) if scores else 0
    dominant = [k for k, v in scores.items() if v == highest]
    return scores, percentages, dominant

def save_candidate(candidate_id, first, last, position, created, answers, status,
                   started_at, completed_at=None):
    scores, percentages, dominant = score_answers(answers)
    duration = max(0, int(time.time() - started_at)) if started_at else 0
    dominant_text = " / ".join(STYLE_INFO[k]["name"] for k in dominant) if answers else ""
    with db() as con:
        con.execute("""INSERT INTO candidates
        (id,first_name,last_name,position,created_at,updated_at,completed_at,status,
         answers,scores,dominant,duration_seconds)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
        updated_at=excluded.updated_at, completed_at=excluded.completed_at,
        status=excluded.status, answers=excluded.answers, scores=excluded.scores,
        dominant=excluded.dominant, duration_seconds=excluded.duration_seconds""",
        (candidate_id, first, last, position, created, now_iso(), completed_at,
         status, json.dumps(answers, ensure_ascii=False),
         json.dumps({"scores": scores, "percentages": percentages}, ensure_ascii=False),
         dominant_text, duration))
        con.commit()

def fetch_candidates():
    with db() as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()]

def fetch_candidate(cid):
    with db() as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
        return dict(row) if row else None

def fmt_date(value):
    if not value: return "—"
    try: return datetime.fromisoformat(value).astimezone().strftime("%d.%m.%Y %H:%M")
    except Exception: return value

def completion(status):
    st.markdown("## Շնորհակալություն։")
    st.markdown("### Թեստն ավարտված է։")
    st.write("Ձեր պատասխանները պահպանվել են։ HR բաժինը կդիտարկի Ձեր պատասխանները։ Տվյալները պաշտպանված են և հասանելի են միայն HR աշխատակիցներին։")
    if status == "Timed Out":
        st.info("Ժամանակը լրացել է։ Պահպանվել են Ձեր արդեն տրված պատասխանները։")
    if st.button("Գլխավոր էջ", use_container_width=True):
        for k in ["candidate_id","candidate_started","candidate_created","candidate_first",
                  "candidate_last","candidate_position","answers","question_index","finished_status"]:
            st.session_state.pop(k, None)
        for q in range(1, 31):
            st.session_state.pop(f"answer_{q}", None)
        st.rerun()

st.session_state.setdefault("active_page", "Թեստի Հարթակ")
page = st.session_state.active_page

if page == "HR մուտք":
    st.markdown("## HR մուտք")
    if not st.session_state.get("hr_authenticated"):
        if not get_setting("admin_password_hash"):
            st.warning("HR գաղտնաբառը դեռ կարգավորված չէ։ Տեղադրեք FYM_HR_PASSWORD գաղտնի փոփոխականը Streamlit Secrets-ում կամ միջավայրի փոփոխականներում, ապա վերաբեռնեք հավելվածը։")
        with st.form("hr_login"):
            password = st.text_input("Գաղտնաբառ", type="password")
            submitted = st.form_submit_button("Մուտք գործել")
        if submitted:
            stored = get_setting("admin_password_hash")
            if stored and verify_password(password, stored):
                st.session_state.hr_authenticated = True
                st.rerun()
            else:
                st.error("Գաղտնաբառը սխալ է կամ դեռ կարգավորված չէ։")
    else:
        st.success("Մուտքը հաստատված է։")
        if st.button("Ելք HR բաժնից"):
            st.session_state.hr_authenticated = False
            st.rerun()
        with st.expander("Փոխել HR գաղտնաբառը"):
            with st.form("change_password"):
                old = st.text_input("Գործող գաղտնաբառ", type="password")
                new = st.text_input("Նոր գաղտնաբառ", type="password")
                confirm = st.text_input("Կրկնել նոր գաղտնաբառը", type="password")
                change = st.form_submit_button("Պահպանել նոր գաղտնաբառը")
            if change:
                stored = get_setting("admin_password_hash")
                if not stored or not verify_password(old, stored):
                    st.error("Գործող գաղտնաբառը սխալ է։")
                elif len(new) < 12:
                    st.error("Նոր գաղտնաբառը պետք է պարունակի առնվազն 12 նիշ։")
                elif new != confirm:
                    st.error("Նոր գաղտնաբառերը չեն համընկնում։")
                else:
                    set_setting("admin_password_hash", hash_password(new))
                    st.success("Գաղտնաբառը փոխվել է։")

        if st.session_state.get("hr_authenticated"):
            records = fetch_candidates()
            st.markdown("---")
            st.markdown("## HR վահանակ")
            total = len(records)
            completed = sum(r["status"] == "Completed" for r in records)
            timed_out = sum(r["status"] == "Timed Out" for r in records)
            abandoned = sum(r["status"] in ("Abandoned", "Closed Early") for r in records)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Ընդհանուր թեկնածուներ", total)
            c2.metric("Ավարտված", completed)
            c3.metric("Ժամանակը լրացել է", timed_out)
            c4.metric("Չավարտված", abandoned)
            durations = [r["duration_seconds"] for r in records
                         if r["status"] in ("Completed", "Timed Out") and r["duration_seconds"]]
            if durations:
                avg_seconds = int(sum(durations) / len(durations))
                st.metric("Միջին տևողություն", f"{avg_seconds // 60:02d}:{avg_seconds % 60:02d}")

            completed_records = [r for r in records if r["status"] in ("Completed","Timed Out")]
            if completed_records:
                all_scores = []
                dominant_counts = {}
                for r in completed_records:
                    try:
                        parsed = json.loads(r["scores"] or "{}")
                        all_scores.append(parsed.get("scores", {}))
                        dominant_counts[r["dominant"]] = dominant_counts.get(r["dominant"], 0) + 1
                    except Exception:
                        pass
                if all_scores:
                    avg = {k: round(sum(s.get(k,0) for s in all_scores)/len(all_scores),2) for k in STYLE_INFO}
                    st.markdown("### Կազմակերպության վիճակագրություն")
                    st.caption("Միջին միավորներ՝ ըստ ոճերի")
                    st.bar_chart(pd.DataFrame({"Միջին միավոր": [avg[k] for k in STYLE_INFO]},
                                              index=[STYLE_INFO[k]["name"] for k in STYLE_INFO]))
                    if dominant_counts:
                        st.write("Ամենահաճախ հանդիպող գերիշխող ոճը:", max(dominant_counts, key=dominant_counts.get))
                        st.caption("Գերիշխող ոճերի բաշխում")
                        st.bar_chart(pd.DataFrame({"Թեկնածուների քանակ": list(dominant_counts.values())},
                                                  index=list(dominant_counts.keys())))

            st.markdown("---")
            st.markdown("## Թեկնածուների ցանկ")
            search = st.text_input("Որոնել ըստ անվան, ազգանվան կամ հաստիքի")
            statuses = ["Բոլորը"] + sorted({r["status"] for r in records})
            status_filter = st.selectbox("Կարգավիճակ", statuses)
            filtered = []
            for r in records:
                hay = f'{r["first_name"]} {r["last_name"]} {r["position"]}'.lower()
                if search.lower() not in hay: continue
                if status_filter != "Բոլորը" and r["status"] != status_filter: continue
                filtered.append(r)
            if filtered:
                table_rows = [{
                    "Անուն": r["first_name"], "Ազգանուն": r["last_name"],
                    "Հաստիք": r["position"], "Ամսաթիվ": fmt_date(r["created_at"]),
                    "Կարգավիճակ": r["status"], "Գերիշխող ոճ": r["dominant"] or "—"
                } for r in filtered]
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
                options = {f'{r["first_name"]} {r["last_name"]} | {r["position"]} | {r["id"][:8]}': r["id"] for r in filtered}
                selected_label = st.selectbox("Դիտել թեկնածուի հաշվետվությունը", list(options))
                selected = fetch_candidate(options[selected_label])
                if selected:
                    st.markdown("### Թեկնածուի հաշվետվություն")
                    st.write(f'**Անուն:** {selected["first_name"]} {selected["last_name"]}')
                    st.write(f'**Հաստիք:** {selected["position"]}')
                    st.write(f'**Ամսաթիվ:** {fmt_date(selected["created_at"])}')
                    st.write(f'**Ավարտի ամսաթիվ:** {fmt_date(selected["completed_at"])}')
                    st.write(f'**Կարգավիճակ:** {selected["status"]}')
                    answers = json.loads(selected["answers"] or "{}")
                    scores, percentages, dominant = score_answers(answers)
                    st.markdown("#### Պատասխաններ")
                    answer_rows = [{"Հարց": int(n), "Պատասխան": a} for n,a in sorted(answers.items(), key=lambda x:int(x[0]))]
                    if answer_rows:
                        st.dataframe(pd.DataFrame(answer_rows), use_container_width=True, hide_index=True)
                    st.markdown("#### Արդյունքներ")
                    result_df = pd.DataFrame([{
                        "Ոճ": STYLE_INFO[k]["name"], "Միավոր": scores[k],
                        "Տոկոս": f'{percentages[k]}%',
                    } for k in sorted(STYLE_INFO, key=lambda x: scores[x], reverse=True)])
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    st.bar_chart(pd.DataFrame({"Տոկոս": [percentages[k] for k in STYLE_INFO]},
                                              index=[STYLE_INFO[k]["name"] for k in STYLE_INFO]))
                    st.markdown("#### Գերիշխող ոճի մեկնաբանություն")
                    for k in dominant:
                        info = STYLE_INFO[k]
                        st.markdown(f"**{info['name']}**")
                        st.write(info["meaning"])
                        st.write("**Ուժեղ կողմեր**")
                        for item in info["strengths"]: st.markdown(f"- {item}")
                        st.write("**Հնարավոր ռիսկեր / զարգացման կողմեր**")
                        for item in info["risks"]: st.markdown(f"- {item}")
                        st.write("**Աշխատավայրում դրսևորումներ**")
                        st.write(info["work"])
                        st.write("**Զարգացման առաջարկ**")
                        st.write(info["coaching"])
                    st.caption("Արդյունքները նկարագրում են տվյալ հարցաթերթիկում ընտրված նախընտրությունները և չպետք է օգտագործվեն որպես աշխատանքի ընդունման միակ չափանիշ։")
            else:
                st.info("Համապատասխան թեկնածուներ չկան։")

            if records:
                export_rows = []
                for r in records:
                    row = {"ID":r["id"],"Անուն":r["first_name"],"Ազգանուն":r["last_name"],
                           "Հաստիք":r["position"],"Սկիզբ":r["created_at"],
                           "Ավարտ":r["completed_at"],"Կարգավիճակ":r["status"],
                           "Գերիշխող ոճ":r["dominant"]}
                    ans = json.loads(r["answers"] or "{}")
                    for i in range(1,31): row[f"Հարց {i}"] = ans.get(str(i),"")
                    sc,pc,dom = score_answers(ans)
                    for k in STYLE_INFO:
                        row[f'{STYLE_INFO[k]["name"]} միավոր'] = sc[k]
                        row[f'{STYLE_INFO[k]["name"]} տոկոս'] = pc[k]
                    export_rows.append(row)
                csv = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8-sig")
                st.download_button("Արտահանել CSV", csv, "fym_candidate_assessments.csv",
                                   "text/csv", use_container_width=True)
            st.caption("Տվյալները պահվում են մինչև 5 տարի՝ ըստ հավելվածի պահպանման կարգավորման։")

else:
    components.html(
        """
        <script>
        (() => {
          try {
            const doc = window.parent.document;
            if (doc.__fymClipboardGuardInstalled) return;
            doc.__fymClipboardGuardInstalled = true;
            ["copy", "cut", "paste", "contextmenu"].forEach((eventName) => {
              doc.addEventListener(eventName, (event) => event.preventDefault(), true);
            });
            doc.addEventListener("keydown", (event) => {
              const key = (event.key || "").toLowerCase();
              if ((event.ctrlKey || event.metaKey) && ["c", "v", "x", "a"].includes(key)) {
                event.preventDefault();
              }
            }, true);
          } catch (error) {}
        })();
        </script>
        """,
        height=0,
    )
    if st.session_state.get("finished_status"):
        completion(st.session_state.finished_status)
    elif not st.session_state.get("candidate_id"):
        st.markdown('<div class="fym-subtitle">Խնդրում ենք ուշադիր կարդալ հրահանգները և պատասխանել բոլոր հարցերին։</div>', unsafe_allow_html=True)
        st.markdown('<div class="fym-card">Յուրաքանչյուր հարցում ընտրեք այն տարբերակը, որն առավել հաճախ է արտահայտում Ձեր մոտեցումը։ Յուրաքանչյուր հարցի համար ընտրեք միայն մեկ պատասխան՝ A կամ B։ Թեստը բաղկացած է 30 հարցից և պետք է ավարտվի 15 րոպեի ընթացքում։</div>', unsafe_allow_html=True)
        with st.form("candidate_details"):
            first = st.text_input("Անուն", key="cand_first_name")
            last = st.text_input("Ազգանուն", key="cand_last_name")
            position = st.text_input("Հաստիք", key="cand_position")
            start = st.form_submit_button("Սկսել թեստը", use_container_width=True)
        if start:
            if not first.strip() or not last.strip() or not position.strip():
                st.error("Խնդրում ենք լրացնել բոլոր դաշտերը։")
            else:
                cid = secrets.token_urlsafe(18)
                started = time.time()
                created = now_iso()
                st.session_state.candidate_id = cid
                st.session_state.candidate_started = started
                st.session_state.candidate_created = created
                st.session_state.candidate_first = first.strip()
                st.session_state.candidate_last = last.strip()
                st.session_state.candidate_position = position.strip()
                st.session_state.answers = {}
                for q in range(1, 31):
                    st.session_state.pop(f"answer_{q}", None)
                st.session_state.question_index = 0
                save_candidate(cid, first.strip(), last.strip(), position.strip(), created,
                               {}, "In Progress", started)
                st.rerun()
    else:
        cid = st.session_state.candidate_id
        started = st.session_state.candidate_started
        answers = st.session_state.answers
        elapsed = int(time.time() - started)
        remaining = max(0, DURATION_SECONDS - elapsed)
        if remaining <= 0:
            save_candidate(cid, st.session_state.candidate_first, st.session_state.candidate_last,
                           st.session_state.candidate_position, st.session_state.candidate_created,
                           answers, "Timed Out", started, now_iso())
            st.session_state.finished_status = "Timed Out"
            st.rerun()
        
        st_autorefresh(interval=1000, key="assessment_timer")
        mins, secs = divmod(remaining, 60)
        qidx = st.session_state.question_index
        
        st.markdown(f'<div class="fym-timer">Մնացած ժամանակը՝ {mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        st.progress(len(answers) / 30)
        st.caption(f"Հարց {qidx+1} / 30")
        st.markdown("---")
        
        a_text, b_text = QUESTIONS[qidx]
        current_ans = answers.get(str(qidx+1))
        
        radio_index = None
        if current_ans == "A":
            radio_index = 0
        elif current_ans == "B":
            radio_index = 1

        choice = st.radio(
            "Ընտրեք մեկ տարբերակ",
            ["A", "B"],
            format_func=lambda x: f"{x}. {a_text if x == 'A' else b_text}",
            index=radio_index,
            key=f"q_radio_{qidx+1}"
        )
        
        if choice and current_ans != choice:
            answers[str(qidx+1)] = choice
            st.session_state.answers = answers
            save_candidate(cid, st.session_state.candidate_first, st.session_state.candidate_last,
                           st.session_state.candidate_position, st.session_state.candidate_created,
                           answers, "In Progress", started)

        st.markdown("---")
        left, right = st.columns(2)
        with left:
            if qidx > 0 and st.button("Նախորդ", use_container_width=True):
                st.session_state.question_index -= 1
                st.rerun()
        with right:
            has_answered = bool(answers.get(str(qidx+1)))
            if qidx < 29:
                if st.button("Հաջորդ", use_container_width=True, disabled=not has_answered):
                    st.session_state.question_index += 1
                    st.rerun()
            else:
                if st.button("Ավարտել թեստը", use_container_width=True, disabled=(len(answers) != 30)):
                    save_candidate(cid, st.session_state.candidate_first, st.session_state.candidate_last,
                                   st.session_state.candidate_position, st.session_state.candidate_created,
                                   answers, "Completed", started, now_iso())
                    st.session_state.finished_status = "Completed"
                    st.rerun()
        if qidx == 29 and len(answers) != 30:
            st.caption("Ավարտելու համար անհրաժեշտ է պատասխանել բոլոր հարցերին։")

# HR Portal Navigation Button and Home button at the bottom
st.markdown("---")
col_home, col_portal = st.columns(2)
with col_home:
    if st.button("Գլխավոր էջ", key="bottom_home_button", use_container_width=True):
        for k in ["candidate_id","candidate_started","candidate_created","candidate_first",
                  "candidate_last","candidate_position","answers","question_index","finished_status"]:
            st.session_state.pop(k, None)
        for q in range(1, 31):
            st.session_state.pop(f"answer_{q}", None)
        st.session_state.active_page = "Թեստ"
        st.rerun()
with col_portal:
    nav_label = "HR Portal" if st.session_state.active_page == "Թեստ" else "Թեստ"
    if st.button(nav_label, key="bottom_portal_button", use_container_width=True):
        st.session_state.active_page = "HR մուտք" if st.session_state.active_page == "Թեստ" else "Թեստ"
        st.rerun()

st.markdown('<div class="small-note" style="text-align:center">FYM Hospitality Group</div>', unsafe_allow_html=True)
