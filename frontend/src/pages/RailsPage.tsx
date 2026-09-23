import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; store_id: number; label: string; length_cm: number; max_garment_length_cm: number | null };
export default function RailsPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const reload = () => api<R[]>("/rails").then(setRows);
  useEffect(() => { reload(); }, []);
  function draftValue(r: R): string {
    return r.id in drafts ? drafts[r.id] : (r.max_garment_length_cm == null ? "" : String(r.max_garment_length_cm));
  }
  async function save(r: R) {
    setMsg(""); setErr("");
    const raw = draftValue(r).trim();
    const value = raw === "" ? null : Number(raw);
    if (value !== null && (!Number.isFinite(value) || value <= 0)) {
      setErr(`${r.label}：请输入正数，或留空表示不限`);
      return;
    }
    try {
      await api(`/rails/${r.id}`, { method: "PATCH", body: JSON.stringify({ max_garment_length_cm: value }) });
      setMsg(`${r.label} 衣长上限已${value == null ? "清除（不限）" : `设为 ${value}cm`}`);
      setDrafts(d => { const next = { ...d }; delete d[r.id]; return next; });
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>挂杆</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>标签</th><th>门店</th><th>长度 cm</th><th>衣长上限 cm</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id}>
      <td>{r.label}</td><td>{r.store_id}</td><td className="mono">{r.length_cm}</td>
      <td><input
        type="number" min="1" inputMode="numeric" placeholder="不限"
        value={draftValue(r)}
        onChange={e => setDrafts(d => ({ ...d, [r.id]: e.target.value }))}
      /></td>
      <td><button onClick={() => save(r)}>保存</button></td>
    </tr>)}</tbody></table>
  </>);
}
