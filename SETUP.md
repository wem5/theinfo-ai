# theinfo.ai — setup steps

Everything below only needs to be done once. After that, the hourly pipeline takes over.

## 1. Create the GitHub repo

1. Go to https://github.com/new
2. Owner: `wem5`, Repository name: `theinfo-ai` (or any name you like — just tell me what you picked)
3. Set it to **Public** (required for free GitHub Pages)
4. Don't initialize with a README — leave it empty
5. Click **Create repository**

## 2. Enable GitHub Pages

1. In the new repo: **Settings → Pages**
2. Under "Build and deployment" → Source: **Deploy from a branch**
3. Branch: `main`, folder: `/ (root)` → Save

## 3. Point your domain at it

At your domain registrar (wherever theinfo.ai is registered), add these DNS records:

**A records** for the apex domain (`theinfo.ai`), pointing to GitHub Pages' IPs:
```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

**Optional** — if you also want `www.theinfo.ai` to work, add:
```
CNAME  www  wem5.github.io
```

Then in the repo: **Settings → Pages → Custom domain** → enter `theinfo.ai` → Save. (A `CNAME` file with `theinfo.ai` in it is already included in the site files I built — GitHub Pages uses it to know which domain to serve.)

DNS can take anywhere from a few minutes to ~48 hours to propagate. GitHub will show a green checkmark once it's verified and can issue HTTPS.

## 4. Create an access token so I can push updates automatically

Since the site updates hourly on its own, I need a token to push commits on your behalf.

1. Go to https://github.com/settings/personal-access-tokens/new
2. Token name: `theinfo-ai-autopublish`
3. Expiration: your call — 90 days is reasonable (you'll just need to regenerate it after)
4. Repository access: **Only select repositories** → choose `theinfo-ai`
5. Permissions → **Repository permissions → Contents** → set to **Read and write**
6. Generate token, copy it (starts with `github_pat_...`)

**Heads up on where this lives:** the hourly automation runs as a saved, standalone task, so the token needs to be stored in that task's saved instructions file on your computer (not just in this chat) so it can authenticate each time it runs. It won't be shown in this conversation transcript beyond your one paste. Scoping it to *only* this one repo with *only* Contents read/write (as above) means even in the worst case, exposure is limited to this repo — it can't touch your other repos or account settings.

Once you've done steps 1–4, send me:
- The repo name (if not `theinfo-ai`)
- The token

...and I'll push the initial site live and set up the hourly scanning task.
