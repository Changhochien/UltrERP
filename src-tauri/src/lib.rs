use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{
    menu::MenuBuilder,
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, Runtime, Window, WindowEvent,
};

const MAIN_WINDOW_LABEL: &str = "main";
const TRAY_ICON_ID: &str = "main-tray";
const TRAY_MENU_RESTORE_ID: &str = "restore";
const TRAY_MENU_QUIT_ID: &str = "quit";

#[derive(Default)]
struct DesktopShellState {
    quitting: AtomicBool,
}

fn restore_main_window<R: Runtime>(app: &AppHandle<R>) {
    let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) else {
        return;
    };

    if window.is_minimized().unwrap_or(false) {
        let _ = window.unminimize();
    }

    let _ = window.show();
    let _ = window.set_focus();
}

fn hide_window_to_tray<R: Runtime>(window: &Window<R>) {
    let _ = window.hide();
}

fn request_explicit_quit<R: Runtime>(app: &AppHandle<R>) {
    app.state::<DesktopShellState>()
        .quitting
        .store(true, Ordering::SeqCst);
    app.exit(0);
}

fn build_tray<R: Runtime, M: Manager<R>>(manager: &M) -> tauri::Result<()> {
    let app = manager.app_handle();

    let menu = MenuBuilder::new(manager)
        .text(TRAY_MENU_RESTORE_ID, "Show UltrERP")
        .separator()
        .text(TRAY_MENU_QUIT_ID, "Quit UltrERP")
        .build()?;

    let mut tray_builder = TrayIconBuilder::with_id(TRAY_ICON_ID)
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("UltrERP");

    if let Some(icon) = app.default_window_icon().cloned() {
        tray_builder = tray_builder.icon(icon);
    }

    tray_builder
        .on_menu_event(|app, event| match event.id().as_ref() {
            TRAY_MENU_RESTORE_ID => restore_main_window(app),
            TRAY_MENU_QUIT_ID => request_explicit_quit(app),
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                restore_main_window(tray.app_handle());
            }
        })
        .build(manager)?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(DesktopShellState::default())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            build_tray(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() != MAIN_WINDOW_LABEL {
                return;
            }

            if let WindowEvent::CloseRequested { api, .. } = event {
                if window
                    .state::<DesktopShellState>()
                    .quitting
                    .load(Ordering::SeqCst)
                {
                    return;
                }

                api.prevent_close();
                hide_window_to_tray(window);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}