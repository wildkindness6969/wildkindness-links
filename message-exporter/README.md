# Message Exporter

Turn the text messages on your iPhone into:

- **Chat-style PDFs** — one per conversation, with bubbles just like the Messages app
- **A spreadsheet** (`messages.xlsx`) — every message with date, time, who sent it,
  their number, and the text, plus a summary tab with one row per conversation

**Everything happens on your own computer.** Nothing is uploaded anywhere, no
account is needed, and the tool deletes its temporary files when it finishes.

---

## One-time setup

You need Python 3 installed. To check, open **Terminal** (find it with
Spotlight: press ⌘-Space and type "Terminal") and type:

```
python3 --version
```

If you see a version number like `Python 3.11.5`, you're set. If not, download
and install Python from <https://www.python.org/downloads/> — the standard
installer is fine.

## Step 1 — Back up your iPhone to this Mac

1. Plug your iPhone into the Mac with its charging cable.
2. If the phone shows a **Trust This Computer?** prompt, tap **Trust** and
   enter your phone passcode.
3. Open **Finder** and click your iPhone in the left sidebar.
4. Under *Backups*, select **"Back up all of the data on your iPhone to this Mac"**.
5. Click **Back Up Now** and let it finish (a first backup can take 15–60 minutes).

> **About the "Encrypt local backup" checkbox:** either setting works. If it's
> checked, the app will ask you for the backup password you chose when you first
> turned it on. **If you've forgotten that password, nobody — including Apple —
> can recover it**, so test it before relying on it.

## Step 2 — Run the app

Double-click **`run.command`** in this folder.

- The first run installs a few components and can take a minute or two.
- A Terminal window opens and stays open while the app runs — that's normal.
- Your web browser opens to the Message Exporter page automatically.

**If macOS says the file "cannot be opened":** right-click (or Control-click)
`run.command` and choose **Open**, then click **Open** in the dialog. You only
have to do this once.

> ### ⚠️ The #1 thing that goes wrong: Full Disk Access
>
> macOS protects iPhone backups, so the first time you run the app it may say
> it can't see any backups, or show a permission error. The fix takes 30 seconds:
>
> 1. Open **System Settings → Privacy & Security → Full Disk Access**
> 2. Turn on the switch next to **Terminal**
> 3. Quit Terminal completely (⌘Q) and double-click `run.command` again

## Step 3 — In the browser

1. Pick your iPhone's backup from the list (newest is shown first).
2. If the backup is encrypted, enter the backup password. Checking it takes
   about 10 seconds.
3. Watch the progress bar. Big message histories can take a few minutes.
4. When it finishes, click **Open the folder**.

## Where your files are

Exports go to **`~/Documents/MessageExports/`**, in a folder named after your
phone and today's date, e.g. `Documents/MessageExports/Jordan's iPhone-2026-06-12/`:

```
pdf/                 one PDF per conversation
messages.xlsx        all messages + a per-conversation summary tab
export_log.txt       what was exported, plus any notes
```

## Privacy notes

- The app runs only on your computer (it binds to 127.0.0.1 and loads no
  outside resources). You can run it with Wi-Fi off if you like.
- Temporary decrypted copies of the database are deleted automatically.
- Your exported files contain your message history — treat the folder like the
  private data it is. You can also delete the iPhone backup afterward in
  Finder → iPhone → Manage Backups.

## Troubleshooting

| Problem | Fix |
|---|---|
| "No iPhone backups found" | Do Step 1 first; then make sure Terminal has Full Disk Access (see above) and click Rescan. |
| "That password didn't unlock the backup" | This is the *backup* password from Finder, not your phone passcode or Apple ID. If it's lost, you must reset backup settings on the phone (Settings → General → Transfer or Reset → Reset → Reset All Settings) and make a new backup. |
| "operation not permitted" in Terminal | Full Disk Access again — see the boxed callout above. |
| Export seems stuck | Very large histories (50,000+ messages) genuinely take several minutes; the progress text updates as it works. |
| Some messages show "[Unable to decode message body]" | A few messages (often heavily formatted ones) can't be fully decoded; the count appears in `export_log.txt`. Everything else still exports. |

## For developers

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pypdf
python -m pytest tests/                         # run the test suite
python -m tests.fixtures.make_fixture_backup    # build a fake backup
python cli.py --backup tests/fixtures/_built_backup --out /tmp/demo
```

The pipeline normalizes everything into `exporter/models.py` dataclasses
(`ExportBundle` → `Conversation` → `Message`); output formats live in
`exporter/exporters/` and only consume that model, so new exports (e.g. a
client roster CSV or per-conversation JSONL for AI training) are additive.
