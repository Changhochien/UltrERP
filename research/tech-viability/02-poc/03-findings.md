# Tauri 2.x + FastAPI Sidecar PoC Findings

## 1. Which Tauri Version Was Installed

- **Tauri CLI**: v2.x (latest stable via `npm create tauri-app`)
- **Tauri Rust crate**: `tauri = "2.10.3"` (from Cargo.lock)
- **Tauri plugins used**: `tauri-plugin-opener = "2.5.3"`
- **Node.js**: v23.9.0, npm 10.9.2
- **Rust**: cargo 1.88.0 (873a06493 2025-05-10)
- **Python**: 3.13.2 (Homebrew)
- **React**: 19.1.0 with TypeScript, Vite 7.x

## 2. Sidecar Spawning Behavior on macOS

### Pattern Used

The PoC uses a **child-process spawning** pattern rather than Tauri's `externalBinary`/`sidecar` build-system feature. The Rust backend spawns the Python sidecar as a subprocess via `std::process::Command` at application startup.

**Why not `externalBinary`?**
The `externalBinary` feature in Tauri 2.x is designed for pre-compiled binaries (e.g., PyInstaller builds). Using raw Python with a venv is simpler and more portable for a PoC. The spawning pattern is equivalent in behavior.

### Path Resolution

`CARGO_MANIFEST_DIR` is used to reliably locate the sidecar directory, because the Tauri binary can be at different paths depending on how it was launched (`target/debug/` vs `target/release/`):

```
src-tauri/
  sidecar/
    main.py          <- FastAPI app
    .venv/           <- Python virtual environment
      bin/python3    <- venv Python interpreter
    requirements.txt
```

The Rust sidecar path resolution:
```rust
let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")?;  // src-tauri/
let sidecar_dir = PathBuf::from(manifest_dir).join("sidecar");
let python_exec = sidecar_dir.join(".venv/bin/python3");
```

### Spawn Command

```rust
Command::new(&python_exec)
    .arg("-m")
    .arg("uvicorn")
    .arg("main:app")
    .arg("--host").arg("0.0.0.0")
    .arg("--port").arg("8000")
    .current_dir(&sidecar_dir)  // CRITICAL: must be sidecar/ for uvicorn to find main:app
    .spawn()?;
```

### Verified Behavior (macOS)

| Test | Result |
|------|--------|
| `cargo run` from `src-tauri/` | Sidecar spawns, both endpoints return 200 OK |
| `npm run tauri dev` | Same - Vite dev server + Tauri binary both start |
| `/api/ping` response | `{"status":"pong","timestamp":"2026-03-30T..."}` |
| `/api/domains` response | `{"domains":["customers","invoices","inventory"]}` |
| Window close → sidecar kill | Graceful shutdown via `on_window_event` |

### macOS-Specific Observations

1. **Python venv shim**: On macOS (Homebrew Python), `.venv/bin/python3` is a shell script that wraps the Homebrew Python interpreter. The working directory must be set explicitly in Rust's `Command::current_dir()` because subprocess working directory inheritance from a GUI app (Tauri's macOS app bundle) is not guaranteed.

2. **Port 8000 availability**: The sidecar binds to `0.0.0.0:8000` (not `localhost:8000`). The webview on macOS can reach it via `http://localhost:8000`. No special Tauri permissions are required for localhost HTTP in the webview - standard fetch works.

3. **No firewall prompt**: On first run, no macOS firewall prompt appears because the sidecar listens on `0.0.0.0` (not a privileged port) and only loopback traffic is used.

## 3. Issues with the Reference Implementation

### Path Resolution Bug (Fixed)

The original implementation used `std::env::current_exe()` with `parent().parent().parent()` to locate the sidecar directory. This is fragile and failed in practice because:

- The binary path during `cargo run` is `src-tauri/target/debug/tauri-fastapi-poc`
- `parent()` x3 = `src-tauri/` (correct)
- But the working directory of a GUI app on macOS is not guaranteed to be the project root
- The sidecar directory was found via `CARGO_MANIFEST_DIR` instead, which is a Cargo environment variable set at compile time and always points to the correct location

**Fix**: Use `CARGO_MANIFEST_DIR` instead of `current_exe()` path walking.

### CORS Configuration

FastAPI's `CORSMiddleware` was configured with `allow_origins=["*"]` to allow the Tauri webview to make cross-origin requests. In production, this should be restricted to the Tauri app's allowed origins.

### CSP in tauri.conf.json

The Content Security Policy was set to allow connections to `localhost:8000`:
```json
"csp": "default-src 'self'; connect-src 'self' http://localhost:8000 http://localhost:1420; ..."
```

Without this, the webview's fetch to `http://localhost:8000` would be blocked by the CSP.

## 4. Production Recommendations

### 1. PyInstaller Over Raw Python

For production desktop distribution, compile the Python sidecar with PyInstaller (as demonstrated in the `dieharders/example-tauri-v2-python-server-sidecar` reference repo). This:
- Eliminates the Python runtime dependency on the user's machine
- Allows use of Tauri's built-in `externalBinary` sidecar feature
- Produces a single self-contained app bundle

### 2. Windows NSIS Sidecar Bug (Issue #15134)

As documented in the survey, the NSIS installer on Windows does not replace the sidecar binary on reinstalls. **This must be tested and worked around** before any Windows production deployment.

**Workaround options**:
- Use the WiX installer instead of NSIS
- Implement a post-install script that explicitly replaces the sidecar binary
- Use PyInstaller + `externalBinary` and configure Tauri to handle upgrades

### 3. Sidecar Lifecycle Management

The PoC handles graceful shutdown via `on_window_event`, killing the sidecar child process when the window closes. This should be extended to:
- Handle `SIGTERM` signals
- Detect sidecar crashes and optionally restart
- Implement a health-check ping from the webview on startup to confirm sidecar availability

### 4. Port Conflict Handling

The PoC hardcodes port 8000. A production app should:
- Check if the port is available and fall back to an alternative port if not
- Store the chosen port in a location accessible to both the Rust backend (for spawning) and the React frontend (for fetch URLs)

### 5. Security Considerations

- The sidecar runs as the same user as the Tauri app (no privilege separation)
- The FastAPI app should implement authentication (e.g., a shared secret) to prevent other local processes from calling the sidecar API
- CORS should be restricted to known origins, not `*`

## Project Structure

```
02-poc/
  tauri-fastapi-poc/
    src-tauri/
      src/lib.rs           <- Rust: sidecar spawning, Tauri commands
      sidecar/
        main.py            <- FastAPI app (ping, domains endpoints)
        .venv/             <- Python venv with fastapi, uvicorn
        requirements.txt
      tauri.conf.json
      Cargo.toml
    src/
      App.tsx              <- React: calls http://localhost:8000/api/ping
      App.css
    package.json
    vite.config.ts
```

## Running the PoC

```bash
cd tauri-fastapi-poc/src-tauri/sidecar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ../..
npm install
npm run tauri dev
```

The Tauri window will open showing the PoC UI. Click "Call /api/ping" to verify the FastAPI sidecar is responding.
