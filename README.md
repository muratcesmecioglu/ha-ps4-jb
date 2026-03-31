# 🎮 PS4 JB Web Server — Home Assistant Add-on

A Home Assistant add-on that hosts a local web server for PS4 jailbreak payloads. It supports multiple exploit chains for firmwares 5.05 - 9.60 and provides a built-in admin panel to download and manage [GoldHEN](https://github.com/GoldHEN/GoldHEN) — all from your Home Assistant instance.

## Features

- **Static File Server** — Serves exploit files over HTTP using Python's built-in `http.server`
- **Configurable Port** — Set the listening port from the add-on configuration page (default: `8000`)
- **GoldHEN Updater** — One-click download of the latest GoldHEN pre-release directly from GitHub
- **Persistent Storage** — Downloaded `goldhen.bin` is stored in `/data/` and survives add-on restarts
- **Admin Panel** — Clean web UI at `/_admin` for managing GoldHEN updates with real-time debug logs
- **Host Networking** — Direct port access on your Home Assistant host, no port forwarding needed

## Installation

### Method 1: Add Custom Repository (Recommended)

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click **⋮ → Repositories** in the top right corner
3. Add this repository URL: `https://github.com/muratcesmecioglu/ha-ps4-jb`
4. Click **Add**, then close the dialog
5. Find **"PS4 JB Web Server"** under the newly added repository and click **Install**
6. Configure the port if needed, then click **Start**

### Method 2: Local Installation

1. Copy this repository into your Home Assistant's `/addons/` directory:
   ```
   /addons/ps4_jb_webserver/
   ```
2. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
3. Click **⋮ → Check for updates**
4. Find **"PS4 JB Web Server"** under **Local add-ons** and click **Install**
5. Configure the port if needed, then click **Start**

### Method 3: Self-Hosted Server (Standalone)

You can run this project completely outside of Home Assistant on any PC, Linux, Mac, or Raspberry Pi. Code paths automatically adapt when running standalone.

1. Clone or download this repository to your machine.
2. Ensure you have **Python 3** installed (`python3 --version`).
3. *(Optional)* Install **7-Zip** (`p7zip`) and add it to your system PATH if you want to use the auto-updater for `.7z` GitHub releases. Standard `.bin` file uploads through the Admin Panel work perfectly even without 7-Zip.
4. Open a console in the project directory and run the server (specify your port, default is 8000):
   ```bash
   python3 server.py 8000
   ```
5. Use `http://localhost:8000/_admin` to upload your GoldHEN payload or update it.
6. On your PS4 browser, navigate to: `http://<YOUR_PC_IP>:8000`

## Usage

| URL | Description |
|-----|-------------|
| `http://<HA_IP>:<port>/` | PSFree exploit page (point your PS4 browser here) |
| `http://<HA_IP>:<port>/_admin` | Admin panel for GoldHEN management |
| `http://<HA_IP>:<port>/goldhen.bin` | Direct link to GoldHEN payload |

### Updating GoldHEN

There are two methods to update the GoldHEN payload:

**Method 1: Automatic Update (GitHub)**
1. Open the admin panel at `http://<HA_IP>:<port>/_admin`
2. Click **"Update GoldHEN (Github)"**
3. The add-on will automatically fetch the latest **pre-release** from the [GoldHEN releases page](https://github.com/GoldHEN/GoldHEN/releases), extract `goldhen.bin` from the `.7z` archive, and make it available.

**Method 2: Manual File Upload**
1. Download the latest GoldHEN release from [SiSTRo's Ko-fi page](https://ko-fi.com/sistro).
2. Open the admin panel at `http://<HA_IP>:<port>/_admin`
3. Under the **"Upload GoldHEN"** section, click **"Choose File"** to select your file.
4. You can upload either a raw `goldhen.bin` file or a `.7z` / `.zip` archive containing the payload. The server will automatically extract the binary.
5. Click **"Upload"** to process the file and save it to your local server.

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `port` | `8000` | HTTP server listening port |

## Project Structure

```
├── config.yaml     # Add-on metadata and options
├── build.yaml      # Architecture-specific base images
├── Dockerfile      # Container build instructions
├── run.sh          # Entrypoint script
├── server.py       # Custom HTTP server with admin API
└── web/            # Static files served to PS4
    └── index.html  # PSFree exploit entry point
```

## Changelog

**v1.1.0**
- Fully renewed base (thanks to [Feyzee61](https://github.com/Feyzee61)'s [ps4jb](https://github.com/Feyzee61/ps4jb) project)
- Added firmware support for 5.05, 6.72, 7.00 up to 9.60
- Added manual file upload support for .bin and .7z files (GitHub version may sometimes be outdated)

**v1.0.0**
- Added persistent storage for `goldhen.bin` to survive add-on restarts
- Added Admin Panel (`/_admin`) for managing GoldHEN updates
- Added offline caching for the PS4 browser via AppCache
- Added Ingress support for Home Assistant dashboard
- Added ability to install via Custom Repository URL

## Credits

This add-on bundles and builds upon the incredible work of the PS4 homebrew community. The heart and core logic of this web server implementation was derived directly from the amazing work of **[Feyzee61](https://github.com/Feyzee61)**.

- **[ps4jb](https://github.com/Feyzee61/ps4jb)** (Licensed under [GPL-3.0](https://github.com/Feyzee61/ps4jb/blob/main/LICENSE)) by [Feyzee61](https://github.com/Feyzee61) — The core exploit host logic and inspiration for this project.
- **[GoldHEN](https://github.com/GoldHEN/GoldHEN)** ([Repository](https://github.com/GoldHEN/GoldHEN)) by [SiSTRo](https://github.com/SiSTR0) — The Homebrew Enabler for PS4, providing debug settings, FTP server, plugin support, cheat menu, and much more.
- **PS4 Scene Contributors** — Countless developers, researchers, and testers who made PS4 jailbreaking possible.

## License

This project is licensed under the **GNU General Public License v3.0**.
