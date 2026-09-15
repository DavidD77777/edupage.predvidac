import streamlit as st
import traceback
from edupage_api import Edupage

st.set_page_config(page_title="EduPage Předvídač", layout="centered")

st.title("🎓 Předvídač známek pro EduPage")
st.write("Zadej své přihlašovací údaje a spočítej si průměr.")

if 'grades' not in st.session_state:
    st.session_state.grades = None

# --- 1. PŘIHLAŠOVACÍ OBRAZOVKA ---
if st.session_state.grades is None:
    skola = st.text_input("Název školy (např. zsmasarykova - bez .edupage.org)")
    jmeno = st.text_input("Přihlašovací jméno")
    heslo = st.text_input("Heslo", type="password")

    if st.button("Přihlásit a načíst známky"):
        if skola and jmeno and heslo:
            with st.spinner("Přihlašuji a stahuji známky..."):
                try:
                    edupage = Edupage()
                    edupage.login(jmeno, heslo, skola)
                    raw_grades = edupage.get_grades()
                    
                    st.session_state.grades = raw_grades

                    if not st.session_state.grades:
                        st.warning("Přihlášení proběhlo, ale EduPage nevrátil žádné známky.")
                    else:
                        st.success("Úspěšně načteno!")
                        st.rerun()

                except Exception as e:
                    print("CHYBA V APLIKACI:")
                    traceback.print_exc()
                    st.error(f"❌ Chyba: {type(e).__name__} - {str(e)}")
        else:
            st.warning("Vyplňte prosím všechny údaje.")

# --- 2. PŘEDVÍDAČ ZNÁMEK ---
else:
    if st.button("Odhlásit se"):
        st.session_state.grades = None
        st.rerun()

    predmety = {}
    for g in st.session_state.grades:
        # Váha se v EduPage API jmenuje 'importance' (příp. 'weight')
        vaha = getattr(g, "importance", None)
        if vaha is None:
            vaha = getattr(g, "weight", 1.0)
        if vaha is None: 
            vaha = 1.0

        # Číselná známka je v 'grade_n'
        hodnota = getattr(g, "grade_n", None)
        
        # Pojistka kdyby byla hodnota jinde (např. v 'value')
        if hodnota is None:
            val_str = str(getattr(g, "value", "")).strip()
            val_str = val_str.replace("-", ".5").replace("+", ".25")
            try:
                hodnota = float(val_str)
            except ValueError:
                continue

        if hodnota is None:
            continue

        try:
            hodnota = float(hodnota)
            vaha = float(vaha)
        except ValueError:
            continue

        # Název předmětu je přímo v 'subject_name'
        nazev = getattr(g, "subject_name", None)
        if not nazev:
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
            "popis": getattr(g, "comment", "") or getattr(g, "title", "Bez popisu")
        })

    if not predmety:
        st.warning("⚠️ Žádné známky ke zpracování. Tady jsou surová data z EduPage:")
        st.write(st.session_state.grades)
    else:
        vybrany_predmet = st.selectbox("Vyberte předmět:", list(predmety.keys()))

        if vybrany_predmet:
            znamky_predmetu = predmety[vybrany_predmet]

            suma_vazenych = sum(z["hodnota"] * z["vaha"] for z in znamky_predmetu)
            suma_vah = sum(z["vaha"] for z in znamky_predmetu)

            aktualni_prumer = suma_vazenych / suma_vah if suma_vah > 0 else 0

            st.write(f"### Aktuální průměr: **{aktualni_prumer:.2f}**")

            with st.expander("Zobrazit mé současné známky z tohoto předmětu"):
                for z in znamky_predmetu:
                    st.write(f"• Známka: **{z['hodnota']}** (Váha: {z['vaha']}) - {z['popis']}")

            st.divider()
            st.write("### 🔮 Co by bylo, kdyby...")

            sloupec1, sloupec2 = st.columns(2)
            with sloupec1:
                nova_znamka = st.number_input("Jakou známku dostaneš?", min_value=1.0, max_value=5.0, value=1.0, step=0.5)
            with sloupec2:
                nova_vaha = st.selectbox("S jakou váhou?", options=[0.25, 0.50, 1.00, 2.00, 3.00], index=2)

            nova_suma_vazenych = suma_vazenych + (nova_znamka * nova_vaha)
            nova_suma_vah = suma_vah + nova_vaha
            novy_prumer = nova_suma_vazenych / nova_suma_vah if nova_suma_vah > 0 else 0

            st.info(f"### Tvůj odhadovaný průměr bude: **{novy_prumer:.2f}**")

            rozdil = novy_prumer - aktualni_prumer
            if rozdil < 0:
                st.success(f"📈 Super! Průměr si zlepšíš o {abs(rozdil):.2f}.")
            elif rozdil > 0:
                st.error(f"📉 Pozor. Průměr se ti zhorší o {abs(rozdil):.2f}.")
            else:
                st.warning("Průměr zůstane stejný.")
