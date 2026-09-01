import streamlit as st
from edupage_api import Edupage

# Nastavení vzhledu aplikace
st.set_page_config(page_title="EduPage Předvídač", layout="centered")

st.title("🎓 Předvídač známek pro EduPage")
st.write("Funguje stejně jako v Bakalářích – zadej fiktivní známku a zjisti svůj nový průměr!")

# Paměť aplikace - aby si pamatovala, že jsme přihlášení a máme stažené známky
if 'grades' not in st.session_state:
    st.session_state.grades = None

# --- 1. PŘIHLAŠOVACÍ OBRAZOVKA ---
if st.session_state.grades is None:
    st.subheader("Přihlášení do EduPage")
    
    skola = st.text_input("Název školy (např. zsmasarykova - bez .edupage.org)")
    jmeno = st.text_input("Přihlašovací jméno")
    heslo = st.text_input("Heslo", type="password") # Skryje heslo hvězdičkami

    if st.button("Přihlásit a načíst známky"):
        if skola and jmeno and heslo:
            with st.spinner("Přihlašuji a stahuji známky..."):
                try:
                    edupage = Edupage()
                    edupage.login(jmeno, heslo, skola)
                    st.session_state.grades = edupage.get_grades()
                    st.success("Úspěšně načteno!")
                    st.rerun() # Obnoví stránku do zobrazení známek
                except Exception as e:
                    st.error(f"❌ Přihlášení selhalo! Detail chyby: {e}")
        else:
            st.warning("Vyplňte prosím všechny údaje.")

# --- 2. PŘEDVÍDAČ ZNÁMEK ---
else:
    if st.button("Odhlásit se"):
        st.session_state.grades = None
        st.rerun()

    # Roztřídění stažených známek do jednotlivých předmětů
    predmety = {}
    for g in st.session_state.grades:
        # 1. Ošetření váhy
        vaha = getattr(g, "weight", 1)
        if vaha is None: 
            vaha = 1

        # 2. Úprava známky na číslo (ošetření znamének + a -)
        val_str = str(getattr(g, "value", "")).strip()
        val_str = val_str.replace("-", ".5").replace("+", ".25")
        
        try:
            hodnota = float(val_str)
            vaha = int(vaha)
        except ValueError:
            continue  # Přeskočí nečíselné známky (např. "N", "Uvolněn")

        # 3. Získání názvu předmětu
        subject_obj = getattr(g, "subject", None)
        if hasattr(subject_obj, "name"):
            nazev = subject_obj.name
        elif subject_obj:
            nazev = str(subject_obj)
        else:
            nazev = "Neznámý předmět"

        if nazev not in predmety:
            predmety[nazev] = []

        predmety[nazev].append({
            "hodnota": hodnota,
            "vaha": vaha,
            "popis": getattr(g, "comment", "")
        })

    # Kontrola, zda máme nějaké platné předměty
    if not predmety:
        st.warning("⚠️ Nebyly nalezeny žádné číselné známky pro výpočet průměru.")
    else:
        # Výběrové menu pro předměty
        vybrany_predmet = st.selectbox("Vyberte předmět:", list(predmety.keys()))

        if vybrany_predmet:
            znamky_predmetu = predmety[vybrany_predmet]

            # Výpočet aktuálního průměru
            suma_vazenych = sum(z["hodnota"] * z["vaha"] for z in znamky_predmetu)
            suma_vah = sum(z["vaha"] for z in znamky_predmetu)

            aktualni_prumer = suma_vazenych / suma_vah if suma_vah > 0 else 0

            st.write(f"### Aktuální průměr: **{aktualni_prumer:.2f}**")

            # Výpis aktuálních známek
            with st.expander("Zobrazit mé současné známky z tohoto předmětu"):
                for z in znamky_predmetu:
                    st.write(f"• Známka: **{z['hodnota']}** (Váha: {z['vaha']}) - {z['popis']}")

            st.divider()

            # --- SIMULACE (CO KDYBY...) ---
            st.write("### 🔮 Co by bylo, kdyby...")

            sloupec1, sloupec2 = st.columns(2)
            with sloupec1:
                nova_znamka = st.number_input("Jakou známku dostaneš?", min_value=1.0, max_value=5.0, value=1.0, step=0.5)
            with sloupec2:
                nova_vaha = st.number_input("S jakou váhou?", min_value=1, max_value=100, value=10)

            # Přepočítání průměru
            nova_suma_vazenych = suma_vazenych + (nova_znamka * nova_vaha)
            nova_suma_vah = suma_vah + nova_vaha
            novy_prumer = nova_suma_vazenych / nova_suma_vah if nova_suma_vah > 0 else 0

            st.info(f"### Tvůj odhadovaný průměr bude: **{novy_prumer:.2f}**")

            # Vyhodnocení zlepšení/zhoršení
            rozdil = novy_prumer - aktualni_prumer
            if rozdil < 0:
                st.success(f"📈 Super! Průměr si zlepšíš o {abs(rozdil):.2f}.")
            elif rozdil > 0:
                st.error(f"📉 Pozor. Průměr se ti zhorší o {abs(rozdil):.2f}.")
            else:
                st.warning("Průměr zůstane stejný.")