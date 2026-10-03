# Brief for Claude: make a guide image and an explainer video for lawyers

**Hi Claude.** I built **Atlas AI** — a product by **Web Triggers** (like ChatGPT is a product of OpenAI) and I want to show it to lawyers who are
**not technical**. Please read this whole brief, then make these 3 things for me:

1. **An infographic image.** A one-page visual guide: how a lawyer uses the app, step by step.
   Make it as a single HTML page (portrait, 1080 × 1350) so I can take a screenshot of it.
2. **An animated explainer video.** A single HTML page that plays a 45–60 second animation by
   itself (1920 × 1080) so I can screen-record it. Add a "Replay" button at the end.
3. **A voice-over script.** Short lines I can read aloud over the video, with the time for each
   line.

If anything in this brief is unclear, make a sensible choice and tell me what you chose.

---

## 1. What the app is (plain English)

Atlas AI checks a document against a checklist.

- You upload **what the document SHOULD contain**, for example the firm's contract-review
  checklist or the client's term sheet.
- You upload **the document itself**, for example the contract received from the other side.
- The app goes through the checklist **point by point** and labels each point:

| Label | Colour | What it means for a lawyer |
|---|---|---|
| **Covered** | Green | The clause is in the document. The app shows the exact quote. |
| **Partial** | Amber | The point is dealt with, but something is missing. Example: a liability clause with no cap amount. |
| **Missing** | Red | Nothing in the document deals with this point. |
| **Conflict** | Purple | The document says something different from the checklist. Example: the checklist says 30 days' notice, the contract says 7. |
| **Unclear** | Grey | The lawyer needs to decide. |

- **Every result comes with the exact sentence and page from the document**, so the lawyer can
  check it in seconds.
- The lawyer can also **ask questions in plain English**, such as "What should I negotiate?",
  and **download a PDF report**.

**One-line pitch:** *"Check any contract against your checklist in minutes. Every finding comes
with the exact quote and page."*

**Comparison a lawyer will understand:** it does what a junior associate does on a first review
against a checklist. It is fast and quotes everything, and the lawyer still makes the decisions.

---

## 2. Who the audience is

- Practising lawyers: advocates, in-house counsel, law-firm associates.
- They are busy and not technical. Do not use words like "AI model", "LLM", "vector", "upload
  pipeline" or "requirements extraction".
- They care about three things: **saving time**, **not missing a clause**, and **client
  confidentiality**.

---

## 3. How a lawyer uses it (the steps to show)

Use these exact button names, because they match the real app.

1. **Start.** Click **New analysis**, choose **Compare requirements**, type a name (e.g.
   "ABC Ltd — Services Agreement"), then click **Continue**.
2. **Add documents.**
   - Left box, **"What should exist?"**: upload the checklist or term sheet.
   - Right box, **"What currently exists?"**: upload the contract.
   - Click **Start analysis**.
3. **Check the checklist points.** In the **Requirements** tab, click **Extract**. The app turns
   the checklist into numbered points (REQ-001, REQ-002 and so on). The lawyer reads them, edits
   or removes any that are wrong, then approves them.
4. **Run the check.** Click **Analyze**. After a minute or two, each point gets its label
   (Covered, Partial, Missing, Conflict or Unclear).
5. **See the proof.** Click any point to see the exact sentence from the contract and its page.
6. **Ask questions.** In the **Ask** tab, type questions such as:
   - "Which protections for my client are missing?"
   - "Summarise the conflicts and what to negotiate."
   - "What does the contract say about termination?"
7. **Double-check doubtful points.** On a Missing or Unclear point, click **Re-check with
   agent**. The app searches again more carefully. It only changes the result if it finds a
   real quote.
8. **Download the report.** In the **Report** tab, download a **PDF** for the file or the
   client, or a **CSV** spreadsheet.

**Bonus to mention:** when the other side sends a revised draft, run the check again. The
report shows what improved and what got worse since the last version.

---

## 4. Everyday uses (good for one panel of the infographic)

| Task | Checklist side ("What should exist?") | Document side ("What currently exists?") |
|---|---|---|
| Contract review | Firm's standard clause checklist | Other side's draft contract |
| Did the draft follow instructions? | Term sheet or client's instructions | The draft agreement |
| Policy compliance | List of legal requirements | Company privacy or HR policy |
| Tender compliance | Tender's mandatory conditions | The bid documents |
| Due diligence | Due-diligence checklist | Lease or title documents |

---

## 5. Demo example to animate (use these exact words)

**Checklist (left card):**
1. Governing law and jurisdiction must be stated.
2. Termination needs at least 30 days' written notice.
3. Supplier's liability must be capped at 12 months' fees.
4. Confidentiality must last 3 years after termination.
5. Invoices payable within 45 days.
6. Supplier must hold professional indemnity insurance.
7. Disputes must go to mediation before court.

**Contract (right card), short version:**
- "This Agreement is governed by the laws of India and the courts of Mumbai have exclusive
  jurisdiction."
- "Either party may terminate this Agreement by giving 7 days' written notice."
- "The Supplier shall not be liable for any indirect or consequential loss."
- "Each party shall keep the other party's confidential information secret … for 3 years after
  it ends."
- "The Client shall pay each invoice within 45 days of receipt."
- "Any dispute shall be referred to the courts of Mumbai."

**Results table to show:**

| Checklist point | Result | Why |
|---|---|---|
| Governing law | 🟢 Covered | "governed by the laws of India…" |
| 30 days' notice | 🟣 Conflict | Contract says **7 days** |
| Liability cap | 🟡 Partial | Indirect loss excluded, but **no cap** |
| Confidentiality 3 years | 🟢 Covered | "…for 3 years after it ends" |
| Payment 45 days | 🟢 Covered | "…within 45 days of receipt" |
| Insurance | 🔴 Missing | No insurance clause |
| Mediation first | 🔴 Missing | Goes straight to court |

**Moment to zoom in on:** expand the "30 days' notice" row and show the quote *"Either party may
terminate this Agreement by giving 7 days' written notice."* with a small **"Page 1"** tag.

---

## 6. Must include: "Use it responsibly" (do not skip this)

Show this calmly and clearly, as a small box or end card. Do not make it look like a scary
warning.

- **It's an assistant, not a lawyer.** Always check the quoted text. You make the final call.
- **Keep client documents confidential.** The free online version uses outside AI services.
  Upload only sample, template or **redacted** documents (names and amounts removed). For real
  client files, ask for the **private installation**, which runs on your own computer so nothing
  leaves the office.
- **Works with:** PDF (with selectable text), Word (.docx) and text files, up to 20 MB.
  **Scanned paper copies (photos) don't work.**
- **In our tests it is right about 8 times out of 10**, which is why every result shows its
  quote.

---

## 7. Design style

- **Feel:** calm, trustworthy and professional, like a law-firm brochure, not a tech start-up.
- **Colours:** navy and off-white with one accent colour. Use the five label colours above for
  the results.
- **Text:** large and easy to read, short sentences, no jargon, no hype words like
  "revolutionary" or "game-changing".
- **No stock photos** and no external images or fonts that need downloading. Everything goes
  in the single HTML file.
- Plenty of white space.

---

## 8. What each of the 3 things should contain

### A. Infographic (HTML, 1080 × 1350, portrait)
- Title: **"Check any contract against your checklist in minutes"**
- Subtitle: **"Every finding comes with the exact quote and page."**
- The 4 main steps with simple icons: upload checklist, upload contract, approve the points,
  get results.
- Colour legend for the five labels.
- A small "Everyday uses" panel (section 4).
- Footer: the "Use it responsibly" box (section 6) and the link
  **https://atlas-ai.webtriggers.online**

### B. Animated explainer (HTML, 1920 × 1080, plays by itself, about 45–60 seconds)
1. **Problem (about 6 s):** "Checking a 40-page contract against your checklist takes hours."
2. **Two documents (about 8 s):** the "Your checklist" card slides in from the left and "The
   contract" card from the right.
3. **Results (about 20 s):** checklist lines move into a results table one by one, each getting
   its coloured label (use the table in section 5).
4. **Proof (about 8 s):** the "30 days' notice" row expands to show the quote and "Page 1".
5. **Ask and report (about 8 s):** a question box shows "What should I negotiate?" and a short
   answer appears; then a "Download PDF report" button.
6. **End card (about 6 s):** "Every finding backed by a quote. You make the call." Below it, the
   responsibility line "Use redacted documents on the free version" and the link.
7. A **Replay** button at the end.

### C. Voice-over script
- Match the scenes in B, with a time range for each line.
- Calm, friendly tone. Every sentence under 15 words.
- Plain English, as if explaining to a senior lawyer over tea.

---

Thank you! Please start with the **infographic**, then the **animated explainer**, then the
**voice-over script**.
