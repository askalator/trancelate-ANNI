# Repo NOTICE & GUI‑Lizenz‑Block (ANNI)

Dieser Baukasten liefert dir sofort nutzbare Vorlagen, damit ANNI sauber alle Dritt-Lizenzen ausweist – im **Repo** und direkt im **GUI (`anni_gui.html`)**. Alle Texte sind auf **kommerzielle Nutzung** mit MIT/Apache/CC‑BY ausgelegt. Ersetze die Platzhalter (⚙︎) und committe die Dateien wie angegeben.

---

## 1) Verzeichnis-Struktur (empfohlen)
```
/
├─ LICENSE                        # deine Projekt-Lizenz (z. B. proprietär oder MIT)
├─ NOTICE.md                      # kurze Übersicht + Attributionen (menschlich lesbar)
├─ THIRD_PARTY_NOTICES/           # komplette Lizenztexte Dritter
│  ├─ README.md
│  ├─ M2M100_LICENSE.txt          # MIT (facebook/m2m100_418M)
│  ├─ IndicTrans2_LICENSE.txt     # MIT (AI4Bharat/IndicTrans2)
│  ├─ OPUS_MT_LICENSE.txt         # CC-BY-4.0 (Helsinki-NLP, je Modell; Namensnennung!)
│  ├─ CTranslate2_LICENSE.txt     # MIT (CTranslate2)
│  ├─ SentencePiece_LICENSE.txt   # Apache-2.0 (Google)
│  └─ OpenCC_LICENSE.txt          # Apache-2.0 (nur wenn verwendet)
└─ scripts/
   └─ check_licenses.sh           # optionaler CI-Check (Vorlage unten)
```

> **Hinweis:** Falls du **NLLB‑200** nur zu internen Evaluationen nutzt, dokumentiere es **im NOTICE.md** als *Research-only (CC‑BY‑NC)*. **Nicht** in Produktion einsetzen.

---

## 2) `NOTICE.md` (fertige Vorlage)
> Lege diese Datei in dein Repo‑Root.

```markdown
# NOTICE

**Projekt:** ANNI — Translation Guard & Engine 3.0  
**Version:** ⚙︎vX.Y.Z  
**Build:** 2025‑10‑01  
**Copyright:** © 2025 TranceLate.it FlexCo, Björn Mayer. Alle Rechte vorbehalten.

Dieses Produkt beinhaltet Komponenten unter Open‑Source‑Lizenzen. Die zugehörigen Lizenztexte liegen in `THIRD_PARTY_NOTICES/` bei.

## Enthaltene Komponenten (Auszug)

### 1) M2M‑100 (facebook/m2m100_418M)
- **Lizenz:** MIT  
- **Verwendung:** Multilinguale Fallback-Übersetzung (JA/ZH/KO, afrikanische/asiatische Sprachen u. a.)  
- **Hinweis:** Copyright- und Lizenzvermerk werden beibehalten.

### 2) IndicTrans2 (AI4Bharat)
- **Lizenz:** MIT  
- **Verwendung:** Spezialisierte en↔Indic‑Routen (Hindi, Bengali, Tamil, Telugu, Urdu …)

### 3) OPUS‑MT (Helsinki‑NLP) — **je nach verwendetem Modell**
- **Lizenz:** i. d. R. CC‑BY‑4.0  
- **Verwendung:** zielgerichtete Paare (z. B. ja↔en, zh↔en)  
- **Namensnennung:** Bitte wie unten angeben (Beispielformulierung).

### 4) CTranslate2
- **Lizenz:** MIT  
- **Verwendung:** Inferenz‑Runtime/Converter

### 5) SentencePiece
- **Lizenz:** Apache‑2.0  
- **Verwendung:** Tokenisierung

### 6) OpenCC (optional)
- **Lizenz:** Apache‑2.0  
- **Verwendung:** ZH Script‑Konvertierung (Hans↔Hant)

---

## Namensnennung für CC‑BY‑4.0 (OPUS‑MT)
Wenn ein OPUS‑MT‑Modell verwendet wird, bitte folgenden Satz ergänzen (pro Modell):

> *"Dieses Produkt nutzt das Modell **Helsinki‑NLP/opus‑mt‑⚙︎SRC‑⚙︎TGT** (© University of Helsinki, Creative Commons Attribution 4.0 International). Quelle: OPUS/OPUS‑MT."*

Liste die tatsächlich gebündelten Modelle hier auf.

---

## Research‑only (nicht kommerziell)
> *Nur falls zutreffend.*

- **NLLB‑200 (Meta):** CC‑BY‑NC — *ausschließlich interne Evaluation/Tests*, nicht im produktiven Pfad.

---

## Haftungsausschluss
Alle Drittkomponenten werden **ohne Gewährleistung** bereitgestellt („AS IS“) — siehe jeweilige Lizenztexte in `THIRD_PARTY_NOTICES/`.
```

---

## 3) Lizenztexte (Vorlagen)
Lege diese Dateien unter `THIRD_PARTY_NOTICES/` ab. **Ersetze** die Platzhalter (⚙︎) und prüfe, ob dein tatsächliches Modell/Repo ggf. bereits eine Lizenz‑Datei mitliefert (dann diese beilegen).

### 3.1 `M2M100_LICENSE.txt` (MIT — Vorlage)
```
MIT License

Copyright (c) 2025 Meta Platforms, Inc. and affiliates

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 3.2 `IndicTrans2_LICENSE.txt` (MIT — Vorlage)
> Identisch zur MIT‑Vorlage oben; ersetze Copyright‑Zeile (z. B. "AI4Bharat").

### 3.3 `OPUS_MT_LICENSE.txt` (CC‑BY‑4.0 — Kurzfassung + Link‑Hinweis)
```
Creative Commons Attribution 4.0 International (CC BY 4.0)

Sie dürfen dieses Werk vervielfältigen und weiterverbreiten sowie Bearbeitungen
anfertigen, auch kommerziell, sofern Sie eine angemessene **Namensnennung**
vornehmen, einen Link zur Lizenz beifügen und angeben, ob Änderungen
vorgenommen wurden. Der vollständige Lizenztext ist dem Paket beizulegen oder
unter https://creativecommons.org/licenses/by/4.0/ einsehbar.

Attributionshinweis (Beispiel):
"Dieses Produkt nutzt das Modell Helsinki‑NLP/opus‑mt‑⚙︎SRC‑⚙︎TGT
(© University of Helsinki, CC BY 4.0). Quelle: OPUS/OPUS‑MT."
```

### 3.4 `CTranslate2_LICENSE.txt` (MIT — Vorlage)
> MIT‑Text wie oben.

### 3.5 `SentencePiece_LICENSE.txt` (Apache‑2.0 — Kurzfassung)
```
Apache License
Version 2.0, January 2004

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### 3.6 `OpenCC_LICENSE.txt` (Apache‑2.0 — Kurzfassung)
> Wie 3.5; nur beilegen, wenn OpenCC genutzt wird.

---

## 4) GUI‑Block für `anni_gui.html` (copy‑paste‑fertig)
> Ein kompakter, zugänglicher Lizenz-/Attributionsdialog. *Keine externen Abhängigkeiten.*

**Einbau:** Packe den gesamten Block in deine `anni_gui.html` (z. B. am Ende vor `</body>`). Passe die `thirdParty`‑Liste an und setze ⚙︎‑Platzhalter.

```html
<!-- BEGIN: ANNI License & Attribution Modal -->
<style>
  .anni-lic-btn{position:fixed;right:16px;bottom:16px;padding:10px 14px;background:#0f172a;color:#fff;border:none;border-radius:12px;box-shadow:0 6px 20px rgba(0,0,0,.2);cursor:pointer}
  .anni-lic-modal{position:fixed;inset:0;background:rgba(15,23,42,.6);display:none;align-items:center;justify-content:center;z-index:9999}
  .anni-lic-card{background:#fff;max-width:760px;width:92%;max-height:80vh;overflow:auto;border-radius:16px;box-shadow:0 16px 50px rgba(0,0,0,.3)}
  .anni-lic-hd{padding:16px 20px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;gap:12px}
  .anni-lic-ttl{font:600 18px/1.2 system-ui,Segoe UI,Roboto,Helvetica,Arial}
  .anni-lic-bd{padding:16px 20px;color:#0f172a}
  .anni-lic-ft{padding:12px 20px;border-top:1px solid #e5e7eb;display:flex;gap:8px;justify-content:flex-end}
  .anni-lic-chip{display:inline-flex;align-items:center;gap:6px;background:#f1f5f9;color:#0f172a;border-radius:999px;padding:6px 10px;font:500 12px/1 system-ui}
  .anni-lic-list{margin:12px 0 0 0;padding:0;list-style:none}
  .anni-lic-list li{margin:10px 0;padding:10px 12px;border:1px solid #e5e7eb;border-radius:12px}
  .anni-lic-list h4{margin:0 0 6px 0;font:600 14px/1.2 system-ui}
  .anni-lic-list p{margin:4px 0 0 0;font:13px/1.35 system-ui;color:#111827}
  .anni-lic-x{margin-left:auto;background:#e11d48;color:#fff;border:none;border-radius:10px;padding:8px 10px;cursor:pointer}
  .anni-lic-sec{display:flex;gap:8px;flex-wrap:wrap}
  .anni-lic-kbd{font:600 11px/1.2 ui-monospace,Menlo,Consolas;background:#0f172a;color:#fff;border-radius:6px;padding:2px 6px}
</style>
<button class="anni-lic-btn" id="anniLicBtn" title="Open-Source-Hinweise">Lizenzen</button>
<div class="anni-lic-modal" id="anniLicModal" aria-hidden="true" role="dialog" aria-labelledby="anniLicTitle">
  <div class="anni-lic-card">
    <div class="anni-lic-hd">
      <div class="anni-lic-ttl" id="anniLicTitle">Open‑Source & Lizenzen · ANNI ⚙︎vX.Y.Z</div>
      <span class="anni-lic-chip">Build: 2025‑10‑01</span>
      <button class="anni-lic-x" id="anniLicClose" aria-label="Schließen">Schließen</button>
    </div>
    <div class="anni-lic-bd">
      <p>Dieses Produkt enthält Open‑Source‑Software. Vollständige Lizenztexte befinden sich in <code>THIRD_PARTY_NOTICES/</code> und in der Datei <code>NOTICE.md</code> des Repositories.</p>
      <div class="anni-lic-sec">
        <span class="anni-lic-kbd">MIT</span>
        <span class="anni-lic-kbd">Apache‑2.0</span>
        <span class="anni-lic-kbd">CC‑BY‑4.0 (Attribution)</span>
      </div>
      <ul class="anni-lic-list" id="anniLicList"></ul>
    </div>
    <div class="anni-lic-ft">
      <button class="anni-lic-chip" id="anniLicExport">Export NOTICE</button>
    </div>
  </div>
</div>
<script>
  // Pflege: Trage hier die tatsächlich gebündelten Komponenten ein
  const thirdParty = [
    {name:'facebook/m2m100_418M', license:'MIT', usage:'Multilinguale Fallback-Übersetzung', attribution:null},
    {name:'AI4Bharat/IndicTrans2', license:'MIT', usage:'en↔Indic‑Routen (Hindi, Bengali, Tamil, Urdu …)', attribution:null},
    {name:'Helsinki‑NLP/opus‑mt‑ja‑en', license:'CC‑BY‑4.0', usage:'ja↔en', attribution:'Dieses Produkt nutzt das Modell Helsinki‑NLP/opus‑mt‑ja‑en (© University of Helsinki, CC BY 4.0). Quelle: OPUS/OPUS‑MT.'},
    {name:'Helsinki‑NLP/opus‑mt‑zh‑en', license:'CC‑BY‑4.0', usage:'zh↔en', attribution:'Dieses Produkt nutzt das Modell Helsinki‑NLP/opus‑mt‑zh‑en (© University of Helsinki, CC BY 4.0). Quelle: OPUS/OPUS‑MT.'},
    {name:'CTranslate2', license:'MIT', usage:'Inferenz Runtime/Converter', attribution:null},
    {name:'SentencePiece', license:'Apache‑2.0', usage:'Tokenisierung', attribution:null},
    // Optional:
    // {name:'OpenCC', license:'Apache‑2.0', usage:'ZH Script‑Konvertierung (Hans↔Hant)', attribution:null},
    // Research-only – NICHT PROD:
    // {name:'NLLB‑200', license:'CC‑BY‑NC (Research‑only)', usage:'Interne Evaluation — nicht im produktiven Pfad', attribution:null},
  ];

  const modal = document.getElementById('anniLicModal');
  const openBtn = document.getElementById('anniLicBtn');
  const closeBtn = document.getElementById('anniLicClose');
  const list = document.getElementById('anniLicList');
  const exportBtn = document.getElementById('anniLicExport');

  const render = () => {
    list.innerHTML = thirdParty.map(tp => `
      <li>
        <h4>${tp.name} · <em>${tp.license}</em></h4>
        <p><strong>Verwendung:</strong> ${tp.usage}</p>
        ${tp.attribution ? `<p><strong>Namensnennung:</strong> ${tp.attribution}</p>` : ''}
      </li>
    `).join('');
  };

  const exportNotice = () => {
    const header = `NOTICE — ANNI\nVersion: ⚙︎vX.Y.Z  •  Build: 2025‑10‑01\n\n`;
    const body = thirdParty.map(tp => `- ${tp.name}  |  ${tp.license}  |  ${tp.usage}${tp.attribution?`\n  Attribution: ${tp.attribution}`:''}`).join('\n');
    const blob = new Blob([header + body + '\n'], {type:'text/plain'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'NOTICE_ANNI.txt';
    a.click();
    URL.revokeObjectURL(a.href);
  };

  openBtn.addEventListener('click', () => { modal.style.display = 'flex'; modal.setAttribute('aria-hidden','false'); render(); });
  closeBtn.addEventListener('click', () => { modal.style.display = 'none'; modal.setAttribute('aria-hidden','true'); });
  modal.addEventListener('click', (e) => { if(e.target === modal) closeBtn.click(); });
  document.addEventListener('keydown', (e)=>{ if(e.key==='Escape' && modal.style.display==='flex') closeBtn.click(); });
  exportBtn.addEventListener('click', exportNotice);
</script>
<!-- END: ANNI License & Attribution Modal -->
```

---

## 5) Optional: CI‑Check (stellt sicher, dass alle Texte beiliegt)
> Lege als `scripts/check_licenses.sh` ab und rufe es in CI vor dem Build auf.

```bash
#!/usr/bin/env bash
set -euo pipefail
missing=0
files=( \
  "THIRD_PARTY_NOTICES/M2M100_LICENSE.txt" \
  "THIRD_PARTY_NOTICES/IndicTrans2_LICENSE.txt" \
  "THIRD_PARTY_NOTICES/CTranslate2_LICENSE.txt" \
  "THIRD_PARTY_NOTICES/SentencePiece_LICENSE.txt" \
)
for f in "${files[@]}"; do
  if [[ ! -s "$f" ]]; then echo "[LICENSE] fehlt: $f"; missing=1; fi
done
if [[ -f "THIRD_PARTY_NOTICES/OPUS_MT_LICENSE.txt" ]]; then echo "[LICENSE] OPUS‑MT vorhanden (CC‑BY‑4.0)"; fi
if [[ $missing -eq 1 ]]; then echo "[LICENSE] Abbruch — fehlende Lizenztexte"; exit 42; fi
echo "[LICENSE] OK"
```

---

## 6) Mini‑Checkliste (bei jedem neuen Sprachpaket)
- [ ] Modell/Lib identifizieren → **Lizenztyp prüfen** (MIT/Apache/CC‑BY/…)
- [ ] **Lizenztext** in `THIRD_PARTY_NOTICES/` ablegen (Datei benennen wie oben)
- [ ] **NOTICE.md** ergänzen (Name, Lizenz, Verwendung, ggf. Attributionstext)
- [ ] **GUI‑Liste** (`thirdParty`) aktualisieren
- [ ] Für **CC‑BY‑4.0**: Namensnennungssatz hinzufügen
- [ ] **Research-only** (CC‑BY‑NC etc.) klar kennzeichnen, nicht in produktiven Pfad laden
- [ ] Container‑Image/Build inkludiert `NOTICE.md` + `THIRD_PARTY_NOTICES/`

---

### Kurzhinweis zur Haftung
MIT/Apache sehen **keine Gewährleistung** vor; CC‑BY überträgt nur Urheber‑, keine Marken-/Patent‑rechte. Für Apache‑2.0 ist ein **Patent‑Grant** enthalten (gut für Tokenizer/Runtime). Achte darauf, Markenbezeichnungen nur beschreibend zu verwenden.

