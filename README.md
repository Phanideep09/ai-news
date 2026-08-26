# AI Radar (cloud version)

This version runs entirely on GitHub's free infrastructure — **not your
laptop**. Once it's set up, it keeps checking feeds and sending you
notifications even if your computer is off, asleep, or on the other side of
the world. No terminal, no `pip install`, no keeping anything running.

## How it works

- **GitHub Actions** checks the feeds every ~3 hours, on GitHub's servers.
- **GitHub Pages** hosts the phone app at a real web address — always
  reachable, no "same wifi" requirement.
- **ntfy.sh** delivers the actual push notifications to your phone.

```
ai-radar/
├── .github/workflows/
│   ├── check-and-notify.yml       # the scheduled job
│   └── send-test-notification.yml # one-click test button
├── core.py                        # fetching + relevance filtering
├── check_and_notify.py            # the script the workflow runs
├── requirements.txt
└── docs/                          # this becomes your website
    ├── index.html
    ├── manifest.json
    ├── sw.js
    ├── icon-192.png
    ├── icon-512.png
    └── data/
        ├── feed_cache.json        # what the app displays (auto-updated)
        └── seen_state.json        # internal memory (auto-updated)
```

Everything below happens on **github.com in your browser** — no terminal
required.

---

## Step 1: Create a GitHub account

If you don't already have one, sign up free at **github.com**.

## Step 2: Create a new repository

1. Click the **+** icon (top right) → **New repository**
2. Name it something like `ai-radar`
3. Set it to **Public** (required for free GitHub Pages on a personal account
   — this just means the code and article titles are visible to anyone who
   looks; your notification topic name stays private, see Step 4)
4. Click **Create repository**

## Step 3: Upload all the files

1. On your new (empty) repo page, click **uploading an existing file**
2. Drag in every file from this project **keeping the folder structure** —
   GitHub preserves folders when you drag a whole folder in, or you can
   upload the `.github`, `docs` folders and the root files separately
3. Scroll down, click **Commit changes**

**Tip:** if drag-and-drop of folders doesn't work well in your browser, you
can upload one file at a time and type the folder path directly into the
filename box (e.g. type `docs/index.html` as the filename when uploading
`index.html` — GitHub creates the folder automatically).

## Step 4: Set up push notifications (ntfy.sh)

1. Install the **ntfy** app on your phone: [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/us/app/ntfy/id1625396347)
2. In the app, subscribe to a topic name you make up — something unguessable,
   e.g. `phani-ai-radar-8f2k1`
3. Back on GitHub: go to your repo → **Settings** tab → **Secrets and
   variables** → **Actions** → **New repository secret**
4. Name: `NTFY_TOPIC`, Value: the topic you just picked → **Add secret**

This keeps your topic name private even though the repo itself is public —
secrets never appear in your code or commit history.

**Optional:** if you have an Anthropic API key and want smarter filtering
(understanding context instead of just keyword matching), add a second
secret named `ANTHROPIC_API_KEY` the same way. Not required — the free
keyword filter works well on its own.

## Step 5: Turn on GitHub Pages

1. Repo → **Settings** → **Pages** (left sidebar)
2. Under **Source**, choose **Deploy from a branch**
3. Branch: **main**, Folder: **/docs** → **Save**
4. GitHub shows you a URL like `https://yourusername.github.io/ai-radar/` —
   this is your app's permanent address. It can take a minute or two to go
   live the first time.

## Step 6: Run the first check manually

The scheduled check runs every 3 hours automatically, but let's seed real
data right now instead of waiting:

1. Repo → **Actions** tab
2. Click **Check AI feeds** in the left list
3. Click **Run workflow** (dropdown, top right) → **Run workflow** (green
   button)
4. Wait ~30 seconds, refresh the page — you should see a green checkmark
   when it finishes
5. If any relevant items were found, you'll get a real notification on your
   phone right now

## Step 7: Open it on your phone and install it

1. Open **Chrome** on your phone
2. Go to your Pages URL from Step 5, e.g. `https://yourusername.github.io/ai-radar/`
3. Tap the **⋮** menu → **Add to Home screen**
4. Open it from your home screen — articles should already be there from
   Step 6

## Step 8: Confirm notifications work

Tap the **gear icon** in the app for instructions, or directly:
1. Repo → **Actions** → **Send test notification** → **Run workflow**
2. You should get a push within a few seconds

---

## That's it — you're done

From here, it runs itself:
- Every ~3 hours, GitHub automatically checks feeds and notifies you of
  anything relevant
- The app always shows the latest data when you open it
- Your laptop can be off, closed, anywhere — none of this depends on it

## Making changes later

To edit any file (like adjusting which feeds are checked, in `core.py`),
go to the file on GitHub, click the **pencil icon** to edit, make your
change, and **Commit changes** directly in the browser. No git commands
needed.

## Customizing sources

Edit `FEEDS` in `core.py`. Other feeds worth considering:
- `https://feeds.arstechnica.com/arstechnica/technology-lab` (Ars Technica Tech)
- `https://www.reddit.com/r/LocalLLaMA/.rss`
- `https://www.reddit.com/r/artificial/.rss`

To follow different arXiv categories, change `cat:cs.AI` in the arXiv URL to
e.g. `cat:cs.CL` (NLP) or `cat:cs.LG` (ML), or combine with `+OR+`.

## Adjusting the check frequency

Edit `.github/workflows/check-and-notify.yml`, change the `cron` line.
`"0 */3 * * *"` means every 3 hours. `"0 */1 * * *"` would mean every hour.
(GitHub Actions has a practical minimum of about 5 minutes and may run a
few minutes late under load — this is normal.)

## Resetting / rescanning everything

Actions tab → **Check AI feeds** → **Run workflow** → type `yes` in the
reset box → **Run workflow**. This clears memory of what's already been
seen, so all current articles look new again.

## One optional nice-to-have

Open `docs/index.html`, find this line near the bottom of the `<script>`
section:
```js
const GITHUB_REPO_URL = "";
```
Fill in your repo's URL, e.g. `"https://github.com/yourusername/ai-radar"`,
and commit the change. This makes the settings panel show a direct "Open
GitHub Actions" link instead of just instructions.
