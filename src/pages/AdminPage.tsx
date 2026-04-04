import { useEffect, useState } from "react";

import {
  fetchAuditLogs,
  fetchUsers,
  type AdminUser,
  type AuditLogEntry,
} from "../lib/api/admin";

export function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [userItems, auditItems] = await Promise.all([
          fetchUsers(),
          fetchAuditLogs(),
        ]);
        if (!active) return;
        setUsers(userItems);
        setAuditLogs(auditItems);
      } catch (err) {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Failed to load admin data");
      } finally {
        if (active) setLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="hero-card" style={{ width: "min(72rem, 100%)" }}>
      <h1 style={{ fontSize: "2rem", lineHeight: 1.1 }}>Admin</h1>
      <p className="caption">Owner-only visibility into users and the latest audit activity.</p>

      {error && (
        <p role="alert" className="field-error" style={{ marginTop: "1rem" }}>
          {error}
        </p>
      )}

      {loading ? (
        <p style={{ marginTop: "1rem" }}>Loading admin data…</p>
      ) : (
        <div style={{ display: "grid", gap: "2rem", marginTop: "1.5rem" }}>
          <section>
            <h2>Users</h2>
            <table className="results-table" aria-label="Users table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>{user.display_name}</td>
                    <td>{user.role}</td>
                    <td>{user.status}</td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty-row">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section>
            <h2>Audit Log</h2>
            <table className="results-table" aria-label="Audit log table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Target</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((entry) => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.created_at).toLocaleString()}</td>
                    <td>{entry.actor_id}</td>
                    <td>{entry.action}</td>
                    <td>{entry.entity_type}:{entry.entity_id}</td>
                  </tr>
                ))}
                {auditLogs.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty-row">
                      No audit entries found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </section>
  );
}