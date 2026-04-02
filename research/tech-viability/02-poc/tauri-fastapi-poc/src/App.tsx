import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface PingResponse {
  status: string;
  timestamp: string;
}

interface DomainsResponse {
  domains: string[];
}

function App() {
  const [pingData, setPingData] = useState<PingResponse | null>(null);
  const [domainsData, setDomainsData] = useState<DomainsResponse | null>(null);
  const [sidecarStatus, setSidecarStatus] = useState<string>("checking...");
  const [pingError, setPingError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Check sidecar status via Tauri command
  useEffect(() => {
    async function checkStatus() {
      try {
        const status = await invoke<string>("sidecar_status");
        setSidecarStatus(status);
      } catch (e) {
        setSidecarStatus(`error: ${e}`);
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Call /api/ping from the FastAPI sidecar
  async function callPing() {
    setIsLoading(true);
    setPingError(null);
    try {
      const resp = await fetch("http://localhost:8000/api/ping");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: PingResponse = await resp.json();
      setPingData(data);
    } catch (e) {
      setPingError(String(e));
      setPingData(null);
    } finally {
      setIsLoading(false);
    }
  }

  // Call /api/domains from the FastAPI sidecar
  async function callDomains() {
    setIsLoading(true);
    setPingError(null);
    try {
      const resp = await fetch("http://localhost:8000/api/domains");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: DomainsResponse = await resp.json();
      setDomainsData(data);
    } catch (e) {
      setPingError(String(e));
      setDomainsData(null);
    } finally {
      setIsLoading(false);
    }
  }

  // Restart the sidecar via Tauri command
  async function restartSidecar() {
    try {
      const result = await invoke<string>("restart_sidecar");
      setSidecarStatus(result);
    } catch (e) {
      setSidecarStatus(`restart error: ${e}`);
    }
  }

  return (
    <main className="container">
      <h1>UltrERP - FastAPI Sidecar PoC</h1>
      <p className="subtitle">Tauri 2.x + Python FastAPI via localhost IPC</p>

      <div className="card">
        <h2>Sidecar Status</h2>
        <p className="status-line">
          <span className={`status-dot ${sidecarStatus.startsWith("running") ? "green" : "red"}`}></span>
          <code>{sidecarStatus}</code>
        </p>
        <button onClick={restartSidecar} className="btn-secondary">Restart Sidecar</button>
      </div>

      <div className="card">
        <h2>/api/ping</h2>
        <p>Health check endpoint. Returns status and UTC timestamp.</p>
        <button onClick={callPing} disabled={isLoading} className="btn-primary">
          {isLoading ? "Loading..." : "Call /api/ping"}
        </button>
        {pingData && (
          <pre className="response-box">
            {JSON.stringify(pingData, null, 2)}
          </pre>
        )}
        {pingError && (
          <pre className="response-box error">
            Error: {pingError}
          </pre>
        )}
      </div>

      <div className="card">
        <h2>/api/domains</h2>
        <p>Returns the list of ERP domain modules.</p>
        <button onClick={callDomains} disabled={isLoading} className="btn-primary">
          {isLoading ? "Loading..." : "Call /api/domains"}
        </button>
        {domainsData && (
          <pre className="response-box">
            {JSON.stringify(domainsData, null, 2)}
          </pre>
        )}
      </div>

      <div className="footer">
        <p>FastAPI sidecar runs at <code>http://localhost:8000</code></p>
        <p>PoC confirms Tauri webview can communicate with Python backend over HTTP.</p>
      </div>
    </main>
  );
}

export default App;
