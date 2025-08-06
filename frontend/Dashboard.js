const { useState, useEffect, useRef } = React;

// Determine initial centre ID from the query string, defaulting to 1
function getInitialCentreId() {
  const params = new URLSearchParams(window.location.search);
  const value = parseInt(params.get("centre_id"), 10);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

function RadarChart({ centre, course }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const minLabReq = Array.isArray(course.min_lab_req)
      ? course.min_lab_req
      : [];
    const skillPrereqs = Array.isArray(course.skill_prereqs)
      ? course.skill_prereqs
      : [];
    const labels = Array.from(
      new Set([
        ...Object.keys(centre.lab_capabilities || {}),
        ...minLabReq,
        ...Object.keys(centre.skill_levels || {}),
        ...skillPrereqs,
      ])
    );
    const centreData = labels.map(
      (l) => centre.lab_capabilities[l] || centre.skill_levels[l] || 0
    );
    const courseData = labels.map((l) =>
      minLabReq.includes(l) || skillPrereqs.includes(l) ? 1 : 0
    );

    const chart = new Chart(canvasRef.current, {
      type: "radar",
      data: {
        labels,
        datasets: [
          {
            label: "Centre",
            data: centreData,
            backgroundColor: "rgba(59,130,246,0.2)",
            borderColor: "rgb(59,130,246)",
          },
          {
            label: "Course",
            data: courseData,
            backgroundColor: "rgba(16,185,129,0.2)",
            borderColor: "rgb(16,185,129)",
          },
        ],
      },
      options: { responsive: true, scales: { r: { beginAtZero: true } } },
    });
    return () => chart.destroy();
  }, [centre, course]);

  return <canvas ref={canvasRef} className="w-full h-64"></canvas>;
}

function Dashboard() {
  const [centreId, setCentreId] = useState(getInitialCentreId());
  const [data, setData] = useState({
    centre: { lab_capabilities: {}, skill_levels: {}, risk_score: 0, partner_tier: "" },
    recommendations: [],
  });
  const [error, setError] = useState(null);
  const [modeFilter, setModeFilter] = useState({
    online: true,
    onsite: true,
    hybrid: true,
  });
  const [minScore, setMinScore] = useState(0);
  const [open, setOpen] = useState(null);

  const fetchData = async () => {
    setError(null);
    try {
      const res = await fetch(`/recommend/1?top_n=20`);
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
      setData({
        centre: { lab_capabilities: {}, skill_levels: {}, risk_score: 0, partner_tier: "" },
        recommendations: [],
      });
    }
  };

  useEffect(() => {
    fetchData();
  }, [centreId]);

  const filtered = data.recommendations.filter(
    (c) => modeFilter[c.delivery_mode] && c.score >= minScore
  );

  return (
    <div className="space-y-4">
      {error && <div className="p-2 bg-red-100 text-red-700">{error}</div>}
      <div className="flex space-x-2 items-center">
        <label>Centre ID:</label>
        <input
          className="border p-1"
          value={centreId}
          onChange={(e) => setCentreId(e.target.value)}
        />
        <button
          className="bg-blue-500 text-white px-2 py-1"
          onClick={fetchData}
        >
          Load
        </button>
      </div>
      <div className="bg-white p-4 rounded shadow">
        <div className="flex justify-between text-sm mb-1">
          <span>Risk Score</span>
          <span>{data.centre.partner_tier} ({data.centre.risk_score.toFixed(1)})</span>
        </div>
        <div className="w-full bg-gray-200 rounded h-4 relative">
          <div
            className="bg-green-500 h-4 rounded"
            style={{ width: `${(data.centre.risk_score / 10) * 100}%` }}
          ></div>
          <div className="absolute inset-0 flex justify-between text-xs px-1">
            <span>0</span>
            <span>10</span>
          </div>
        </div>
      </div>
      <div className="flex space-x-4">
        {Object.keys(modeFilter).map((mode) => (
          <label key={mode} className="flex items-center space-x-1">
            <input
              type="checkbox"
              checked={modeFilter[mode]}
              onChange={(e) =>
                setModeFilter({ ...modeFilter, [mode]: e.target.checked })
              }
            />
            <span>{mode}</span>
          </label>
        ))}
        <label className="flex items-center space-x-1">
          <span>Min score</span>
          <input
            type="number"
            className="border p-1 w-20"
            value={minScore}
            step="0.1"
            onChange={(e) => setMinScore(parseFloat(e.target.value) || 0)}
          />
        </label>
      </div>
      {filtered.map((course, idx) => (
        <div
          key={course.id}
          className="bg-white p-4 rounded shadow"
          onClick={() => setOpen(open === idx ? null : idx)}
        >
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold">{course.title}</h3>
            <span className="text-sm">{(course.score * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2 mt-2">
            <div
              className="bg-blue-500 h-2 rounded"
              style={{ width: `${course.score * 100}%` }}
            ></div>
          </div>
          {open === idx && (
            <div className="mt-4">
              <RadarChart centre={data.centre} course={course} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<Dashboard />);

