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

## Step 1 — Get your messages onto this Mac

You have two ways to do this. Either is fine — pick one.

### Option A — Let the app back up your iPhone for you (no Finder)

Install the free **libimobiledevice** tools once, and the app can make the
backup itself: plug in the phone, click **Back up & export**, done. In Terminal:

```
brew install libimobiledevice
```

(Don't have Homebrew? Get it at <https://brew.sh>, or just use Option B.)

Then plug your iPhone in, unlock it, tap **Trust This Computer** if asked, and
it'll appear at the top of the app's page under *"Back up your iPhone now."*

> **Why this is nice:** backups are **incremental**. The first one is the slow
> one (it copies everything), but the app keeps it in
> `~/Documents/MessageExports/.backup-cache/`, so every run after that only
> copies the handful of new messages — usually seconds. If you'd rather not keep
> the backup around, tick *"Delete the backup afterwards"* (you'll just pay the
> full-backup time again next time). Note there's no way to back up *only*
> Messages — the phone decides what a backup contains — so the first pass copies
> the lot regardless; the app simply extracts the messages and tidies up.

### Option B — Back up in Finder yourself, then point the app at it

1. Plug your iPhone into the Mac with its charging cable.
2. If the phone shows a **Trust This Computer?** prompt, tap **Trust** and
   enter your phone passcode.
3. Open **Finder** and click your iPhone in the left sidebar.
4. Under *Backups*, select **"Back up all of the data on your iPhone to this Mac"**.
5. Click **Back Up Now** and let it finish (a first backup can take 15–60 minutes).

> **Speed tip:** backup time is dominated by photos and videos, not messages. If
> you use **iCloud Photos** with *Optimize iPhone Storage*, your photos aren't in
> the local backup at all, so it's often far quicker than you'd expect.

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

- **Used Option A?** Your iPhone shows up at the top under *"Back up your iPhone
  now."* Click **Back up & export**. The first run does the full backup (be
  patient); later runs are quick.
- **Used Option B?** Pick your iPhone's backup from the list (newest first) and
  click **Export this backup**.

Then:

1. If the backup is encrypted, enter the backup password. Checking it takes
   about 10 seconds.
2. Watch the progress bar. Big message histories can take a few minutes.
3. When it finishes, click **Open the folder**.

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
| iPhone doesn't appear under "Back up your iPhone now" | You need the libimobiledevice tools (`brew install libimobiledevice`); then plug the phone in, unlock it, tap **Trust This Computer**, and refresh. |
| "hasn't trusted this computer yet" | Unlock the phone and tap **Trust This Computer** (enter your passcode), then try again. |
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

python cli.py --list-devices                    # iPhones plugged in (needs libimobiledevice)
python cli.py --device --out /tmp/demo          # back up the phone, then export
python cli.py --device <udid> --discard-backup  # ...and delete the backup after
```

Direct-from-phone backup lives in `exporter/backup/device.py` (a thin wrapper
around `idevice_id` / `ideviceinfo` / `idevicebackup2`) and feeds the *same*
extraction path as a Finder backup via `run_export_from_device()` in
`pipeline.py`. It's tested with subprocess stubs, so the suite runs without the
CLI tools or a phone present.

The pipeline normalizes everything into `exporter/models.py` dataclasses
(`ExportBundle` → `Conversation` → `Message`); output formats live in
`exporter/exporters/` and only consume that model, so new exports (e.g. a
client roster CSV or per-conversation JSONL for AI training) are additive.
