"""
Sadhaan - AI travel assistant for MSRTC (prototype)
Team Sadhaan - Seva First Innovation Challenge 2026

Two screens:
  1. Passenger chat  - WhatsApp-style chat in Marathi / Hindi / English
  2. Officer dashboard - demand + unmet-demand insights for MSRTC

All bus data here is SAMPLE data made for the demo, not real MSRTC data.
"""
import html
import json
import os
import random
import re
import datetime as dt
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ----------------------------------------------------------------------------
# Basic setup
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Sadhaan | MSRTC AI Assistant", page_icon="🚌", layout="wide")

DATA = Path(__file__).parent / "data"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def now_ist():
    return dt.datetime.now(IST)


@st.cache_data
def load_buses():
    return pd.read_csv(DATA / "buses.csv", dtype={"depart": str, "arrive": str})


buses = load_buses()

# ----------------------------------------------------------------------------
# Gemini (AI) set-up. If there is no key, the app still works with simple rules.
# ----------------------------------------------------------------------------
def get_secret(name, default=None):
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


GEMINI_KEY = get_secret("GEMINI_API_KEY")
GEMINI_MODEL = get_secret("GEMINI_MODEL", "gemini-2.5-flash")


@st.cache_resource
def gemini_client(key):
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception:
        return None


client = gemini_client(GEMINI_KEY)

# ----------------------------------------------------------------------------
# City names in English, Marathi and Hindi -> one standard name
# ----------------------------------------------------------------------------
CITY_ALIASES = {
    "Pune": ["pune", "poona", "puna", "पुणे", "पुना", "swargate", "shivajinagar"],
    "Satara": ["satara", "सातारा", "सतारा"],
    "Kolhapur": ["kolhapur", "कोल्हापूर", "कोल्हापुर"],
    "Navi Mumbai": ["navi mumbai", "vashi", "नवी मुंबई", "वाशी"],
    "Mumbai": ["mumbai", "bombay", "dadar", "mumbai central", "मुंबई", "दादर"],
    "Borivali": ["borivali", "borivli", "बोरिवली"],
    "Panvel": ["panvel", "पनवेल"],
    "Kalyan": ["kalyan", "कल्याण"],
    "Bhiwandi": ["bhiwandi", "भिवंडी"],
    "Virar": ["virar", "विरार"],
    "Murbad": ["murbad", "मुरबाड"],
    "Alibag": ["alibag", "alibaug", "अलिबाग"],
    "Pen": ["pen", "पेण"],
    "Palghar": ["palghar", "पालघर"],
    "Shahapur": ["shahapur", "शहापूर"],
    "Nashik": ["nashik", "nasik", "नाशिक", "नासिक"],
    "Shirdi": ["shirdi", "शिर्डी"],
    "Chhatrapati Sambhajinagar": ["sambhajinagar", "aurangabad", "संभाजीनगर", "औरंगाबाद"],
    "Solapur": ["solapur", "sholapur", "सोलापूर", "सोलापुर"],
    "Nagpur": ["nagpur", "नागपूर", "नागपुर"],
    "Amravati": ["amravati", "अमरावती"],
    "Sangli": ["sangli", "सांगली"],
    "Mahabaleshwar": ["mahabaleshwar", "महाबळेश्वर", "महाबलेश्वर"],
    "Thane": ["thane", "ठाणे"],
    "Baramati": ["baramati", "बारामती"],
    "Lonavala": ["lonavala", "lonavla", "लोणावळा", "लोनावला"],
    "Ratnagiri": ["ratnagiri", "रत्नागिरी"],
}

MARATHI_HINTS = ["udya", "sakali", "pahije", "kuthe", "aahe", "jaycha", "jayche", "dupari", "sandhyakali",
                 "ratri", "tikit", "mala", "ahe", "उद्या", "सकाळी", "पाहिजे", "कुठे", "आहे", "जायचे",
                 "दुपारी", "संध्याकाळी", "रात्री", "मला", "तक्रार", "आज"]
HINDI_HINTS = ["kal", "subah", "chahiye", "kahan", "jana", "hai", "mujhe", "dopahar", "shaam", "raat",
               "शिकायत", "कल", "सुबह", "चाहिए", "कहाँ", "जाना", "है", "मुझे", "दोपहर", "शाम", "रात"]

SLOT_WORDS = {
    "morning": ["morning", "sakali", "subah", "सकाळी", "सुबह"],
    "afternoon": ["afternoon", "dupari", "dopahar", "दुपारी", "दोपहर"],
    "evening": ["evening", "sandhyakali", "sham", "shaam", "संध्याकाळी", "शाम"],
    "night": ["night", "ratri", "raat", "रात्री", "रात"],
}
SLOT_HOURS = {"morning": (5, 12), "afternoon": (12, 17), "evening": (17, 21), "night": (21, 29)}

CONCESSIONS = {
    "none": ("Full fare", 1.0),
    "women_50": ("Women – 50% off", 0.5),
    "senior_50": ("Senior citizen 65–74 – 50% off", 0.5),
    "senior_free": ("Senior citizen 75+ – free", 0.0),
}

# ----------------------------------------------------------------------------
# Messages in 3 languages
# ----------------------------------------------------------------------------
T = {
    "en": {
        "welcome": "Namaskar! 🙏 I am <b>Sadhaan</b>, your MSRTC travel assistant.<br>Tell me where you want to go, e.g. <i>“Pune to Satara tomorrow morning”</i>. You can also track your bus or register a complaint.",
        "need_route": "Please tell me <b>from where</b> and <b>to where</b> you want to travel. Example: <i>Pune to Satara tomorrow</i>",
        "options": "Here are buses from <b>{f}</b> to <b>{t}</b> on <b>{d}</b>:",
        "pick": "Reply with the <b>number</b> of the bus you want (e.g. 1).",
        "no_slot": "⚠️ No bus in the <b>{s}</b> on this route. I have noted this for MSRTC. Other buses on this route:",
        "no_route": "😔 Sorry, there is no bus from <b>{f}</b> to <b>{t}</b> in our list yet. I have recorded your request so MSRTC can plan new services.",
        "ask_conc": "Do you have a concession?<br>1️⃣ No concession<br>2️⃣ Woman (50% off)<br>3️⃣ Senior citizen 65–74 (50% off)<br>4️⃣ Senior citizen 75+ (free)",
        "ticket": "✅ <b>Ticket booked!</b>",
        "track": "📍 Your bus <b>{b}</b> is near <b>{p}</b>, about <b>{m} minutes</b> from {s}. (live GPS)",
        "no_ticket": "You have no ticket yet. Tell me your route to book one first.",
        "complaint": "📝 Your complaint is registered. Complaint ID: <b>{c}</b>. MSRTC will update you on WhatsApp.",
        "bad_pick": "Please reply with a number from the list.",
        "confirm": "You selected:<br>🚌 <b>{f} → {t}</b> · {d}<br>🕒 {dep} from {stand} · {type} · ₹{fare}<br><br>Do you want to <b>book a ticket</b> for this bus?<br>1️⃣ Yes, book it<br>2️⃣ No, I was just checking",
        "not_booked": "👍 No problem, no ticket booked. Message me anytime to check another bus or book one.",
        "later_today": "🕒 No more buses today at this time. Showing <b>tomorrow's</b> buses instead.",
    },
    "mr": {
        "welcome": "नमस्कार! 🙏 मी <b>साधन</b>, तुमचा एसटी प्रवास सहाय्यक.<br>कुठे जायचे आहे ते सांगा, उदा. <i>“पुणे ते सातारा उद्या सकाळी”</i>. तुम्ही बस कुठे आहे ते पाहू शकता किंवा तक्रार नोंदवू शकता.",
        "need_route": "कृपया <b>कुठून</b> आणि <b>कुठे</b> जायचे आहे ते सांगा. उदा. <i>पुणे ते सातारा उद्या</i>",
        "options": "<b>{d}</b> रोजी <b>{f}</b> ते <b>{t}</b> बसेस:",
        "pick": "हवी असलेली बस निवडण्यासाठी <b>क्रमांक</b> पाठवा (उदा. 1).",
        "no_slot": "⚠️ या मार्गावर <b>{s}</b> बस नाही. ही माहिती एसटी महामंडळाला कळवली आहे. या मार्गावरील इतर बसेस:",
        "no_route": "😔 माफ करा, <b>{f}</b> ते <b>{t}</b> बस सध्या आमच्या यादीत नाही. तुमची मागणी नोंदवली आहे, जेणेकरून एसटी नवीन सेवा सुरू करू शकेल.",
        "ask_conc": "तुम्हाला सवलत आहे का?<br>1️⃣ सवलत नाही<br>2️⃣ महिला (50% सवलत)<br>3️⃣ ज्येष्ठ नागरिक 65–74 (50% सवलत)<br>4️⃣ ज्येष्ठ नागरिक 75+ (मोफत)",
        "ticket": "✅ <b>तिकीट बुक झाले!</b>",
        "track": "📍 तुमची बस <b>{b}</b> <b>{p}</b> जवळ आहे, {s} पासून सुमारे <b>{m} मिनिटे</b>. (लाईव्ह GPS)",
        "no_ticket": "तुमचे अजून तिकीट नाही. आधी मार्ग सांगा.",
        "complaint": "📝 तुमची तक्रार नोंदवली आहे. तक्रार क्रमांक: <b>{c}</b>. एसटी तुम्हाला WhatsApp वर कळवेल.",
        "bad_pick": "कृपया यादीतील क्रमांक पाठवा.",
        "confirm": "तुम्ही निवडलेली बस:<br>🚌 <b>{f} → {t}</b> · {d}<br>🕒 {dep}, {stand} · {type} · ₹{fare}<br><br>या बससाठी <b>तिकीट बुक</b> करायचे आहे का?<br>1️⃣ हो, बुक करा<br>2️⃣ नाही, फक्त माहिती हवी होती",
        "not_booked": "👍 ठीक आहे, तिकीट बुक केले नाही. दुसरी बस पाहायची किंवा बुक करायची असल्यास कधीही मेसेज करा.",
        "later_today": "🕒 आज या वेळेत आता बस नाही. <b>उद्याच्या</b> बसेस दाखवत आहे.",
    },
    "hi": {
        "welcome": "नमस्ते! 🙏 मैं <b>साधन</b> हूँ, आपका MSRTC यात्रा सहायक।<br>बताइए कहाँ जाना है, जैसे <i>“पुणे से सातारा कल सुबह”</i>। आप बस ट्रैक कर सकते हैं या शिकायत दर्ज कर सकते हैं।",
        "need_route": "कृपया बताइए <b>कहाँ से</b> और <b>कहाँ</b> जाना है। जैसे <i>पुणे से सातारा कल</i>",
        "options": "<b>{d}</b> को <b>{f}</b> से <b>{t}</b> की बसें:",
        "pick": "जो बस चाहिए उसका <b>नंबर</b> भेजिए (जैसे 1)।",
        "no_slot": "⚠️ इस रूट पर <b>{s}</b> कोई बस नहीं है। यह जानकारी MSRTC को भेज दी गई है। इस रूट की दूसरी बसें:",
        "no_route": "😔 माफ़ कीजिए, <b>{f}</b> से <b>{t}</b> की बस अभी हमारी सूची में नहीं है। आपकी मांग दर्ज कर ली गई है ताकि MSRTC नई सेवा शुरू कर सके।",
        "ask_conc": "क्या आपको रियायत मिलती है?<br>1️⃣ कोई रियायत नहीं<br>2️⃣ महिला (50% छूट)<br>3️⃣ वरिष्ठ नागरिक 65–74 (50% छूट)<br>4️⃣ वरिष्ठ नागरिक 75+ (मुफ़्त)",
        "ticket": "✅ <b>टिकट बुक हो गया!</b>",
        "track": "📍 आपकी बस <b>{b}</b> <b>{p}</b> के पास है, {s} से लगभग <b>{m} मिनट</b> दूर। (लाइव GPS)",
        "no_ticket": "आपका अभी कोई टिकट नहीं है। पहले रूट बताइए।",
        "complaint": "📝 आपकी शिकायत दर्ज हो गई है। शिकायत नंबर: <b>{c}</b>। MSRTC आपको WhatsApp पर बताएगा।",
        "bad_pick": "कृपया सूची में से नंबर भेजिए।",
        "confirm": "आपने यह बस चुनी:<br>🚌 <b>{f} → {t}</b> · {d}<br>🕒 {dep}, {stand} · {type} · ₹{fare}<br><br>क्या आप इस बस का <b>टिकट बुक</b> करना चाहते हैं?<br>1️⃣ हाँ, बुक करें<br>2️⃣ नहीं, सिर्फ़ जानकारी चाहिए थी",
        "not_booked": "👍 कोई बात नहीं, टिकट बुक नहीं किया। दूसरी बस देखनी हो या बुक करनी हो तो कभी भी मैसेज करें।",
        "later_today": "🕒 आज इस समय अब कोई बस नहीं है। <b>कल</b> की बसें दिखा रहे हैं।",
    },
}
SLOT_NAMES = {
    "en": {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "night"},
    "mr": {"morning": "सकाळी", "afternoon": "दुपारी", "evening": "संध्याकाळी", "night": "रात्री"},
    "hi": {"morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"},
}

# ----------------------------------------------------------------------------
# Understanding the message (AI first, simple rules as backup)
# ----------------------------------------------------------------------------
def find_city(name):
    if not name:
        return None
    n = str(name).strip().lower()
    best, best_len = None, 0
    for city, aliases in CITY_ALIASES.items():
        for a in aliases + [city.lower()]:
            hit = re.search(rf"\b{re.escape(a)}\b", n) if a.isascii() else a in n
            if hit and len(a) > best_len:
                best, best_len = city, len(a)
    return best or str(name).strip().title()


def has_word(t, words):
    """True if any word appears as a whole word (so 'kal' doesn't match 'Kalyan')."""
    for w in words:
        if w.isascii():
            if re.search(rf"\b{re.escape(w)}\b", t):
                return True
        elif w in t:
            return True
    return False


def detect_language(text):
    t = text.lower()
    if any(w in t.split() or w in t for w in MARATHI_HINTS if not w.isascii()) or \
       any(re.search(rf"\b{w}\b", t) for w in MARATHI_HINTS if w.isascii()):
        return "mr"
    if any(w in t for w in HINDI_HINTS if not w.isascii()) or \
       any(re.search(rf"\b{w}\b", t) for w in HINDI_HINTS if w.isascii()):
        return "hi"
    if re.search(r"[ऀ-ॿ]", text):
        return "mr"
    return "en"


def rule_parse(text):
    """Backup parser that works without any AI key."""
    t = text.lower()
    result = {"intent": "other", "from": None, "to": None, "day_offset": 0, "time_slot": None,
              "concession": None, "now": False, "language": detect_language(text)}

    if any(w in t for w in ["complaint", "complain", "takrar", "shikayat", "तक्रार", "शिकायत"]):
        result["intent"] = "complaint"
        return result
    if any(w in t for w in ["where is", "track", "kuthe aahe", "kahan hai", "कुठे आहे", "कहाँ है", "eta"]):
        result["intent"] = "track"
        return result
    if re.fullmatch(r"\s*(hi|hello|hey|namaskar|namaste|नमस्कार|नमस्ते)\W*\s*", t):
        result["intent"] = "greet"
        return result

    # find cities in the order they appear in the sentence
    spans = []
    for city, aliases in CITY_ALIASES.items():
        for a in set(aliases + [city.lower()]):
            pat = rf"\b{re.escape(a)}\b" if a.isascii() else re.escape(a)
            for m in re.finditer(pat, t):
                spans.append((m.start(), m.end(), city))
    spans.sort(key=lambda x: -(x[1] - x[0]))          # longest names first
    taken, kept = set(), []
    for a, b, city in spans:
        if not taken.intersection(range(a, b)):
            taken.update(range(a, b))
            kept.append((a, city))
    kept.sort()
    cities = []
    for _, c in kept:
        if c not in cities:
            cities.append(c)
    if len(cities) >= 2:
        result["from"], result["to"] = cities[0], cities[1]
    elif len(cities) == 1:
        result["to"] = cities[0]
    if cities:
        result["intent"] = "search"

    if has_word(t, ["tomorrow", "udya", "kal", "उद्या", "कल"]):
        result["day_offset"] = 1
    if has_word(t, ["parva", "parso", "परवा", "परसों"]):
        result["day_offset"] = 2
    for slot, words in SLOT_WORDS.items():
        if has_word(t, words):
            result["time_slot"] = slot
    result["now"] = has_word(t, ["now", "next bus", "abhi", "aatta", "atta", "आत्ता", "आता", "अभी"])
    if any(w in t for w in ["woman", "women", "lady", "mahila", "महिला"]):
        result["concession"] = "women_50"
    if any(w in t for w in ["senior", "jeshtha", "ज्येष्ठ", "वरिष्ठ"]):
        result["concession"] = "senior_50"
    return result


AI_PROMPT = """You help passengers of MSRTC (Maharashtra state buses).
Read the passenger message (it may be Marathi, Hindi, English or a mix, in any script)
and return ONLY JSON with these keys:
intent: one of "search", "complaint", "track", "greet", "other"
from: starting city in English (or null)
to: destination city in English (or null)
day_offset: 0 for today, 1 for tomorrow, 2 for day after tomorrow
time_slot: one of "morning", "afternoon", "evening", "night" or null
concession: one of "women_50", "senior_50", "senior_free" or null
now: true if they want the next bus / a bus right now, else false
language: "mr" for Marathi, "hi" for Hindi, "en" for English

Passenger message: {msg}"""


def ai_parse(text):
    if client is None:
        return None
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=AI_PROMPT.format(msg=text),
            config={"response_mime_type": "application/json", "temperature": 0},
        )
        data = json.loads(resp.text)
        data["from"] = find_city(data.get("from"))
        data["to"] = find_city(data.get("to"))
        data["day_offset"] = int(data.get("day_offset") or 0)
        if data.get("language") not in T:
            data["language"] = detect_language(text)
        return data
    except Exception as e:
        st.session_state["ai_error"] = str(e)[:200]
        return None


def understand(text):
    return ai_parse(text) or rule_parse(text)


def transcribe(audio_bytes):
    """Voice -> text using Gemini (only works with an API key)."""
    if client is None:
        return None
    try:
        from google.genai import types
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                      "Write down exactly what this person says, in the same language and script. Only the words."],
        )
        return resp.text.strip()
    except Exception as e:
        st.session_state["ai_error"] = str(e)[:200]
        return None

# ----------------------------------------------------------------------------
# Logging (this is what feeds the officer dashboard)
# ----------------------------------------------------------------------------
def log_search(frm, to, slot, lang, conc, result, booked=0):
    row = dict(timestamp=now_ist().strftime("%Y-%m-%d %H:%M"), from_city=frm, to_city=to,
               time_slot=slot or "any", language=lang, concession=conc or "none",
               result=result, booked=booked, channel="WhatsApp")
    st.session_state.live_log.append(row)
    st.session_state.last_log = len(st.session_state.live_log) - 1


def log_complaint(text):
    cid = f"C{random.randint(2000, 9999)}"
    st.session_state.live_complaints.append(dict(
        complaint_id=cid, timestamp=now_ist().strftime("%Y-%m-%d %H:%M"),
        category="Passenger message: " + text[:60], route="-", status="Open"))
    return cid

# ----------------------------------------------------------------------------
# Chat logic
# ----------------------------------------------------------------------------
def slot_of(hhmm):
    h = int(hhmm[:2])
    return "morning" if 5 <= h < 12 else "afternoon" if h < 17 else "evening" if h < 21 else "night"


def bus_list_html(options, lang):
    lines = []
    for i, b in enumerate(options, start=1):
        seats = f"{b['seats_left']} seats" if b["seats_left"] > 0 else "FULL"
        lines.append(f"<b>{i}.</b> 🕒 {b['depart']} → {b['arrive']} &nbsp;|&nbsp; {b['bus_type']} "
                     f"&nbsp;|&nbsp; ₹{b['fare']} &nbsp;|&nbsp; {seats}<br>"
                     f"<span class='small'>From {b['from_stand']}</span>")
    return "<br>".join(lines)


def make_ticket(lang):
    s = st.session_state
    b = s.selected
    label, mult = CONCESSIONS[s.concession or "none"]
    fare = int(round(b["fare"] * mult))
    pnr = f"SDN{random.randint(100000, 999999)}"
    seat = random.randint(1, 40)
    s.ticket = dict(b, pnr=pnr, seat=seat, paid=fare, travel_date=s.travel_date)
    if s.get("last_log") is not None and s.last_log < len(s.live_log):
        s.live_log[s.last_log]["booked"] = 1
    s.stage = "idle"
    return (f"{T[lang]['ticket']}<div class='ticket'>"
            f"🎫 PNR <b>{pnr}</b><br>🚌 {b['from_city']} → {b['to_city']} &nbsp;({b['bus_type']})<br>"
            f"📅 {s.travel_date} &nbsp; 🕒 {b['depart']} from {b['from_stand']}<br>"
            f"💺 Seat {seat} &nbsp; 🏷️ {label}<br>"
            f"💰 <b>₹{fare}</b> &nbsp;<span class='paid'>Paid via UPI ✓</span></div>"
            f"<span class='small'>Type “where is my bus” to track it live.</span>")


def reply_to(text):
    s = st.session_state
    msg = text.strip()

    low = msg.lower()
    YES = ["1", "yes", "y", "ok", "book", "ho", "haan", "han", "ha", "हो", "हाँ", "हां", "हा"]
    NO = ["2", "no", "n", "nahi", "nako", "नाही", "नको", "नहीं"]

    # Step 2: user is choosing a bus number
    if s.stage == "choose_bus" and msg.isdigit():
        n = int(msg)
        if 1 <= n <= len(s.options):
            b = s.options[n - 1]
            s.selected = b
            s.stage = "confirm_book"
            return T[s.lang]["confirm"].format(f=b["from_city"], t=b["to_city"], d=s.travel_date,
                                               dep=b["depart"], stand=b["from_stand"],
                                               type=b["bus_type"], fare=b["fare"])
        return T[s.lang]["bad_pick"]

    # Step 3: does the passenger really want to book?
    if s.stage == "confirm_book" and (low in YES or low in NO):
        if low in NO:
            s.stage = "idle"
            return T[s.lang]["not_booked"]
        if s.concession:
            return make_ticket(s.lang)
        s.stage = "choose_conc"
        return T[s.lang]["ask_conc"]

    # Step 4: user is choosing a concession
    if s.stage == "choose_conc" and msg.isdigit():
        n = int(msg)
        if 1 <= n <= 4:
            s.concession = ["none", "women_50", "senior_50", "senior_free"][n - 1]
            return make_ticket(s.lang)
        return T[s.lang]["bad_pick"]

    # Step 1: understand a new message
    p = understand(msg)
    lang = p.get("language", "en")
    s.lang = lang
    intent = p.get("intent")

    if intent == "greet":
        return T[lang]["welcome"]

    if intent == "complaint":
        cid = log_complaint(msg)
        return T[lang]["complaint"].format(c=cid)

    if intent == "track":
        if not s.ticket:
            return T[lang]["no_ticket"]
        stops = {"Pune": "Katraj", "Satara": "Shirwal", "Mumbai": "Sion", "Nashik": "Dwarka Circle",
                 "Kolhapur": "Tavde Hotel", "Thane": "Kapurbawdi", "Borivali": "Dahisar Check Naka",
                 "Panvel": "Kalamboli", "Kalyan": "Shilphata", "Navi Mumbai": "Turbhe",
                 "Bhiwandi": "Kalher", "Virar": "Vasai Phata"}
        place = stops.get(s.ticket["from_city"], "the highway")
        return T[lang]["track"].format(b=s.ticket["bus_id"], p=place, m=random.randint(6, 25),
                                       s=s.ticket["from_stand"])

    if intent == "search" or p.get("from") or p.get("to"):
        frm, to = p.get("from"), p.get("to")
        if not frm or not to:
            return T[lang]["need_route"]
        slot = p.get("time_slot")
        s.time_slot = slot
        s.concession = p.get("concession")
        date = (now_ist() + dt.timedelta(days=p.get("day_offset", 0))).strftime("%d %b %Y")
        s.travel_date = date

        route = buses[(buses.from_city == frm) & (buses.to_city == to)].sort_values("depart")
        if route.empty:
            log_search(frm, to, slot, lang, s.concession, "unmet")
            s.stage = "idle"
            return T[lang]["no_route"].format(f=frm, t=to)

        note = ""
        if p.get("day_offset", 0) == 0:
            now_hm = now_ist().strftime("%H:%M")
            upcoming = route[route.depart >= now_hm]
            if slot:
                upcoming = upcoming[upcoming.depart.apply(slot_of) == slot]
            if upcoming.empty:
                note = T[lang]["later_today"] + "<br><br>"
                date = (now_ist() + dt.timedelta(days=1)).strftime("%d %b %Y")
                s.travel_date = date
            else:
                route = route[route.depart >= now_hm]
        head = T[lang]["options"].format(f=frm, t=to, d=date)
        options = route
        if slot:
            in_slot = route[route.depart.apply(slot_of) == slot]
            if in_slot.empty:
                log_search(frm, to, slot, lang, s.concession, "unmet")
                head = T[lang]["no_slot"].format(s=SLOT_NAMES[lang][slot])
            else:
                options = in_slot
                log_search(frm, to, slot, lang, s.concession, "found")
        else:
            log_search(frm, to, slot, lang, s.concession, "found")
        head = note + head
        options = options[options.seats_left > 0].head(4)
        s.options = options.to_dict("records")
        s.stage = "choose_bus"
        return f"{head}<br><br>{bus_list_html(s.options, lang)}<br><br>{T[lang]['pick']}"

    return T[lang]["welcome"]

# ----------------------------------------------------------------------------
# Session memory
# ----------------------------------------------------------------------------
defaults = dict(messages=[("bot", T["en"]["welcome"], None)], stage="idle", options=[], selected=None,
                concession=None, time_slot=None, travel_date=None, ticket=None, lang="en",
                live_log=[], live_complaints=[], last_audio=None, last_log=None)
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def handle(text):
    t = now_ist().strftime("%H:%M")
    st.session_state.messages.append(("user", text, t))
    st.session_state.messages.append(("bot", reply_to(text), t))

# ----------------------------------------------------------------------------
# Look and feel (shared)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
.small {font-size:12px;color:#667781}
.ticket {background:#FFF7EC;border:1px dashed #F28C28;border-radius:8px;padding:8px 10px;margin:6px 0}
.paid {color:#0a7d34;font-weight:600}
</style>
""", unsafe_allow_html=True)

# WhatsApp-style look, used only on the chat screen
CHAT_CSS = """
<style>
/* page = WhatsApp wallpaper */
.stApp {background-color:#EFEAE2;
  background-image:radial-gradient(rgba(0,0,0,.035) 1.2px, transparent 1.2px),
                   radial-gradient(rgba(0,0,0,.025) 1px, transparent 1px);
  background-size:26px 26px, 13px 13px; background-position:0 0, 6px 6px;}
header[data-testid="stHeader"] {background:transparent; height:0}
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display:none !important}
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {color:#fff !important; z-index:60}
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg {color:#fff !important; fill:#fff !important}
[data-testid="stMainBlockContainer"], .block-container {
  padding:0 0 120px 0 !important; max-width:100% !important;}
[data-testid="stMainBlockContainer"] iframe {display:block}

/* top bar */
.wa-top {position:sticky; top:0; z-index:50; background:#008069; color:#fff;
  display:flex; align-items:center; gap:14px; padding:10px 22px 10px 60px; box-shadow:0 1px 3px rgba(0,0,0,.2)}
.wa-top .back {font-size:22px; opacity:.9}
.wa-top .avatar {width:42px; height:42px; border-radius:50%; background:#F28C28; display:flex;
  align-items:center; justify-content:center; font-size:22px; flex-shrink:0}
.wa-top .name {font-weight:600; font-size:17px; line-height:1.2}
.wa-top .status {font-size:13px; opacity:.85}
.wa-top .icons {margin-left:auto; display:flex; gap:24px; font-size:19px; opacity:.95}

/* message area */
.wa-chat {padding:14px 7% 10px 7%}
.wa-chip {text-align:center; margin:8px 0 12px}
.wa-chip span {background:#fff; color:#54656F; font-size:12.5px; padding:5px 12px; border-radius:8px;
  box-shadow:0 1px .5px rgba(0,0,0,.13)}
.wa-note {background:#FFEECD; color:#54656F; font-size:12.5px; text-align:center; max-width:560px;
  margin:0 auto 14px; padding:7px 12px; border-radius:8px; box-shadow:0 1px .5px rgba(0,0,0,.13)}
.row {display:flex; margin:3px 0}
.msg {position:relative; max-width:65%; padding:7px 10px 8px 10px; border-radius:8px; font-size:15px;
  line-height:1.45; color:#111B21; box-shadow:0 1px .5px rgba(0,0,0,.13); word-wrap:break-word}
.bot {background:#fff; margin-right:auto; border-top-left-radius:0}
.user {background:#D9FDD3; margin-left:auto; border-top-right-radius:0}
.bot::before {content:""; position:absolute; top:0; left:-8px; border-width:0 8px 10px 0;
  border-style:solid; border-color:transparent #fff transparent transparent}
.user::before {content:""; position:absolute; top:0; right:-8px; border-width:0 0 10px 8px;
  border-style:solid; border-color:transparent transparent transparent #D9FDD3}
.meta {float:right; margin:6px 0 -4px 12px; font-size:11px; color:#667781; white-space:nowrap}
.tick {color:#53BDEB; font-weight:700; letter-spacing:-3px; margin-left:3px}

/* bottom typing bar */
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {background:#F0F2F5 !important}
[data-testid="stBottomBlockContainer"] {padding:10px 7% 14px 7% !important; max-width:100% !important}
[data-testid="stChatInput"] {background:#fff !important; border:none !important; border-radius:24px !important;
  box-shadow:none !important}
[data-testid="stChatInput"] textarea {font-size:15px !important}
[data-testid="stChatInput"] *, [data-testid="stChatInput"]:focus-within {border-color:transparent !important; outline:none !important; box-shadow:none !important}
[data-testid="stChatInputSubmitButton"] {background:#00A884 !important; border-radius:50% !important;
  color:#fff !important}
[data-testid="stChatInputSubmitButton"] svg {fill:#fff !important; color:#fff !important}

@media (max-width: 700px) {
  .wa-chat {padding:10px 10px} .msg {max-width:85%} .wa-top {padding:8px 12px 8px 56px}
  .wa-top .icons {gap:16px} [data-testid="stBottomBlockContainer"] {padding:8px 10px 12px !important}
}
</style>
"""

# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🚌 Sadhaan")
    st.caption("AI travel assistant for MSRTC · Prototype")
    page = st.radio("Choose screen", ["💬 Passenger chat", "📊 MSRTC officer dashboard"])
    st.divider()
    if page.startswith("💬"):
        st.markdown("**Try these messages**")
        examples = ["Pune to Satara tomorrow morning", "पुणे ते सातारा उद्या सकाळी",
                    "Thane to Borivali now", "दादर ते पनवेल उद्या सकाळी",
                    "Satara se Pune kal shaam", "Kalyan to Murbad",
                    "Pune to Baramati", "where is my bus", "complaint: bus was 2 hours late"]
        for ex in examples:
            if st.button(ex, width="stretch"):
                handle(ex)
        st.markdown("**🎙️ Speak instead of typing**")
        if hasattr(st, "audio_input"):
            audio = st.audio_input("Record (Marathi / Hindi / English)")
            if audio is not None:
                data = audio.getvalue()
                if data != st.session_state.last_audio:
                    st.session_state.last_audio = data
                    said = transcribe(data)
                    if said:
                        handle(said)
                    else:
                        st.info("Voice needs the Gemini API key. Please type for now.")
        if st.button("🔄 Start new chat", width="stretch"):
            for k, v in defaults.items():
                if k not in ("live_log", "live_complaints"):
                    st.session_state[k] = v if not isinstance(v, list) else list(v)
            st.rerun()
        st.divider()
    if client:
        st.success(f"AI engine: Gemini ({GEMINI_MODEL})")
    else:
        st.warning("AI engine: offline rules (add GEMINI_API_KEY for full AI)")
    if st.session_state.get("ai_error"):
        st.caption("Last AI error (using backup rules): " + st.session_state["ai_error"])
    st.caption("⚠️ Demo uses SAMPLE bus data, not real MSRTC data.")

# ----------------------------------------------------------------------------
# Screen 1: Passenger chat (WhatsApp style, full screen)
# ----------------------------------------------------------------------------
if page.startswith("💬"):
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

    typed = st.chat_input("Type a message")
    if typed:
        handle(typed)

    bubbles = []
    for who, text, t in st.session_state.messages:
        body = html.escape(text) if who == "user" else text
        meta = f"<span class='meta'>{t or ''}"
        meta += "<span class='tick'>✓✓</span></span>" if who == "user" else "</span>"
        bubbles.append(f"<div class='row'><div class='msg {who}'>{body}{meta}</div></div>")

    st.markdown(
        "<div class='wa-top'><div class='avatar'>🚌</div>"
        "<div><div class='name'>Sadhaan · MSRTC</div>"
        "<div class='status'>online · Marathi, हिंदी, English</div></div>"
        "<div class='icons'><span>📹</span><span>📞</span><span>⋮</span></div></div>"
        "<div class='wa-chat'>"
        "<div class='wa-chip'><span>TODAY</span></div>"
        "<div class='wa-note'>🔒 Prototype for the Seva First Innovation Challenge. "
        "Bus timings and fares are sample data.</div>"
        f"{''.join(bubbles)}</div>",
        unsafe_allow_html=True)

    # keep the newest message in view
    scroll_js = (
        f"""<script>
        // {len(st.session_state.messages)}
        const d = window.parent.document;
        function go() {{
          const els = d.querySelectorAll('[data-testid="stMain"], section.stMain, [data-testid="stAppViewContainer"]');
          els.forEach(e => e.scrollTo({{top: e.scrollHeight, behavior: 'smooth'}}));
          window.parent.scrollTo(0, d.body.scrollHeight);
        }}
        setTimeout(go, 150); setTimeout(go, 600);
        </script>"""
    )
    if hasattr(st, "iframe"):
        st.iframe(scroll_js, height=1)
    else:
        components.html(scroll_js, height=0)

# ----------------------------------------------------------------------------
# Screen 2: Officer dashboard
# ----------------------------------------------------------------------------
else:
    st.title("📊 MSRTC Officer Dashboard")
    st.caption("Pilot division · last 30 days · simulated demand data + live searches from this demo")

    log = pd.read_csv(DATA / "demand_log.csv")
    if st.session_state.live_log:
        log = pd.concat([log, pd.DataFrame(st.session_state.live_log)], ignore_index=True)
    comp = pd.read_csv(DATA / "complaints.csv")
    if st.session_state.live_complaints:
        comp = pd.concat([comp, pd.DataFrame(st.session_state.live_complaints)], ignore_index=True)
    log["route"] = log.from_city + " → " + log.to_city
    log["date"] = pd.to_datetime(log.timestamp).dt.date

    unmet = log[log.result == "unmet"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Passenger searches", f"{len(log):,}")
    c2.metric("Tickets booked", f"{int(log.booked.sum()):,}")
    c3.metric("Searches with NO bus", f"{len(unmet):,}", f"{len(unmet) / len(log):.0%} of searches",
              delta_color="inverse")
    c4.metric("Open complaints", int((comp.status != "Resolved").sum()))

    st.subheader("🚨 Unmet demand: people searched, but no bus was available")
    gaps = (unmet.groupby(["route", "time_slot"]).size().reset_index(name="searches")
            .sort_values("searches", ascending=False).head(8))
    gaps["where"] = gaps.route + " (" + gaps.time_slot + ")"
    st.altair_chart(
        alt.Chart(gaps).mark_bar(color="#F28C28", cornerRadiusEnd=4).encode(
            x=alt.X("searches:Q", title="Searches with no bus"),
            y=alt.Y("where:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
            tooltip=["route", "time_slot", "searches"]).properties(height=280),
        width="stretch")

    st.subheader("🤖 AI recommendations for new trips")
    for _, g in gaps.head(3).iterrows():
        extra = max(1, int(g.searches // 40))
        st.markdown(f"- Add **{extra} extra {g.time_slot} trip(s)** on **{g.route}**. "
                    f"{g.searches} passengers searched in the last 30 days and found no bus.")

    a, b = st.columns(2)
    with a:
        st.subheader("Most searched routes")
        top = log.groupby("route").size().reset_index(name="searches").nlargest(8, "searches")
        st.altair_chart(
            alt.Chart(top).mark_bar(color="#1B2A5C", cornerRadiusEnd=4).encode(
                x=alt.X("searches:Q", title="Searches"), y=alt.Y("route:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
                tooltip=["route", "searches"]).properties(height=280),
            width="stretch")
    with b:
        st.subheader("Searches per day")
        daily = log.groupby("date").size().reset_index(name="searches")
        st.altair_chart(
            alt.Chart(daily).mark_line(color="#1B2A5C", point=True).encode(
                x=alt.X("date:T", title=None), y=alt.Y("searches:Q", title="Searches"),
                tooltip=["date:T", "searches"]).properties(height=280),
            width="stretch")

    a, b = st.columns(2)
    with a:
        st.subheader("Language used by passengers")
        names = {"mr": "Marathi", "hi": "Hindi", "en": "English"}
        lang = log.language.map(names).value_counts().reset_index()
        lang.columns = ["language", "searches"]
        st.altair_chart(
            alt.Chart(lang).mark_bar(color="#1B2A5C", cornerRadiusEnd=4).encode(
                x=alt.X("searches:Q", title="Searches"), y=alt.Y("language:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)))
            .properties(height=160), width="stretch")
    with b:
        st.subheader("Concessions used")
        cn = log.concession.map({k: v[0] for k, v in CONCESSIONS.items()}).value_counts().reset_index()
        cn.columns = ["concession", "searches"]
        st.altair_chart(
            alt.Chart(cn).mark_bar(color="#1B2A5C", cornerRadiusEnd=4).encode(
                x=alt.X("searches:Q", title="Searches"), y=alt.Y("concession:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)))
            .properties(height=160), width="stretch")

    st.subheader("📝 Latest complaints")
    st.dataframe(comp.sort_values("timestamp", ascending=False).head(10), hide_index=True,
                 width="stretch")
