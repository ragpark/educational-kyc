const { useState, useEffect, useRef } = React;

function RadarChart({ centre, course }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const labels = Array.from(new Set([
      ...Object.keys(centre.lab_capabilities || {}),
      ...(course.min_lab_req || []),
      ...Object.keys(centre.skill_levels || {}),
      ...(course.skill_prereqs || []),
    ]));
    const centreData = labels.map(l => centre.lab_capabilities[l] || centre.skill_levels[l] || 0);
    const courseData = labels.map(l => (course.min_lab_req.includes(l) || course.skill_prereqs.includes(l)) ? 1 : 0);

    const chart = new Chart(canvasRef.current, {
      type: 'radar',
      data: {
        labels,
        datasets: [
          {
            label: 'Centre',
            data: centreData,
            backgroundColor: 'rgba(59,130,246,0.2)',
            borderColor: 'rgb(59,130,246)',
          },
          {
            label: 'Course',
            data: courseData,
            backgroundColor: 'rgba(16,185,129,0.2)',
            borderColor: 'rgb(16,185,129)',
          },
        ],
      },
      options: {
        responsive: true,
        scales: { r: { beginAtZero: true } },
      },
    });
    return () => chart.destroy();
  }, [centre, course]);
  return <canvas ref={canvasRef} className="w-full h-64"></canvas>;
}

function Dashboard() {
  const [centreId, setCentreId] = useState(1);
  const [data, setData] = useState({ centre: { lab_capabilities: {}, skill_levels: {} }, recommendations: [] });
  const [modeFilter, setModeFilter] = useState({ online: true, onsite: true, hybrid: true });
  const [minScore, setMinScore] = useState(0);
  const [open, setOpen] = useState(null);

  const fetchData = () => {
    fetch(`/recommend/${centreId}?top_n=20`)
      .then(res => res.json())
      .then(setData);
  };

  useEffect(() => {
    fetchData();
  }, [centreId]);

  const filtered = data.recommendations.filter(c => modeFilter[c.delivery_mode] && c.score >= minScore);

  return (
    <div className="space-y-4">
      <div className="flex space-x-2 items-center">
        <label>Centre ID:</label>
        <input className="border p-1" value={centreId} onChange={e => setCentreId(e.target.value)} />
        <button className="bg-blue-500 text-white px-2 py-1" onClick={fetchData}>Load</button>
      </div>
      <div className="flex space-x-4">
        {Object.keys(modeFilter).map(mode => (
          <label key={mode} className="flex items-center space-x-1">
            <input type="checkbox" checked={modeFilter[mode]} onChange={e => setModeFilter({ ...modeFilter, [mode]: e.target.checked })} />
            <span>{mode}</span>
          </label>
        ))}
        <label className="flex items-center space-x-1">
          <span>Min score</span>
          <input type="number" className="border p-1 w-20" value={minScore} step="0.1" onChange={e => setMinScore(parseFloat(e.target.value) || 0)} />
        </label>
      </div>
      {filtered.map((course, idx) => (
        <div key={course.id} className="bg-white p-4 rounded shadow" onClick={() => setOpen(open === idx ? null : idx)}>
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-semibold">{course.title}</h3>
            <span className="text-sm">{(course.score * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2 mt-2">
            <div className="bg-blue-500 h-2 rounded" style={{ width: `${course.score * 100}%` }}></div>
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

ReactDOM.createRoot(document.getElementById('root')).render(<Dashboard />);
