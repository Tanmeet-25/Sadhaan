# Sadhaan – MSRTC AI Travel Assistant (Prototype)

Team Sadhaan · Seva First Innovation Challenge 2026

This is a working demo with two screens:

1. **Passenger chat**: a WhatsApp-style chat. Passengers type (or speak) in Marathi, Hindi or English, see buses, book a ticket with a concession, track their bus and register complaints.
2. **MSRTC officer dashboard**: shows the most-searched routes, where passengers searched but **no bus was available**, AI suggestions for new trips, and complaints.

> ⚠️ The bus timetable and the dashboard history are **sample data made up for the demo**, not real MSRTC data. Say this clearly to the judges.

---

## What is inside this folder

| File | What it is |
|---|---|
| `app.py` | The whole app (chat + dashboard) |
| `data/buses.csv` | Sample MSRTC timetable (511 buses, 40 routes, incl. Mumbai-region short routes). Open it in Excel to edit |
| `data/demand_log.csv` | Simulated passenger searches from the last 30 days (feeds the dashboard) |
| `data/complaints.csv` | Sample complaints |
| `requirements.txt` | List of Python libraries the app needs |
| `.streamlit/secrets.toml.example` | Where your AI key goes (see Part 3) |

---

## Part 1: Install the tools (one time, about 15 minutes)

1. **Install Python 3.12**
   - Go to https://www.python.org/downloads/ and download Python 3.12.
   - **Windows:** on the first install screen, tick ✅ **"Add python.exe to PATH"**, then click Install.
2. **Install VS Code** (the code editor) from https://code.visualstudio.com/
3. **Make a free GitHub account** at https://github.com (needed in Part 4 to put the app online).

## Part 2: Run the app on your laptop

1. Unzip `sadhaan.zip` somewhere easy, e.g. `Documents/sadhaan`.
2. Open VS Code → **File → Open Folder** → choose the `sadhaan` folder.
3. Open the terminal in VS Code: **Terminal → New Terminal**.
4. Type these commands one by one and press Enter after each:

   **Windows**
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

   **Mac**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

5. Your browser opens at `http://localhost:8501` with the app. 🎉
6. To stop the app, click inside the terminal and press **Ctrl + C**.
   Next time you only need the `activate` command and `streamlit run app.py`.

**It works even without an AI key.** It then uses simple built-in rules that understand common phrases like "Pune to Satara tomorrow morning" or "पुणे ते सातारा उद्या सकाळी".

## Part 3: Turn on the real AI (Google Gemini, free tier)

With the AI on, the app understands messy, mixed-language messages and voice.

1. Go to https://aistudio.google.com and sign in with a Google account.
2. Click **"Get API key" → "Create API key"**. Copy the key.
3. In the `sadhaan` folder, open the `.streamlit` folder. Make a copy of `secrets.toml.example` and name the copy **`secrets.toml`**.
4. Open `secrets.toml` and paste your key between the quotes:
   ```
   GEMINI_API_KEY = "AIza...your key..."
   ```
5. Restart the app (Ctrl + C, then `streamlit run app.py`). The left sidebar should now say **"AI engine: Gemini"**.

> 🔒 Never share your key or upload `secrets.toml` to GitHub. The included `.gitignore` file already keeps it out.
> If Google renames the model, change `GEMINI_MODEL` in `secrets.toml` to the current "Flash" model name shown in AI Studio.

## Part 4: Put it online (free link for the judges)

1. On GitHub, click **"+" → New repository**, name it `sadhaan`, choose **Public**, click **Create**.
2. On the new repository page, click **"uploading an existing file"** and drag in **everything in the folder** (`app.py`, `requirements.txt`, `README.md`, the `data` folder). **Do not upload `secrets.toml` or `.venv`.** Click **Commit changes**.
3. Go to https://share.streamlit.io and sign in with GitHub.
4. Click **"Create app"** and choose your `sadhaan` repository, branch `main`, main file `app.py`.
5. Open **Advanced settings**:
   - choose Python **3.12**;
   - in **Secrets**, paste the same `GEMINI_API_KEY = "..."` line.
6. Click **Deploy**. After 2–3 minutes you get a link like `https://sadhaan-xxxx.streamlit.app`. Put it in the application form as the **prototype / demo link**.

> The free app "sleeps" if nobody opens it for a while. Open the link yourself before the judges do, so it is awake.

## Part 5: Demo script (2 minutes)

1. **Passenger chat:** type `दादर ते पनवेल उद्या सकाळी` → pick bus `1` → Sadhaan asks *"Do you want to book?"* → reply `हो` → pick concession `2` (woman) → the ticket shows a 50% fare.
   Also try `Kalyan to Murbad` → `1` → `nahi` to show that people can just check timings without booking.
2. Type `where is my bus` → live ETA.
3. Type `Borivali se Thane kal shaam` (Hindi) → *"No bus in the evening… I have noted this for MSRTC."*
4. Type `Thane to Shahapur` → route not available, demand recorded.
5. Switch to **MSRTC officer dashboard** → show the **Unmet demand** chart and **AI recommendations**:
   *"Every passenger message becomes planning data for MSRTC."*

Also record this as a screen video (Windows: **Win + Alt + R**; Mac: **Cmd + Shift + 5**) as a backup.

## Easy changes you can make

- **Add or change buses:** edit `data/buses.csv` in Excel (keep the same column names and save as CSV).
- **Change wording:** messages are in the `T = { ... }` section of `app.py` (English `en`, Marathi `mr`, Hindi `hi`).
- **Add a city name or spelling:** add it to `CITY_ALIASES` in `app.py`.

## Common problems

| Problem | Fix |
|---|---|
| `python is not recognized` | Reinstall Python and tick "Add python.exe to PATH" |
| `streamlit is not recognized` | Run the `activate` command first |
| Windows says "running scripts is disabled" | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, type `Y`, then try `activate` again |
| Sidebar shows "Last AI error" | Check the key in `secrets.toml`, or the model name. The app keeps working with backup rules |
| Online app shows an error | On share.streamlit.io, open **Manage app** → read the log at the bottom |
