import streamlit as st
import json
import random
import os
from groq import Groq

# --- 1. AYARLAR VE API KURULUMU ---
st.set_page_config(page_title="FSP Terminologie Trainer", page_icon="💊", layout="centered")

# BURAYA API ANAHTARINI GİRİYORUZ (Senin dosyandan aldığım örnek anahtar)
# Güvenlik notu: Gerçek projelerde bu st.secrets içinde saklanır.
API_KEY = "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" 

# Groq İstemcisi
try:
    client = Groq(api_key=API_KEY)
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False

# --- 2. VERİ YÜKLEME ---
@st.cache_data
def load_data():
    try:
        with open("terminoloji.json", "r", encoding="utf-8") as f:
            terminoloji_data = json.load(f)
        
        # Sadece terim havuzlarını hazırla
        all_latin_terms = list(terminoloji_data.keys())
        all_german_terms = []
        for v in terminoloji_data.values():
            if isinstance(v, list): all_german_terms.extend(v)
            else: all_german_terms.append(v)
            
        return terminoloji_data, all_latin_terms, all_german_terms
    except FileNotFoundError:
        st.error("❌ 'terminoloji.json' bulunamadı!")
        return {}, [], []

terminoloji_data, all_latin_terms, all_german_terms = load_data()

# --- 3. AI KLİNİK BAĞLAM ÜRETİCİ (GERÇEK LLAMA) ---
def get_ai_context(term, meaning):
    """
    Groq API kullanarak terim için gerçekçi, tıbbi bir cümle üretir.
    """
    if not AI_AVAILABLE:
        return f"Beispiel: Der Begriff '{term}' bedeutet '{meaning}'."

    prompt = f"""
    Erstelle einen kurzen, realistischen klinischen Satz auf Deutsch (für einen Arztbrief oder Anamnese).
    Verwende den Fachbegriff '{term}' (Bedeutung: {meaning}).
    Der Satz soll medizinisch professionell klingen. Gib NUR den Satz aus.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Hızlı ve zeki model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Klinischer Kontext konnte nicht geladen werden. ({term})"

# --- 4. SORU HAZIRLAMA MOTORU ---
def generate_quiz_session(count):
    queue = []
    keys = list(terminoloji_data.keys())
    
    # İstenen sayıda rastgele terim seç
    selected_keys = random.sample(keys, min(count, len(keys)))
    
    for lat in selected_keys:
        german_meanings = terminoloji_data[lat]
        direction = random.choice(["L-D", "D-L"]) # Latince->Almanca veya tam tersi
        
        if direction == "L-D":
            # Soru: Latince, Şıklar: Almanca
            question_text = f"Was bedeutet '{lat}' auf Deutsch?"
            correct = german_meanings[0]
            distractor_pool = all_german_terms
            term_for_ai = lat
            meaning_for_ai = correct
        else:
            # Soru: Almanca, Şıklar: Latince
            german_q = random.choice(german_meanings)
            question_text = f"Was ist der Fachbegriff für '{german_q}'?"
            correct = lat
            distractor_pool = all_latin_terms
            term_for_ai = correct
            meaning_for_ai = german_q
            
        # Şık Üretimi (1 Doğru + 4 Yanlış)
        options = [correct]
        while len(options) < 5:
            dist = random.choice(distractor_pool)
            if dist not in options and dist not in german_meanings: # Eş anlamlıları şıkka koyma
                options.append(dist)
        
        random.shuffle(options)
        
        queue.append({
            "question": question_text,
            "correct": correct,
            "options": options,
            "term_for_ai": term_for_ai,     # AI'ya gönderilecek terim
            "meaning_for_ai": meaning_for_ai # AI'ya gönderilecek anlam
        })
        
    return queue

# --- 5. SESSION STATE ---
if 'quiz_active' not in st.session_state: st.session_state.quiz_active = False
if 'queue' not in st.session_state: st.session_state.queue = []
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'score' not in st.session_state: st.session_state.score = 0
if 'feedback' not in st.session_state: st.session_state.feedback = None # (msg_type, msg, ai_context)

# --- 6. ARAYÜZ ---
st.title("💊 FSP Terminologie: Intensivtraining")

# GİRİŞ EKRANI
if not st.session_state.quiz_active:
    st.markdown("### Willkommen Dr. Emre!")
    st.write("Dieses Modul konzentriert sich ausschließlich auf die medizinische Terminologie.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        q_count = st.select_slider("Wie viele Fragen möchten Sie lösen?", options=[5, 10, 20, 40, 50], value=10)
    
    if st.button("Starten ▶️", use_container_width=True):
        st.session_state.queue = generate_quiz_session(q_count)
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.quiz_active = True
        st.session_state.feedback = None
        st.rerun()

# SINAV EKRANI
else:
    # Bitiş Kontrolü
    if st.session_state.current_idx >= len(st.session_state.queue):
        st.success("🏁 Training Abgeschlossen!")
        
        score = st.session_state.score
        total = len(st.session_state.queue)
        percent = (score / total) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Gesamtfragen", total)
        col2.metric("Richtig", score)
        col3.metric("Erfolg", f"%{percent:.1f}")
        
        if percent < 60:
            st.warning("⚠️ Empfehlung: Bitte wiederholen Sie die Fehler.")
        else:
            st.balloons()
            st.markdown("### 🌟 Ausgezeichnet!")
            
        if st.button("Neues Training 🔄"):
            st.session_state.quiz_active = False
            st.rerun()
            
    else:
        # Soru Gösterimi
        q_data = st.session_state.queue[st.session_state.current_idx]
        total = len(st.session_state.queue)
        
        # Progress Bar
        st.progress((st.session_state.current_idx) / total, text=f"Frage {st.session_state.current_idx + 1} / {total}")
        
        st.subheader(f"❓ {q_data['question']}")
        
        # Form
        with st.form(key=f"form_{st.session_state.current_idx}"):
            user_selection = st.radio("Wählen Sie die korrekte Antwort:", q_data['options'], key="radio")
            
            # Eğer geri bildirim varsa butonu gizle (yerine 'Sonraki' gelecek)
            if st.session_state.feedback is None:
                submitted = st.form_submit_button("Antworten")
            else:
                submitted = False
        
        # Mantık
        if submitted:
            # AI Bağlamını Burda Çekiyoruz (Anlık)
            with st.spinner('Klinischer Kontext wird generiert (AI)...'):
                ai_text = get_ai_context(q_data['term_for_ai'], q_data['meaning_for_ai'])
            
            if user_selection == q_data['correct']:
                st.session_state.score += 1
                msg = f"✅ Richtig! ({q_data['correct']})"
                msg_type = "success"
            else:
                msg = f"❌ Falsch. Die richtige Antwort war: **{q_data['correct']}**"
                msg_type = "error"
            
            st.session_state.feedback = (msg_type, msg, ai_text)
            st.rerun()
            
        # Geri Bildirim Alanı
        if st.session_state.feedback:
            m_type, m_text, m_ai = st.session_state.feedback
            
            if m_type == "success": st.success(m_text)
            else: st.error(m_text)
            
            # AI Kutusu
            st.info(f"**🤖 Klinischer Kontext (Llama 3):**\n\n_{m_ai}_")
            
            if st.button("Nächste Frage ➡️", use_container_width=True):
                st.session_state.current_idx += 1
                st.session_state.feedback = None
                st.rerun()