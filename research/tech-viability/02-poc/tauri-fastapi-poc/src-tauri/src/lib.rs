use log::{error, info};
use std::process::Command;
use std::sync::Mutex;
use tauri::{Manager, State};

// Mutable state to hold the sidecar child process
struct SidecarState {
    child: Option<std::process::Child>,
}

/// Resolve the path to the sidecar script and its venv Python interpreter.
///
/// In dev mode (debug build):
///   Tauri binary: src-tauri/target/debug/tauri-fastapi-poc
///   Sidecar dir:  src-tauri/sidecar/
///   Venv Python:  src-tauri/sidecar/.venv/bin/python3
///
/// In release mode:
///   Tauri binary: src-tauri/target/release/tauri-fastapi-poc
///   Sidecar dir:  src-tauri/sidecar/   (copied to bundle root by Tauri)
///   Venv Python:  src-tauri/sidecar/.venv/bin/python3
fn resolve_sidecar_paths() -> Result<(std::path::PathBuf, std::path::PathBuf, std::path::PathBuf), String> {
    // Use CARGO_MANIFEST_DIR which always points to src-tauri/ regardless of
    // where the binary was built (target/debug or target/release).
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
        .map_err(|_| "CARGO_MANIFEST_DIR not set - this must be run via cargo")?;

    let src_tauri = std::path::PathBuf::from(&manifest_dir);
    let sidecar_dir = src_tauri.join("sidecar");
    let sidecar_script = sidecar_dir.join("main.py");

    // Venv Python: .venv/bin/python3 on Unix, .venv/bin/python.exe on Windows
    let venv_python = if cfg!(windows) {
        sidecar_dir.join(".venv").join("Scripts").join("python.exe")
    } else {
        sidecar_dir.join(".venv").join("bin").join("python3")
    };

    Ok((sidecar_script, venv_python, sidecar_dir))
}

/// Spawn the FastAPI sidecar and return the process handle.
/// The sidecar runs at localhost:8000.
fn spawn_sidecar() -> Result<std::process::Child, String> {
    let (sidecar_script, python_exec, sidecar_dir) = resolve_sidecar_paths()?;

    info!("Sidecar script: {:?}", sidecar_script);
    info!("Python exec:    {:?}", python_exec);

    if !sidecar_script.exists() {
        return Err(format!("Sidecar script not found: {:?}", sidecar_script));
    }
    if !python_exec.exists() {
        return Err(format!("Python venv not found: {:?}. Run `pip install -r sidecar/requirements.txt` inside the venv.", python_exec));
    }

    // Pass --host and --port as uvicorn CLI args
    // Run from sidecar_dir so uvicorn can find `main:app` (main.py)
    let child = Command::new(&python_exec)
        .arg("-m")
        .arg("uvicorn")
        .arg("main:app")
        .arg("--host")
        .arg("0.0.0.0")
        .arg("--port")
        .arg("8000")
        .current_dir(&sidecar_dir)
        .spawn()
        .map_err(|e| format!("failed to spawn sidecar: {}", e))?;

    info!("FastAPI sidecar spawned with PID {}", child.id());
    Ok(child)
}

#[tauri::command]
fn sidecar_status(state: State<'_, Mutex<SidecarState>>) -> String {
    let state = state.lock().unwrap();
    match &state.child {
        Some(c) if c.id() > 0 => format!("running (pid {})", c.id()),
        _ => "not running".to_string(),
    }
}

#[tauri::command]
fn restart_sidecar(state: State<'_, Mutex<SidecarState>>) -> Result<String, String> {
    info!("Restarting sidecar...");

    // Kill existing sidecar
    {
        let mut s = state.lock().unwrap();
        if let Some(mut c) = s.child.take() {
            let _ = c.kill();
            let _ = c.wait();
            info!("Old sidecar killed");
        }
    }

    // Spawn new sidecar
    let child = spawn_sidecar()?;
    let pid = child.id();
    let mut s = state.lock().unwrap();
    s.child = Some(child);

    Ok(format!("restarted (pid {})", pid))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
        .format_timestamp_millis()
        .init();

    info!("Starting UltrERP Tauri PoC (Tauri 2.x + FastAPI sidecar)...");

    // Spawn the sidecar before building the Tauri app
    let sidecar_child: Option<std::process::Child> = match spawn_sidecar() {
        Ok(c) => Some(c),
        Err(e) => {
            error!("Failed to spawn sidecar: {}", e);
            // Continue anyway - the webview will show the connection error
            None
        }
    };

    let sidecar_state = Mutex::new(SidecarState { child: sidecar_child });

    tauri::Builder::default()
        .manage(sidecar_state)
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, sidecar_status, restart_sidecar])
        .setup(|app| {
            info!("Tauri app setup complete");
            if let Some(path) = app.path().app_data_dir().ok() {
                info!("App data dir: {:?}", path);
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                info!("Window close requested, killing sidecar...");
                if let Some(state) = window.try_state::<Mutex<SidecarState>>() {
                    let mut s = state.lock().unwrap();
                    if let Some(mut c) = s.child.take() {
                        let _ = c.kill();
                        let _ = c.wait();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}
