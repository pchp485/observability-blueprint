import { useEffect, useState, useMemo } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Home = () => {
  const [hello, setHello] = useState(null);
  const [health, setHealth] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const maskedBackend = useMemo(() => {
    if (!BACKEND_URL) return "(not set)";
    try {
      const url = new URL(BACKEND_URL);
      return `${url.origin}`;
    } catch {
      return BACKEND_URL;
    }
  }, []);

  const fetchHello = async () => {
    try {
      const res = await axios.get(`${API}/`);
      setHello(res.data?.message || "");
    } catch (e) {
      setError(`GET /api/ failed: ${e?.message || e}`);
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await axios.get(`${API}/health`);
      setHealth(res.data);
    } catch (e) {
      setError(`GET /api/health failed: ${e?.message || e}`);
    }
  };

  const fetchItems = async () => {
    try {
      const res = await axios.get(`${API}/status`);
      setItems(res.data || []);
    } catch (e) {
      setError(`GET /api/status failed: ${e?.message || e}`);
    }
  };

  const createStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      await axios.post(`${API}/status`, { client_name: "web-app" });
      await fetchItems();
    } catch (e) {
      setError(`POST /api/status failed: ${e?.message || e}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHello();
    fetchHealth();
    fetchItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <header className="App-header">
        <a
          className="App-link"
          href="https://emergent.sh"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img alt="Emergent" src="https://avatars.githubusercontent.com/in/1201222?s=120&u=2686cf91179bbafbc7a71bfbc43004cf9ae1acea&v=4" />
        </a>
        <h1 className="mt-5">AetherCollect Demo Sprint</h1>
        <p className="opacity-80 text-sm">Backend: {maskedBackend}</p>

        <div className="mt-6 space-y-2">
          <p>hello: {hello ?? "…"}</p>
          <p>
            health: {health ? `${health.status} / db: ${health.db}` : "…"}
          </p>
        </div>

        <div className="mt-8">
          <button
            onClick={createStatus}
            disabled={loading}
            className="px-4 py-2 rounded bg-blue-500 hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Recording…" : "Record status"}
          </button>
        </div>

        {error && (
          <p className="mt-4 text-red-400 text-sm max-w-xl">{error}</p>
        )}

        <div className="mt-8 w-full max-w-2xl text-left">
          <h3 className="text-lg mb-2">Latest status checks</h3>
          <ul className="space-y-1 text-sm">
            {items.slice(0, 5).map((it) => (
              <li key={it.id} className="opacity-90">
                <code>{it.timestamp}</code> — <b>{it.client_name}</b>
              </li>
            ))}
            {items.length === 0 && (
              <li className="opacity-70">No status yet. Click "Record status".</li>
            )}
          </ul>
        </div>
      </header>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />}>
            <Route index element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;