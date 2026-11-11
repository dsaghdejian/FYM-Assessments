import os
import json
import time
import hashlib
import secrets
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
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
    page_title="FYM Hospitality Group | Թեստ",
    page_icon="F",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Clean, responsive, black-and-white presentation.
st.markdown("""
<style>
:root { color-scheme: light; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #ffffff !important; color: #171717 !important;
}
[data-testid="stHeader"] { background: #ffffff !important; }
.block-container { max-width: 900px; padding-top: 1rem; padding-bottom: 3rem; }
h1, h2, h3, p, label, span { color: #171717; }
.fym-logo-wrap { width:100%; display:flex; justify-content:center; align-items:center;
                 padding:.15rem 0 .7rem 0; }
.fym-kicker { text-align:center; color:#555; font-size:.78rem; letter-spacing:.12em;
              text-transform:uppercase; margin-bottom:.15rem; }
.fym-title { text-align:center; font-size:1.55rem; font-weight:700; margin:.1rem 0 .5rem; }
.fym-subtitle { text-align:center; color:#555; margin-bottom:1.1rem; }
hr { border:0; border-top:1px solid #dedede; margin:1.1rem 0; }
/* Keep every button visually identical in every interaction state. */
div.stButton > button, div.stDownloadButton > button,
div[data-testid="stFormSubmitButton"] > button,
button[kind="primary"], button[kind="secondary"] {
    border:1px solid #171717 !important; border-radius:7px !important;
    background:#171717 !important; color:#fff !important;
    min-height:2.65rem; font-weight:600; width:100%;
    transition:none !important; box-shadow:none !important;
}
div.stButton > button:hover, div.stButton > button:active,
div.stButton > button:focus, div.stButton > button:focus-visible,
div.stDownloadButton > button:hover, div.stDownloadButton > button:active,
div.stDownloadButton > button:focus, div.stDownloadButton > button:focus-visible,
div[data-testid="stFormSubmitButton"] > button:hover,
div[data-testid="stFormSubmitButton"] > button:active,
div[data-testid="stFormSubmitButton"] > button:focus,
div[data-testid="stFormSubmitButton"] > button:focus-visible,
div.stButton > button:disabled, div.stDownloadButton > button:disabled,
div[data-testid="stFormSubmitButton"] > button:disabled {
    background:#171717 !important; border-color:#171717 !important;
    color:#fff !important; filter:none !important; transform:none !important;
    box-shadow:none !important; outline:none !important;
}
div.stButton > button:disabled, div.stDownloadButton > button:disabled,
div[data-testid="stFormSubmitButton"] > button:disabled { opacity:.5 !important; }
/* White radio exterior with a black selected centre. */
div[data-testid="stRadio"] input[type="radio"] {
    appearance:none !important; -webkit-appearance:none !important;
    width:18px !important; height:18px !important; min-width:18px !important;
    border:2px solid #171717 !important; border-radius:50% !important;
    background:#fff !important; display:inline-grid !important;
    place-content:center !important; accent-color:#171717 !important;
}
div[data-testid="stRadio"] input[type="radio"]::before {
    content:""; width:8px; height:8px; border-radius:50%;
    transform:scale(0); background:#171717;
}
div[data-testid="stRadio"] input[type="radio"]:checked::before { transform:scale(1); }
div[data-testid="stRadio"] label { color:#171717 !important; background:#ffffff !important; }
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover { background:#ffffff !important; }
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
    background:#fff !important; border-color:#171717 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child > div {
    background:transparent !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] > div:first-child > div,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div,
div[data-testid="stRadio"] [role="radio"][aria-checked="true"] > div:first-child > div {
    background:#171717 !important;
}
div[data-testid="stRadio"] [role="radio"] > div:first-child {
    background:#ffffff !important; border:2px solid #171717 !important;
}
[data-testid="stProgressBar"] > div > div { background:#171717 !important; }
[data-testid="stMetric"] { border:1px solid #e5e5e5; border-radius:8px; padding:.75rem; }
.fym-card { border:1px solid #e2e2e2; border-radius:9px; padding:1rem 1.1rem;
            margin:.6rem 0; background:#fff; }
.fym-muted { color:#626262 !important; font-size:.9rem; }
.fym-timer { border:1px solid #222; border-radius:8px; padding:.45rem .8rem;
             text-align:center; font-weight:700; font-size:1.12rem; }
.small-note { font-size:.82rem; color:#666; }
[data-testid="stDataFrame"], [data-testid="stTable"] { max-width:100%; }
@media (max-width: 640px) {
  .block-container { padding-left:1rem; padding-right:1rem; }
  .fym-title { font-size:1.3rem; }
}
</style>
""", unsafe_allow_html=True)

def render_header():
    if LOGO_PATH.exists():
        left, center, right = st.columns([1, 3, 1])
        with center:
            # The logo keeps its original aspect ratio and is scaled down to fit.
            st.image(str(LOGO_PATH), width=400)
    else:
        st.markdown('<div class="fym-logo-wrap"><strong>FYM HOSPITALITY GROUP</strong></div>', unsafe_allow_html=True)
    st.markdown('<div class="fym-kicker">FYM HOSPITALITY GROUP</div>', unsafe_allow_html=True)
    st.markdown('<div class="fym-title">Թեստ</div>', unsafe_allow_html=True)

render_header()

# Candidate records are stored in SQLite. Set FYM_DB_PATH to a mounted persistent
# volume path when running on infrastructure that provides persistent storage.
def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            position TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            completed_at TEXT, status TEXT NOT NULL, answers TEXT NOT NULL,
            scores TEXT, dominant TEXT, duration_seconds INTEGER DEFAULT 0,
            tab_events TEXT NOT NULL DEFAULT '[]', tab_switches INTEGER DEFAULT 0,
            total_away_seconds REAL DEFAULT 0, longest_away_seconds REAL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        )""")
        columns = {row[1] for row in con.execute("PRAGMA table_info(candidates)").fetchall()}
        migrations = {
            "tab_events": "TEXT NOT NULL DEFAULT '[]'",
            "tab_switches": "INTEGER DEFAULT 0",
            "total_away_seconds": "REAL DEFAULT 0",
            "longest_away_seconds": "REAL DEFAULT 0",
        }
        for name, definition in migrations.items():
            if name not in columns:
                con.execute(f"ALTER TABLE candidates ADD COLUMN {name} {definition}")
        con.commit()
    # Ensure a usable default HR login exists on a fresh database.
    if not get_setting("admin_password_hash"):
        try:
            secret_password = st.secrets.get("FYM_HR_PASSWORD", "")
        except Exception:
            secret_password = ""
        initial = os.getenv("FYM_HR_PASSWORD") or secret_password or "1234"
        set_setting("admin_password_hash", hash_password(initial))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    with db() as con:
        con.execute("DELETE FROM candidates WHERE created_at < ?", (cutoff,))
        # Mark old unfinished sessions abandoned; a browser close cannot be
        # identified with certainty, so this is a stale-session classification.
        stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        con.execute("UPDATE candidates SET status='Abandoned' WHERE status='In Progress' AND updated_at < ?", (stale_cutoff,))
        con.commit()

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


init_db()


# Each row: (option A style, option B style). The supplied key's row 5
# marked A under both collaboration and accommodation. The wording of A
# describes joint problem-solving, so it is mapped to collaboration only.
STYLE_INFO = {
    "M": {
        "name": "Մրցակցություն",
        "meaning": "Մարդը հակված է վճռականորեն պաշտպանելու իր դիրքորոշումը և հետամուտ լինելու իր նպատակներին։ Այս մոտեցումը շեշտադրում է սեփական շահերի պաշտպանությունը։",
        "strengths": ["Արագ և վճռական որոշումներ կայացնելու պատրաստակամություն", "Սեփական դիրքորոշումը հստակ ներկայացնելու կարողություն", "Կարևոր սկզբունքներն ու չափանիշները պաշտպանելու հաստատակամություն"],
        "risks": ["Կարող է նվազեցնել մյուս կողմի ներգրավվածությունը", "Չափազանց հաճախ կիրառելիս կարող է սրել հարաբերությունները", "Կարող է սահմանափակել այլընտրանքային լուծումների քննարկումը"],
        "work": "Ղեկավարման ընթացքում կարող է դրսևորվել որպես ուղղակի և որոշումակենտրոն մոտեցում։ Թիմում օգտակար է հրատապության կամ հստակ չափանիշների դեպքում, սակայն կարևոր է լսել հակառակ կարծիքները։",
        "coaching": "Զարգացնել ակտիվ լսումը, հարցեր տալու և սեփական դիրքորոշումը հիմնավորելու՝ առանց մյուս կողմին անտեսելու հմտությունները։",
        "interview": ["Պատմե՛ք մի իրավիճակի մասին, երբ ստիպված եք եղել պաշտպանել ձեր դիրքորոշումը տարաձայնության պայմաններում։ Ինչպե՞ս եք հիմնավորել այն։", "Ինչպե՞ս եք ապահովում, որ վճռական որոշում կայացնելիս լսված լինեն նաև թիմի մյուս անդամները։"],
        "leadership": "Կարող է նախընտրել հստակ ուղղություն սահմանել և արագ որոշումներ կայացնել, հատկապես հրատապ իրավիճակներում։",
        "teamwork": "Կարող է առաջ մղել սեփական առաջարկը և պաշտպանել թիմի նպատակները․ կարևոր է նաև տարածք տալ գործընկերների կարծիքներին։",
        "conflict_behavior": "Հակված է բացահայտորեն դիմակայել տարաձայնությանը և պաշտպանել իր դիրքորոշումը։",
        "communication": "Ուղղակի, հաստատակամ և արդյունքի վրա կենտրոնացած հաղորդակցություն։",
        "environment": "Հստակ նպատակներով, որոշումների պատասխանատվության սահմանված շրջանակով և նախաձեռնություն ցուցաբերելու հնարավորությամբ միջավայր։"
    },
    "G": {
        "name": "Համագործակցություն",
        "meaning": "Մարդը ձգտում է բացահայտել երկու կողմերի մտահոգություններն ու շահերը և գտնել լուծում, որը հնարավորինս ամբողջականորեն հաշվի է առնում դրանք։",
        "strengths": ["Խնդրի խորքային պատճառները բացահայտելու կարողություն", "Վստահության և թիմային ներգրավվածության խթանում", "Երկարաժամկետ և փոխշահավետ լուծումների որոնում"],
        "risks": ["Քննարկումը կարող է երկար տևել", "Բոլոր կողմերի համաձայնությունը միշտ չէ, որ իրատեսական է", "Ժամանակի ճնշման պայմաններում կարող է դժվարանալ արագ որոշում կայացնելը"],
        "work": "Թիմում նպաստում է կարծիքների փոխանակմանը և համատեղ պատասխանատվությանը։ Ղեկավարման մեջ կարող է խրախուսել մասնակցային որոշումների կայացումը։",
        "coaching": "Սովորել սահմանել քննարկման ժամանակային սահմաններ և տարբերակել այն իրավիճակները, երբ անհրաժեշտ է արագ որոշում։",
        "interview": ["Նկարագրե՛ք մի դեպք, երբ տարաձայնության ժամանակ բացահայտել եք երկու կողմերի իրական կարիքները։", "Ինչպե՞ս եք գործում, երբ համատեղ լուծում գտնելը շատ ժամանակ է պահանջում։"],
        "leadership": "Կարող է խրախուսել մասնակցային որոշումներ և տարբեր տեսակետների ներառում։",
        "teamwork": "Ուժեղ կողմ կարող է լինել գործընկերների ներգրավումը, համագործակցությունը և ընդհանուր լուծումների որոնումը։",
        "conflict_behavior": "Փորձում է բացահայտել տարաձայնության հիմքում ընկած շահերն ու կարիքները՝ գտնելու երկու կողմերի համար ընդունելի լուծում։",
        "communication": "Հարցեր տվող, լսող և քննարկման միջոցով համաձայնության հասնելու հաղորդակցություն։",
        "environment": "Համագործակցային միջավայր՝ բաց քննարկումների, համատեղ որոշումների և բարդ խնդիրների խորքային լուծման հնարավորությամբ։"
    },
    "P": {
        "name": "Փոխզիջում",
        "meaning": "Մարդը փնտրում է միջանկյալ լուծում, որի դեպքում երկու կողմերն էլ որոշ չափով զիջում են և ստանում իրենց համար կարևոր արդյունքի մի մասը։",
        "strengths": ["Գործնական և համեմատաբար արագ համաձայնության հասնելու կարողություն", "Երկու կողմերի կարիքները հաշվի առնելու պատրաստակամություն", "Փակուղուց դուրս գալու և աշխատանքը շարունակելու հմտություն"],
        "risks": ["Լուծումը կարող է չանդրադառնալ խնդրի խորքային պատճառներին", "Երկու կողմերն էլ կարող են մասամբ դժգոհ մնալ", "Կարևոր սկզբունքները երբեմն կարող են զիջվել արագ համաձայնության համար"],
        "work": "Օգտակար է ռեսուրսների, ժամանակացույցերի կամ առաջնահերթությունների շուրջ բանակցություններում։ Թիմում օգնում է առաջ շարժվել, երբ ամբողջական համաձայնությունը դժվար է։",
        "coaching": "Մինչև զիջումների գնալը հստակեցնել՝ որոնք են չզիջվող պահանջները և արդյոք հնարավոր է ավելի ամբողջական լուծում։",
        "interview": ["Պատմե՛ք մի իրավիճակի մասին, երբ տարաձայնության ընթացքում գտել եք միջանկյալ լուծում։", "Ինչպե՞ս եք որոշում՝ որ հարցերում կարելի է զիջել, իսկ որոնք պետք է պահպանել։"],
        "leadership": "Կարող է նպաստել արագ համաձայնության և գործնական լուծումների՝ երբ կողմերի առաջնահերթությունները տարբեր են։",
        "teamwork": "Կարող է օգնել թիմին դուրս գալ փակուղուց և հավասարակշռել տարբեր պահանջները։",
        "conflict_behavior": "Փնտրում է միջանկյալ լուծում, որտեղ երկու կողմերն էլ որոշ չափով զիջում են։",
        "communication": "Գործնական, բանակցային և փոխադարձ զիջումների վրա կենտրոնացած հաղորդակցություն։",
        "environment": "Միջավայր, որտեղ անհրաժեշտ են բանակցություններ, ճկունություն և տարբեր թիմերի առաջնահերթությունների համաձայնեցում։"
    },
    "X": {
        "name": "Խուսափում",
        "meaning": "Մարդը կարող է հետաձգել կամ չմտնել տարաձայնության քննարկման մեջ՝ ժամանակ շահելու, լարվածությունը նվազեցնելու կամ տվյալ պահին հարցը երկրորդական համարելու նպատակով։",
        "strengths": ["Անհարկի սրացումից խուսափելու կարողություն", "Զգացմունքները կարգավորելու և մտածելու ժամանակ ստեղծելու հնարավորություն", "Երկրորդական հարցերի վրա ավելորդ ռեսուրս չծախսելու հմտություն"],
        "risks": ["Կարևոր խնդիրները կարող են մնալ չլուծված", "Հետաձգումը կարող է մեծացնել անորոշությունը", "Մյուս կողմը կարող է դա ընկալել որպես անտարբերություն կամ անհասանելիություն"],
        "work": "Կարճ դադարն օգտակար է բարձր լարվածության պահին։ Սակայն չքննարկված աշխատանքային խնդիրները կարող են ազդել համագործակցության և ծառայության որակի վրա։",
        "coaching": "Հետաձգելիս պայմանավորվել քննարկման հստակ ժամկետի շուրջ և վերադառնալ խնդրին՝ պատրաստված ու փաստերի հիման վրա։",
        "interview": ["Նկարագրե՛ք մի դեպք, երբ որոշել եք չարձագանքել տարաձայնությանը անմիջապես։ Ինչպե՞ս եք հետո վերադարձել հարցին։", "Ինչպե՞ս եք տարբերակում այն իրավիճակները, երբ դադարը օգտակար է, և երբ խնդիրը պետք է քննարկել։"],
        "leadership": "Կարող է նախընտրել դադար տալ լարված իրավիճակում և վերադառնալ հարցին, երբ հնարավոր է հանգիստ գնահատել այն։",
        "teamwork": "Կարող է նվազեցնել անմիջական լարվածությունը, սակայն կարևոր է չթողնել, որ չլուծված հարցերը կուտակվեն։",
        "conflict_behavior": "Կարող է հետաձգել կամ շրջանցել քննարկումը, երբ հարցը երկրորդական է կամ լարվածությունը բարձր է։",
        "communication": "Զուսպ և ոչ առճակատող հաղորդակցություն․ օգտակար է հստակ պայմանավորվել հետագա քննարկման մասին։",
        "environment": "Կանխատեսելի միջավայր՝ մտածելու ժամանակով և չլուծված հարցերին վերադառնալու հստակ գործընթացներով։"
    },
    "H": {
        "name": "Հարմարվողականություն",
        "meaning": "Մարդը կարևորում է դիմացինի կարիքներն ու հարաբերությունների պահպանումը և որոշ իրավիճակներում պատրաստ է զիջել սեփական նախընտրությունը։",
        "strengths": ["Հարաբերությունները պահպանելու և լարվածությունը մեղմելու կարողություն", "Ճկունություն և դիմացինի կարիքների նկատմամբ զգայունություն", "Համագործակցային միջավայրին նպաստելու պատրաստակամություն"],
        "risks": ["Կարող է անտեսել սեփական կարևոր կարիքները", "Կրկնվող զիջումները կարող են առաջացնել դժգոհություն", "Մյուսները կարող են չհասկանալ մարդու իրական դիրքորոշումը"],
        "work": "Թիմում կարող է աջակցել փոխօգնությանը և հաճախորդակենտրոն մոտեցմանը։ Կարևոր է, որ զիջումները չխաթարեն աշխատանքի չափանիշները կամ դերային պատասխանատվությունը։",
        "coaching": "Զարգացնել հարգալից սահմաններ դնելու և սեփական կարիքները հանգիստ ու հստակ արտահայտելու կարողությունը։",
        "interview": ["Պատմե՛ք մի իրավիճակի մասին, երբ զիջել եք՝ աշխատանքային հարաբերությունը պահպանելու համար։ Ինչպե՞ս եք գնահատել դրա հետևանքները։", "Ինչպե՞ս եք արտահայտում ձեր անհամաձայնությունը՝ միաժամանակ հարգելով դիմացինի կարիքները։"],
        "leadership": "Կարող է կարևորել հարաբերությունների պահպանումը և թիմի անդամների կարիքների նկատմամբ զգայունությունը։",
        "teamwork": "Կարող է աջակցել գործընկերներին, պահպանել համագործակցությունը և հարթել լարվածությունը։",
        "conflict_behavior": "Կարող է զիջել սեփական նախընտրությունը՝ դիմացինի համար կարևոր հարցը կամ աշխատանքային հարաբերությունը պահպանելու նպատակով։",
        "communication": "Դիվանագիտական, մեղմ և դիմացինի զգացմունքները հաշվի առնող հաղորդակցություն։",
        "environment": "Աջակցող և հարաբերությունների վրա հիմնված միջավայր՝ հստակ դերերով ու սահմաններով, որտեղ հնարավոր է բարձրաձայնել նաև սեփական կարիքները։"
    }
}
# Exact mapping transcribed from the supplied scoring key (A style, B style).
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
    dominant = [k for k, v in scores.items() if v == highest] if sum(scores.values()) else []
    return scores, percentages, dominant

def save_candidate(candidate_id, first, last, position, created, answers, status,
                   started_at, completed_at=None):
    scores, percentages, dominant = score_answers(answers)
    duration = max(0, int(time.time() - started_at)) if started_at else 0
    dominant_text = " / ".join(STYLE_INFO[k]["name"] for k in dominant) if answers else ""
    events = st.session_state.get("focus_events", [])
    switches = sum(1 for event in events if event.get("state") == "left")
    total_away = float(st.session_state.get("focus_total_away", 0.0))
    longest_away = float(st.session_state.get("focus_longest_away", 0.0))
    with db() as con:
        con.execute("""INSERT INTO candidates
        (id,first_name,last_name,position,created_at,updated_at,completed_at,status,
         answers,scores,dominant,duration_seconds,tab_events,tab_switches,
         total_away_seconds,longest_away_seconds)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
        updated_at=excluded.updated_at, completed_at=excluded.completed_at,
        status=excluded.status, answers=excluded.answers, scores=excluded.scores,
        dominant=excluded.dominant, duration_seconds=excluded.duration_seconds,
        tab_events=excluded.tab_events, tab_switches=excluded.tab_switches,
        total_away_seconds=excluded.total_away_seconds,
        longest_away_seconds=excluded.longest_away_seconds""",
        (candidate_id, first, last, position, created, now_iso(), completed_at,
         status, json.dumps(answers, ensure_ascii=False),
         json.dumps({"scores": scores, "percentages": percentages}, ensure_ascii=False),
         dominant_text, duration, json.dumps(events, ensure_ascii=False), switches,
         total_away, longest_away))
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

@st.cache_resource
def get_focus_tracker():
    """Best-effort browser focus tracker using a tiny local Streamlit component."""
    component_dir = Path(tempfile.mkdtemp(prefix="fym_focus_tracker_"))
    component_html = r"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<script>
(() => {
  let sequence = 0;
  let away = false;
  const send = (state) => {
    sequence += 1;
    const value = {id: String(Date.now()) + '-' + sequence,
                   state, timestamp: new Date().toISOString()};
    window.parent.postMessage({isStreamlitMessage:true,
      type:'streamlit:setComponentValue', value}, '*');
  };
  window.parent.postMessage({isStreamlitMessage:true,
    type:'streamlit:componentReady', apiVersion:1}, '*');
  window.parent.postMessage({isStreamlitMessage:true,
    type:'streamlit:setFrameHeight', height:0}, '*');
  try {
    const doc = window.parent.document;
    const win = window.parent;
    const leave = () => { if (!away) { away = true; send('left'); } };
    const back = () => { if (away) { away = false; send('returned'); } };
    doc.addEventListener('visibilitychange', () => {
      if (doc.visibilityState === 'hidden') leave(); else back();
    }, true);
    win.addEventListener('blur', leave, true);
    win.addEventListener('focus', back, true);
    win.addEventListener('pagehide', leave, true);
  } catch (e) { /* Browser isolation may prevent parent-page access. */ }
})();
</script></body></html>"""
    (component_dir / "index.html").write_text(component_html, encoding="utf-8")
    return components.declare_component("fym_focus_tracker", path=str(component_dir))


def install_assessment_controls():
    """Install best-effort copy/paste and text-selection deterrents in the app page."""
    components.html("""
    <script>
    (() => {
      try {
        const d = window.parent.document;
        if (d.__fymAssessmentHandlers) return;
        const block = e => e.preventDefault();
        const keys = e => {
          const key = (e.key || '').toLowerCase();
          if ((e.ctrlKey || e.metaKey) && ['c','v','x','a','p','s'].includes(key)) {
            e.preventDefault(); e.stopPropagation();
          }
        };
        ['copy','cut','paste','contextmenu','selectstart'].forEach(name =>
          d.addEventListener(name, block, true));
        d.addEventListener('keydown', keys, true);
        d.__fymAssessmentHandlers = {block, keys};
      } catch (e) { /* Browser restrictions can limit these controls. */ }
    })();
    </script>
    """, height=0, width=0)


def remove_assessment_controls():
    components.html("""
    <script>
    (() => {
      try {
        const d = window.parent.document;
        const h = d.__fymAssessmentHandlers;
        if (!h) return;
        ['copy','cut','paste','contextmenu','selectstart'].forEach(name =>
          d.removeEventListener(name, h.block, true));
        d.removeEventListener('keydown', h.keys, true);
        delete d.__fymAssessmentHandlers;
      } catch (e) {}
    })();
    </script>
    """, height=0, width=0)


def record_focus_event(event, candidate_id):
    if not isinstance(event, dict):
        return
    event_id = str(event.get("id", ""))
    state = event.get("state")
    stamp = event.get("timestamp") or now_iso()
    if not event_id or state not in {"left", "returned"}:
        return
    if event_id == st.session_state.get("last_focus_event_id"):
        return
    st.session_state.last_focus_event_id = event_id
    events = st.session_state.setdefault("focus_events", [])
    if state == "left":
        st.session_state.focus_away_started = stamp
        events.append({"state": "left", "timestamp": stamp})
    else:
        started = st.session_state.get("focus_away_started")
        duration = 0.0
        if started:
            try:
                duration = max(0.0, (datetime.fromisoformat(stamp.replace("Z", "+00:00")) -
                                      datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds())
            except Exception:
                duration = 0.0
        st.session_state.focus_total_away = st.session_state.get("focus_total_away", 0.0) + duration
        st.session_state.focus_longest_away = max(st.session_state.get("focus_longest_away", 0.0), duration)
        events.append({"state": "returned", "timestamp": stamp, "duration_seconds": round(duration, 1)})
        st.session_state.focus_away_started = None
    with db() as con:
        con.execute("""UPDATE candidates SET tab_events=?, tab_switches=?,
            total_away_seconds=?, longest_away_seconds=?, updated_at=? WHERE id=?""",
            (json.dumps(events, ensure_ascii=False),
             sum(1 for item in events if item.get("state") == "left"),
             float(st.session_state.get("focus_total_away", 0.0)),
             float(st.session_state.get("focus_longest_away", 0.0)), now_iso(), candidate_id))
        con.commit()


def duration_label(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def completion(status):
    st.markdown("## Շնորհակալություն։")
    st.markdown("### Թեստն ավարտված է։")
    st.write("Ձեր պատասխանները պահպանվել են։ Մարդկային ռեսուրսների (HR) բաժինը կդիտարկի Ձեր պատասխանները։ Տվյալները պաշտպանված են և հասանելի են միայն լիազորված HR աշխատակիցներին։")
    if status == "Timed Out":
        st.info("Ժամանակը լրացել է։ Պահպանվել են Ձեր արդեն տրված պատասխանները։")
    if st.button("Գլխավոր էջ", use_container_width=True):
        remove_assessment_controls()
        for k in ["candidate_id","candidate_started","candidate_created","candidate_first",
                  "candidate_last","candidate_position","answers","question_index","finished_status",
                  "focus_events","focus_total_away","focus_longest_away","focus_away_started",
                  "last_focus_event_id","current_question_choice"]:
            st.session_state.pop(k, None)
        st.rerun()

# Sidebar navigation. The HR area is separate and password protected.
st.sidebar.markdown("### FYM Hospitality Group")
page = st.sidebar.radio("Բաժին", ["Թեստ", "HR մուտք"], label_visibility="collapsed")

if page == "HR մուտք":
    st.markdown("## HR մուտք")
    if not st.session_state.get("hr_authenticated"):
        st.caption("Լիազորված HR աշխատակիցների համար։")
        with st.form("hr_login"):
            password = st.text_input("Գաղտնաբառ", type="password")
            submitted = st.form_submit_button("Մուտք գործել", use_container_width=True)
        if submitted:
            stored = get_setting("admin_password_hash")
            if stored and verify_password(password, stored):
                st.session_state.hr_authenticated = True
                st.rerun()
            else:
                st.error("Գաղտնաբառը սխալ է։")
    else:
        top_left, top_right = st.columns([4, 1])
        with top_left:
            st.markdown("## Թեկնածուների արդյունքներ")
        with top_right:
            if st.button("Ելք", use_container_width=True):
                st.session_state.hr_authenticated = False
                st.rerun()

        with st.expander("Փոխել HR գաղտնաբառը"):
            with st.form("change_password"):
                old = st.text_input("Գործող գաղտնաբառ", type="password")
                new = st.text_input("Նոր գաղտնաբառ", type="password")
                confirm = st.text_input("Կրկնել նոր գաղտնաբառը", type="password")
                change = st.form_submit_button("Պահպանել նոր գաղտնաբառը", use_container_width=True)
            if change:
                stored = get_setting("admin_password_hash")
                if not stored or not verify_password(old, stored):
                    st.error("Գործող գաղտնաբառը սխալ է։")
                elif len(new) < 8:
                    st.error("Նոր գաղտնաբառը պետք է պարունակի առնվազն 8 նիշ։")
                elif new != confirm:
                    st.error("Նոր գաղտնաբառերը չեն համընկնում։")
                else:
                    set_setting("admin_password_hash", hash_password(new))
                    st.success("Գաղտնաբառը փոխվել է։")

        records = fetch_candidates()
        completed_records = [r for r in records if r["status"] in ("Completed", "Timed Out")]
        durations = [r["duration_seconds"] for r in completed_records if r["duration_seconds"]]
        average_duration = int(sum(durations) / len(durations)) if durations else 0
        total = len(records)
        completed_count = sum(r["status"] == "Completed" for r in records)
        timed_out_count = sum(r["status"] == "Timed Out" for r in records)
        in_progress_count = sum(r["status"] == "In Progress" for r in records)
        abandoned_count = sum(r["status"] == "Abandoned" for r in records)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Թեկնածուներ", total)
        metric_cols[1].metric("Միջին տևողություն", duration_label(average_duration) if durations else "—")
        metric_cols[2].metric("Ավարտված ժամանակին", completed_count)
        metric_cols[3].metric("Ժամանակի ավարտին ուղարկված", timed_out_count)
        st.caption(f"Ընթացքում՝ {in_progress_count}  ·  Չավարտված՝ {abandoned_count}")

        if completed_records:
            st.markdown("### Ընդհանուր վիճակագրություն")
            score_sets = []
            dominant_counts = {}
            for record in completed_records:
                try:
                    parsed = json.loads(record.get("scores") or "{}")
                    score_sets.append(parsed.get("scores", {}))
                    dominant = record.get("dominant") or "Չի որոշվել"
                    dominant_counts[dominant] = dominant_counts.get(dominant, 0) + 1
                except (ValueError, TypeError):
                    continue
            if score_sets:
                avg_scores = {k: round(sum(float(item.get(k, 0)) for item in score_sets) / len(score_sets), 2)
                              for k in STYLE_INFO}
                avg_frame = pd.DataFrame({
                    "Ոճ": [STYLE_INFO[k]["name"] for k in STYLE_INFO],
                    "Միջին միավոր": [avg_scores[k] for k in STYLE_INFO]
                })
                distribution = pd.DataFrame({
                    "Գերիշխող ոճ": list(dominant_counts.keys()),
                    "Թեկնածուների քանակ": list(dominant_counts.values())
                })
                graph_left, graph_right = st.columns(2)
                with graph_left:
                    st.plotly_chart(px.bar(avg_frame, x="Միջին միավոր", y="Ոճ", orientation="h",
                                           range_x=[0, 13], title="Ոճերի միջին միավորներ",
                                           text="Միջին միավոր"), use_container_width=True)
                with graph_right:
                    if not distribution.empty:
                        st.plotly_chart(px.pie(distribution, names="Գերիշխող ոճ",
                                               values="Թեկնածուների քանակ", hole=.45,
                                               title="Գերիշխող ոճերի բաշխում"), use_container_width=True)
                if dominant_counts:
                    most_common = max(dominant_counts, key=dominant_counts.get)
                    st.write(f"**Ամենահաճախ հանդիպող գերիշխող ոճը՝** {most_common}")

        st.markdown("---")
        st.markdown("### Թեկնածուների ցանկ")
        filter_a, filter_b, filter_c = st.columns([2, 1, 1])
        with filter_a:
            search = st.text_input("Որոնել ըստ անվան, ազգանվան կամ հաստիքի")
        with filter_b:
            statuses = ["Բոլորը"] + sorted({r["status"] for r in records})
            status_filter = st.selectbox("Կարգավիճակ", statuses)
        with filter_c:
            sort_order = st.selectbox("Դասավորել", ["Նորերը սկզբում", "Հները սկզբում"])
        date_range = st.date_input("Ամսաթվի միջակայք", value=(datetime.now().date() - timedelta(days=RETENTION_DAYS), datetime.now().date()))
        filtered = []
        for record in records:
            haystack = f'{record["first_name"]} {record["last_name"]} {record["position"]}'.casefold()
            if search.casefold() not in haystack:
                continue
            if status_filter != "Բոլորը" and record["status"] != status_filter:
                continue
            if isinstance(date_range, tuple) and len(date_range) == 2:
                try:
                    record_date = datetime.fromisoformat(record["created_at"]).date()
                    if not (date_range[0] <= record_date <= date_range[1]):
                        continue
                except Exception:
                    continue
            filtered.append(record)
        if sort_order == "Հները սկզբում":
            filtered = list(reversed(filtered))

        if filtered:
            table_rows = [{
                "Անուն": r["first_name"], "Ազգանուն": r["last_name"],
                "Հաստիք": r["position"], "Ամսաթիվ": fmt_date(r["created_at"]),
                "Կարգավիճակ": r["status"], "Գերիշխող ոճ": r["dominant"] or "—"
            } for r in filtered]
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
            report_options = {
                f'{r["first_name"]} {r["last_name"]} — {r["position"]} — {fmt_date(r["created_at"])}': r["id"]
                for r in filtered
            }
            selected_label = st.selectbox("Ընտրել թեկնածուի ամբողջական հաշվետվությունը", list(report_options))
            selected = fetch_candidate(report_options[selected_label])
            if selected:
                st.markdown("---")
                st.markdown("## Թեկնածուի ամբողջական հաշվետվություն")
                info_cols = st.columns(3)
                info_cols[0].markdown(f'**Անուն, ազգանուն**  \n{selected["first_name"]} {selected["last_name"]}')
                info_cols[1].markdown(f'**Հաստիք**  \n{selected["position"]}')
                info_cols[2].markdown(f'**Կարգավիճակ**  \n{selected["status"]}')
                st.caption(f'Սկսել է՝ {fmt_date(selected["created_at"])}  ·  Ավարտել է՝ {fmt_date(selected["completed_at"])}  ·  Տևողություն՝ {duration_label(selected["duration_seconds"])}')
                answers = json.loads(selected.get("answers") or "{}")
                scores, percentages, dominant = score_answers(answers)
                rank_order = sorted(STYLE_INFO, key=lambda k: (-scores[k], STYLE_INFO[k]["name"]))
                st.markdown("### Արդյունքների գրաֆիկ")
                score_frame = pd.DataFrame({
                    "Ոճ": [STYLE_INFO[k]["name"] for k in rank_order],
                    "Միավոր": [scores[k] for k in rank_order],
                    "Տոկոս": [percentages[k] for k in rank_order],
                })
                chart_col, detail_col = st.columns([3, 2])
                with chart_col:
                    st.plotly_chart(px.bar(score_frame, x="Միավոր", y="Ոճ", orientation="h",
                                           range_x=[0, 13], text="Տոկոս",
                                           title="Հինգ ոճերի համեմատություն"), use_container_width=True)
                with detail_col:
                    if sum(scores.values()) > 0:
                        st.plotly_chart(px.pie(score_frame, names="Ոճ", values="Միավոր", hole=.42,
                                               title="Միավորների հարաբերակցություն"), use_container_width=True)
                    else:
                        st.info("Գրաֆիկը հասանելի կլինի պատասխանների պահպանումից հետո։")
                st.markdown("### Չափումների արդյունքներ")
                st.caption("Միավորը ցույց է տալիս տվյալ ոճին վերագրված ընտրված պատասխանների քանակը, իսկ տոկոսը՝ դրանց բաժինը բոլոր պատասխանների մեջ։")
                score_rows = [{
                    "Ոճ": STYLE_INFO[k]["name"], "Միավոր": scores[k],
                    "Տոկոս": f'{percentages[k]}%', "Դիրք": f'{rank_order.index(k)+1} / 5'
                } for k in rank_order]
                st.dataframe(pd.DataFrame(score_rows), use_container_width=True, hide_index=True)
                dominant_names = " / ".join(STYLE_INFO[k]["name"] for k in dominant) if dominant else "—"
                st.markdown(f"**Առաջատար ոճ՝ {dominant_names}**")

                st.markdown("### Գերիշխող ոճի մանրամասն մեկնաբանություն")
                for style_key in dominant:
                    info = STYLE_INFO[style_key]
                    with st.expander(f'{info["name"]} — առաջատար ոճ', expanded=True):
                        st.write(info["meaning"])
                        st.markdown("**Ուժեղ կողմեր**")
                        for item in info["strengths"]:
                            st.markdown(f"- {item}")
                        st.markdown("**Հնարավոր ռիսկեր / զարգացման կողմեր**")
                        for item in info["risks"]:
                            st.markdown(f"- {item}")
                        st.markdown("**Աշխատավայրում հնարավոր դրսևորումներ**")
                        st.write(info["work"])
                        st.markdown("**Ղեկավարման մոտեցում**")
                        st.write(info["leadership"])
                        st.markdown("**Թիմային համագործակցություն**")
                        st.write(info["teamwork"])
                        st.markdown("**Տարաձայնության կարգավորում**")
                        st.write(info["conflict_behavior"])
                        st.markdown("**Հաղորդակցման ոճ**")
                        st.write(info["communication"])
                        st.markdown("**Հնարավոր նախընտրելի աշխատանքային միջավայր**")
                        st.write(info["environment"])
                        st.markdown("**Զարգացման առաջարկ**")
                        st.write(info["coaching"])
                        st.markdown("**Հարցազրույցի առաջարկվող հարցեր**")
                        for question in info["interview"]:
                            st.markdown(f"- {question}")
                with st.expander("Մնացած ոճերի բացատրությունները"):
                    for style_key in rank_order:
                        if style_key in dominant:
                            continue
                        info = STYLE_INFO[style_key]
                        st.markdown(f'**{info["name"]} — {scores[style_key]} միավոր ({percentages[style_key]}%)**')
                        st.write(info["meaning"])
                        st.markdown("**Ուժեղ կողմեր:** " + "; ".join(info["strengths"]))
                        st.markdown("**Զարգացման կողմեր:** " + "; ".join(info["risks"]))

                st.markdown("### Պատասխաններ")
                with st.expander(f'Բացել բոլոր պատասխանները ({len(answers)} / 30)', expanded=False):
                    for number, (a_text, b_text) in enumerate(QUESTIONS, start=1):
                        chosen = answers.get(str(number))
                        answer_text = a_text if chosen == "A" else b_text if chosen == "B" else "Պատասխան չկա"
                        mapped_style = KEY[number][0 if chosen == "A" else 1] if chosen in ("A", "B") else None
                        style_text = STYLE_INFO[mapped_style]["name"] if mapped_style else "—"
                        st.markdown(f'**Հարց {number}.** {answer_text}')
                        st.caption(f'Ընտրված տարբերակ՝ {chosen or "—"}  ·  Հաշվարկված ոճ՝ {style_text}')
                        if number != len(QUESTIONS):
                            st.markdown("---")

                st.markdown("### Թեստի ընթացքի տվյալներ")
                st.write(f'Ժամանակի ավարտին ավտոմատ ուղարկում՝ {"Այո" if selected["status"] == "Timed Out" else "Ոչ"}')
                st.write(f'Արձանագրված էջից դուրս գալու դեպքեր՝ {selected.get("tab_switches", 0)}')
                st.write(f'Էջից դուրս գտնվելու ընդհանուր ժամանակ՝ {duration_label(selected.get("total_away_seconds", 0))}')
                st.write(f'Ամենաերկար բացակայություն՝ {duration_label(selected.get("longest_away_seconds", 0))}')
                try:
                    event_log = json.loads(selected.get("tab_events") or "[]")
                except (ValueError, TypeError):
                    event_log = []
                if event_log:
                    st.markdown("**Էջից դուրս գալու և վերադառնալու պատմություն**")
                    event_rows = [{
                        "Իրադարձություն": "Էջից դուրս է եկել" if e.get("state") == "left" else "Վերադարձել է",
                        "Ժամանակ": fmt_date(e.get("timestamp")),
                        "Տևողություն": duration_label(e.get("duration_seconds", 0)) if e.get("state") == "returned" else "—"
                    } for e in event_log]
                    st.dataframe(pd.DataFrame(event_rows), use_container_width=True, hide_index=True)
                else:
                    st.caption("Էջից դուրս գալու իրադարձություններ չեն արձանագրվել կամ դիտարկումը հասանելի չի եղել։")
                st.caption("Բրաուզերի թույլտվություններից կախված՝ ֆոկուսի կորուստը կարող է արձանագրվել ոչ ամբողջական։ Համակարգը չի որոշում, թե որ կայքն է բացվել։")
                st.caption("Արդյունքները նկարագրում են հարցաթերթիկում արտահայտված նախընտրությունները և չպետք է օգտագործվեն որպես աշխատանքի ընդունման միակ չափանիշ։")
        else:
            st.info("Համապատասխան թեկնածուներ չկան։")

        if records:
            export_rows = []
            for record in records:
                row = {
                    "ID": record["id"], "Անուն": record["first_name"],
                    "Ազգանուն": record["last_name"], "Հաստիք": record["position"],
                    "Սկիզբ": record["created_at"], "Ավարտ": record["completed_at"],
                    "Կարգավիճակ": record["status"], "Տևողություն (վրկ)": record["duration_seconds"],
                    "Գերիշխող ոճ": record["dominant"],
                    "Ֆոկուսի կորուստների քանակ": record.get("tab_switches", 0),
                    "Բացակայության ընդհանուր ժամանակ (վրկ)": record.get("total_away_seconds", 0),
                    "Երկար բացակայություն (վրկ)": record.get("longest_away_seconds", 0),
                }
                answers = json.loads(record.get("answers") or "{}")
                for number in range(1, 31):
                    chosen = answers.get(str(number), "")
                    row[f"Հարց {number}"] = chosen
                    row[f"Հարց {number} տեքստ"] = (QUESTIONS[number-1][0] if chosen == "A" else QUESTIONS[number-1][1] if chosen == "B" else "")
                score_values, percentage_values, _ = score_answers(answers)
                for style_key in STYLE_INFO:
                    row[f'{STYLE_INFO[style_key]["name"]} միավոր'] = score_values[style_key]
                    row[f'{STYLE_INFO[style_key]["name"]} տոկոս'] = percentage_values[style_key]
                export_rows.append(row)
            csv_data = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button("Արտահանել CSV", csv_data, "fym_tki_candidate_results.csv",
                               "text/csv", use_container_width=True)
        st.caption("Տվյալները պահվում են մինչև 5 տարի՝ ըստ հավելվածի պահպանման կարգավորման։")
        if Path(DB_PATH).exists():
            st.download_button(
                "Ներբեռնել տվյալների բազայի պահուստային պատճենը",
                data=Path(DB_PATH).read_bytes(),
                file_name="fym_candidate_data_backup.db",
                mime="application/octet-stream",
                use_container_width=True,
                help="Պահուստային ֆայլը պարունակում է թեկնածուների անձնական տվյալներ․ պահեք այն անվտանգ վայրում։"
            )

else:
    # Candidate flow
    if st.session_state.get("finished_status"):
        completion(st.session_state.finished_status)
    elif not st.session_state.get("candidate_id"):
        remove_assessment_controls()
        st.markdown('<div class="fym-subtitle">Խնդրում ենք ուշադիր կարդալ հրահանգները և պատասխանել բոլոր հարցերին։</div>', unsafe_allow_html=True)
        st.markdown('<div class="fym-card">Յուրաքանչյուր հարցում ընտրեք այն տարբերակը, որն առավել հաճախ է արտահայտում Ձեր մոտեցումը։ Յուրաքանչյուր հարցի համար ընտրեք միայն մեկ պատասխան՝ A կամ B։ Թեստը բաղկացած է 30 հարցից և պետք է ավարտվի 15 րոպեի ընթացքում։</div>', unsafe_allow_html=True)
        st.info("Գնահատման ընթացքում համակարգը կարող է արձանագրել, երբ թեստի էջը կորցնում է ֆոկուսը։ Այն չի որոշում, թե որ կայքն է բացվել։")
        with st.form("candidate_details"):
            first = st.text_input("Անուն")
            last = st.text_input("Ազգանուն")
            position = st.text_input("Հաստիք")
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
                st.session_state.question_index = 0
                st.session_state.focus_events = []
                st.session_state.focus_total_away = 0.0
                st.session_state.focus_longest_away = 0.0
                st.session_state.focus_away_started = None
                st.session_state.last_focus_event_id = None
                st.session_state.pop("current_question_choice", None)
                save_candidate(cid, first.strip(), last.strip(), position.strip(), created,
                               {}, "In Progress", started)
                st.rerun()
    else:
        cid = st.session_state.candidate_id
        install_assessment_controls()
        tracker = get_focus_tracker()
        focus_event = tracker(key="fym_focus_tracker", default=None)
        record_focus_event(focus_event, cid)
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
        # One shared widget key is explicitly reset from the answer dictionary
        # on every question render, preventing the prior question's choice from carrying over.
        st.session_state["current_question_choice"] = answers.get(str(qidx + 1))
        choice = st.radio("Ընտրեք մեկ տարբերակ", ["A", "B"],
                          format_func=lambda x: f"{x}. {a_text if x == 'A' else b_text}",
                          index=None, key="current_question_choice")
        if choice in ("A", "B"):
            answers[str(qidx + 1)] = choice
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
            if qidx < 29:
                if st.button("Հաջորդ", use_container_width=True, disabled=not bool(choice)):
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

st.markdown("---")
st.markdown('<div class="small-note" style="text-align:center">FYM Hospitality Group</div>', unsafe_allow_html=True)
