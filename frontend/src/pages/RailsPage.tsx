import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = { id: number; store_id: number; label: string; length_cm: number; max_garment_cm: number | null };
export default function RailsPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [caps, setCaps] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => {
    api<R[]>("/rails").then(rs => {
      setRows(rs);
      setCaps(Object.fromEntries(rs.map(r => [r.id, r.max_garment_cm == null ? "" : String(r.max_garment_cm)])));
    });
  }, []);
  async function save(r: R) {
    setMsg(""); setErr("");
    const raw = (caps[r.id] ?? "").trim();
    if (raw && Number(raw) <= 0) { setErr(`${r.label} 上限必须为正数`); return; }
    try {
      const updated = await api<R>(`/rails/${r.id}`, {
        method: "PATCH",
        body: JSON.stringify({ max_garment_cm: raw === "" ? null : Number(raw) }),
      });
      setRows(rs => rs.map(x => x.id === updated.id ? updated : x));
      setMsg(`${r.label} 可收衣长上限已保存：${raw === "" ? "不限" : raw + "cm"}`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>挂杆</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>标签</th><th>门店</th><th>长度 cm</th><th>可收衣长上限 cm</th><th></th></tr></thead>
    <tbody>{rows.map(r => <tr key={r.id}>
      <td>{r.label}</td><td>{r.store_id}</td><td className="mono">{r.length_cm}</td>
      <td>
        <input
          className="mono"
          value={caps[r.id] ?? ""}
          placeholder="不限"
          style={{ width: "7rem" }}
          onChange={e => setCaps(c => ({ ...c, [r.id]: e.target.value }))}
        />
      </td>
      <td><button onClick={() => save(r)}>保存</button></td>
    </tr>)}</tbody></table>
  </>);
}
