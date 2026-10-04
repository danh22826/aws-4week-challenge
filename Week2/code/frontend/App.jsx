import { useState } from "react";

function App() {
  const [symptoms, setSymptoms] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    const res = await fetch("http://<ALB-DNS>/api/v1/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptoms })
    });
    setResult(await res.json());
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>MediAssist — Nhập triệu chứng</h2>
      <textarea value={symptoms} onChange={e => setSymptoms(e.target.value)} rows={4} cols={50} />
      <br />
      <button onClick={handleSubmit}>Phân tích</button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default App;