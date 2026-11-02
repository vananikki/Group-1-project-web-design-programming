# Backend deployment and public access

This document explains how to run the FastAPI backend locally, how to expose the frontend publicly with ngrok, and how to avoid CORS issues when the frontend runs on a public domain while the backend remains local.

## 1) Run backend locally

From the project root:

```bash
cd backend
PYTHONPATH=. .venv/bin/python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

This binds the API on port 8000 and allows access from:

- localhost
- LAN IPs
- Tailscale IPs
- other local devices on the same network

If you want the API to stay local-only, use `127.0.0.1` instead of `0.0.0.0`.

## 2) Run frontend locally

```bash
cd ..
python3 -m http.server 5500 --bind 0.0.0.0 --directory frontend
```

The frontend is then available at:

- http://localhost:5500
- http://<LAN_IP>:5500
- http://<Tailscale_IP>:5500

## 3) Expose frontend to the public via ngrok

Use the static ngrok domain you already have:

```bash
ngrok http --domain=racoon-synopsis-daintily.ngrok-free.dev 5500
```

The public frontend URL is:

```text
https://racoon-synopsis-daintily.ngrok-free.dev
```

In this setup, the backend stays local; ngrok only exposes the frontend. That keeps the app simpler and avoids exposing the backend directly.

## 4) CORS configuration

The backend must allow the public frontend origin. In the backend environment or `.env`, set:

```env
CORS_ORIGINS=https://racoon-synopsis-daintily.ngrok-free.dev
```

The app also allows `.ngrok-free.app` / `.ngrok.io` origins through the regex in the CORS middleware.

## 5) Fix the frontend API URL

The frontend chooses its backend URL from the current page hostname. When the page is served from ngrok, it must not try to call the same public host on port 8000. Instead, it should call the local backend.

Use one of these patterns:

```js
sessionStorage.setItem("online-judge-api-base-url", "http://127.0.0.1:8000");
location.reload();
```

Or for LAN/Tailscale:

```js
sessionStorage.setItem("online-judge-api-base-url", "http://192.168.1.50:8000");
location.reload();
```

This is the correct behavior for a public frontend with a local backend.

## 6) Recommended architecture

This project is best run in the following pattern:

```text
Browser -> ngrok public frontend -> local frontend server -> local backend API
```

This setup works well for:

- localhost access
- LAN access from other devices
- Tailscale access
- public access through ngrok

## 7) Troubleshooting

### Frontend opens but API calls fail

Check that:

- backend is running on port 8000
- frontend is running on port 5500
- the browser is not trying to call `https://<ngrok-domain>:8000`
- CORS is allowed for the ngrok frontend domain

### Browser blocks requests with CORS

Verify that the backend includes the origin in `CORS_ORIGINS` and that the request origin matches exactly. For example:

```text
https://racoon-synopsis-daintily.ngrok-free.dev
```

### Local backend is unreachable from LAN

If another device on the LAN cannot reach the backend, run it on `0.0.0.0:8000` and make sure the firewall/network allows traffic on port 8000.

### Public access still fails

Open the URL in the browser and inspect the console/network tab. The usual problem is the frontend constructing the wrong API base URL.
