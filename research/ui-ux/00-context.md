# UI/UX Context

Source: /Volumes/2T_SSD_App/Projects/UltrERP/design-artifacts/A-Product-Brief/2026-03-30-erp-architecture-design.md

Desktop stack:
- Tauri 2.x (8MB installer vs 120MB Electron)
- Vite + React frontend
- shadcn/ui + Radix UI components
- Tailwind CSS

User split:
- Casual users (GUI): clicking through screens
- Power users (CLI): erp customers list, erp invoices create

Taiwan localization requirements:
- ROC dates: display as 114/03/30 for March 30, 2025
- Tax ID (統一編號): 8 digits + check digit, real-time validation
- Traditional Chinese throughout UI
- Phone formats, address formats

Core screens needed:
1. Customer list/create/edit (tax_id validation feedback)
2. Invoice creation with eGUI state indicator
3. Inventory check with reorder alerts
4. Order workflow

System integration:
- System tray icon for background operation
- Native notifications for eGUI state changes
- Keyboard shortcuts for power users

Component considerations:
- shadcn/ui Table for data grids
- shadcn/ui Dialog/Sheet for modals
- shadcn/ui Form with Zod validation
