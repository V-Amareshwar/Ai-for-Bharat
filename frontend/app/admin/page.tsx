"use client";

import { useState, useEffect } from "react";

type Application = {
  id: string;
  user_id: string;
  status: string;
  timestamp: number;
  form_data: Record<string, string | null>;
  rejection_reason?: string;
};

export default function AdminDashboard() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch all applications from the FastAPI backend
  const fetchApplications = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/dummy-gov/applications");
      const data = await response.json();
      setApplications(data.applications);
      setLoading(false);
    } catch (error) {
      console.error("Failed to fetch applications:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
    // Auto-refresh every 5 seconds to show new live submissions
    const interval = setInterval(fetchApplications, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (id: string) => {
    await fetch(`http://localhost:8000/api/v1/dummy-gov/applications/${id}/approve`, {
      method: "PUT",
    });
    setSelectedApp(null);
    fetchApplications();
  };

  const handleReject = async (id: string) => {
    if (!rejectReason.trim()) return alert("Please provide a reason for rejection.");
    
    await fetch(`http://localhost:8000/api/v1/dummy-gov/applications/${id}/reject`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: rejectReason }),
    });
    
    setShowRejectInput(false);
    setRejectReason("");
    setSelectedApp(null);
    fetchApplications();
  };

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-800 mb-2">Government Admin Portal</h1>
        <p className="text-slate-500 mb-8">Review and manage dynamic citizen scheme applications.</p>

        {/* The Applications Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-slate-500 animate-pulse">Loading applications...</div>
          ) : applications.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No applications found. Try submitting one via voice!</div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-100 text-slate-600 text-sm uppercase tracking-wider">
                  <th className="p-4 font-semibold">Application ID</th>
                  <th className="p-4 font-semibold">Citizen ID</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4 font-medium text-slate-800">{app.id}</td>
                    <td className="p-4 text-slate-600">{app.user_id}</td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        app.status === "Approved" ? "bg-green-100 text-green-700" :
                        app.status === "Rejected" ? "bg-red-100 text-red-700" :
                        app.status === "Submitted" ? "bg-blue-100 text-blue-700" :
                        "bg-orange-100 text-orange-700"
                      }`}>
                        {app.status}
                      </span>
                    </td>
                    <td className="p-4">
                      <button 
                        onClick={() => { setSelectedApp(app); setShowRejectInput(false); }}
                        className="text-sm bg-slate-800 text-white px-4 py-2 rounded-lg hover:bg-slate-700 transition-colors"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Dynamic Modal for Viewing Full Form Details */}
      {selectedApp && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
            <div className="flex justify-between items-center mb-6 border-b pb-4">
              <h2 className="text-2xl font-bold text-slate-800">Application {selectedApp.id}</h2>
              <button onClick={() => setSelectedApp(null)} className="text-slate-400 hover:text-slate-600 text-2xl">&times;</button>
            </div>

            {/* Render ALL Dynamic Fields Extracted by the AI */}
            <div className="bg-slate-50 rounded-xl p-5 border border-slate-100 mb-6 space-y-3">
              <h3 className="font-semibold text-slate-700 mb-4 border-b pb-2">Extracted Citizen Data</h3>
              {Object.keys(selectedApp.form_data).length === 0 ? (
                <p className="text-slate-500 text-sm text-center">No data extracted yet.</p>
              ) : (
                Object.entries(selectedApp.form_data).map(([key, value]) => (
                  <div key={key} className="flex flex-col sm:flex-row sm:justify-between sm:items-center border-b border-slate-200 border-dashed pb-2 last:border-0">
                    <span className="text-slate-500 text-sm font-medium capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="text-slate-800 font-semibold">{value || "—"}</span>
                  </div>
                ))
              )}
            </div>

            {selectedApp.status === "Rejected" && selectedApp.rejection_reason && (
              <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-6 border border-red-100">
                <strong>Rejection Reason:</strong> {selectedApp.rejection_reason}
              </div>
            )}

            {/* Accept / Reject Controls */}
            {selectedApp.status !== "Approved" && selectedApp.status !== "Rejected" && (
              <div className="flex flex-col gap-3">
                {!showRejectInput ? (
                  <div className="flex gap-3">
                    <button 
                      onClick={() => handleApprove(selectedApp.id)}
                      className="flex-1 bg-green-600 text-white font-bold py-3 rounded-xl hover:bg-green-700 transition-colors"
                    >
                      ✓ Approve Application
                    </button>
                    <button 
                      onClick={() => setShowRejectInput(true)}
                      className="flex-1 bg-red-100 text-red-700 font-bold py-3 rounded-xl hover:bg-red-200 transition-colors"
                    >
                      ✕ Reject
                    </button>
                  </div>
                ) : (
                  <div className="bg-red-50 p-4 rounded-xl border border-red-200 animate-fade-in-up">
                    <label className="block text-red-800 font-semibold mb-2">Reason for Rejection:</label>
                    <textarea 
                      className="w-full p-3 rounded-lg border border-red-200 mb-3 focus:outline-none focus:ring-2 focus:ring-red-400"
                      rows={3}
                      placeholder="e.g., Annual income exceeds scheme limits."
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <button 
                        onClick={() => handleReject(selectedApp.id)}
                        className="bg-red-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-red-700 transition-colors"
                      >
                        Confirm Rejection
                      </button>
                      <button 
                        onClick={() => setShowRejectInput(false)}
                        className="bg-white text-slate-600 px-4 py-2 rounded-lg font-bold border hover:bg-slate-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}