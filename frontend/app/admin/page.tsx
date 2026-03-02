"use client";

import { useState, useEffect } from "react";

export default function AdminDashboard() {
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch all applications from our FastAPI Dummy Gov Sandbox
  const fetchApplications = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/dummy-gov/applications");
      if (!res.ok) throw new Error("Network response was not ok");
      const data = await res.json();
      setApplications(data.applications);
      setLoading(false);
    } catch (error) {
      console.error("Failed to fetch applications", error);
      setLoading(false);
    }
  };

  // Load data on mount and refresh every 5 seconds for the live demo feel
  useEffect(() => {
    fetchApplications();
    const interval = setInterval(fetchApplications, 5000);
    return () => clearInterval(interval);
  }, []);

  // Approve Button Logic
  const handleApprove = async (id: string) => {
    try {
      await fetch(`http://127.0.0.1:8000/api/v1/dummy-gov/applications/${id}/approve`, {
        method: "PUT",
      });
      fetchApplications(); // Refresh the UI immediately after approving
    } catch (error) {
      console.error("Failed to approve application", error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 sm:p-12">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 border-b border-gray-200 pb-4">
          <h1 className="text-3xl font-bold text-gray-900">Government Admin Portal</h1>
          <p className="text-gray-500 mt-2">Official Sandbox Environment for Jan-Sahayak</p>
        </div>

        <div className="bg-white shadow-lg rounded-xl overflow-hidden border border-gray-100">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">App ID</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Citizen Mobile</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Scheme</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-left text-xs font-bold text-slate-600 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading && applications.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500 animate-pulse">Loading applications...</td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">No applications pending. Talk to Didi to submit one!</td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap font-mono text-sm text-gray-900">{app.id}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{app.user_id}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{app.scheme}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-3 py-1 inline-flex text-xs leading-5 font-bold rounded-full ${
                          app.status === "Approved" 
                            ? "bg-green-100 text-green-800 border border-green-200" 
                            : "bg-amber-100 text-amber-800 border border-amber-200"
                        }`}>
                          {app.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {app.status !== "Approved" ? (
                          <button 
                            onClick={() => handleApprove(app.id)}
                            className="text-white bg-blue-600 hover:bg-blue-700 active:scale-95 px-4 py-2 rounded-lg font-medium transition-all shadow-sm"
                          >
                            Approve
                          </button>
                        ) : (
                          <span className="text-gray-400 italic">Processed</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}