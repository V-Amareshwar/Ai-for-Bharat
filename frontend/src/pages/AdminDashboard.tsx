import React, { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Api } from '../services/api';
import './AdminDashboard.css';

interface Application {
    application_id: string;
    scheme_id: string;
    user_id: string;
    data: Record<string, any>;
    status: string;
    reason?: string;
    created_at: string;
}

const renderJsonWithHighlights = (jsonObj: any) => {
    const jsonStr = JSON.stringify(jsonObj, null, 2);
    const highlighted = jsonStr.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        function (match) {
            let cls = 'json-value';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        }
    );
    return <pre dangerouslySetInnerHTML={{ __html: highlighted }}></pre>;
};

export const AdminDashboard: React.FC = () => {
    const [applications, setApplications] = useState<Application[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedApp, setSelectedApp] = useState<Application | null>(null);
    const [reason, setReason] = useState("");
    const [actionLoading, setActionLoading] = useState(false);

    // Authentication State
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [passwordInput, setPasswordInput] = useState("");

    useEffect(() => {
        if (isAuthenticated) {
            fetchApplications();
        }
    }, [isAuthenticated]);

    const fetchApplications = async () => {
        try {
            setLoading(true);
            const data = await Api.getAdminApplications();
            setApplications(data);
        } catch (err: any) {
            setError("Failed to load applications. Make sure the backend is running.");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleStatusUpdate = async (status: string) => {
        if (!selectedApp) return;

        try {
            setActionLoading(true);
            await Api.updateAdminApplicationStatus(selectedApp.application_id, status, reason);
            // Optimistic visual update
            setApplications(prev => prev.map(app =>
                app.application_id === selectedApp.application_id
                    ? { ...app, status, reason }
                    : app
            ));
            setSelectedApp(null);
            setReason("");
        } catch (err: any) {
            alert("Error updating application status.");
            console.error(err);
        } finally {
            setActionLoading(false);
        }
    };
    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (passwordInput === 'kmit') {
            setIsAuthenticated(true);
        } else {
            alert("Incorrect password. Hint for Hackathon Judges: kmit");
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="admin-login-container">
                <div className="admin-login-card">
                    <ShieldCheck size={56} className="admin-login-icon" />
                    <h2>Officer Portal Login</h2>
                    <p>Enter the administrative password to access the DidiGov tracking portal.</p>
                    <form onSubmit={handleLogin}>
                        <input
                            type="password"
                            value={passwordInput}
                            onChange={(e) => setPasswordInput(e.target.value)}
                            placeholder="Password (Hint: kmit)"
                            autoFocus
                        />
                        <button type="submit" className="login-btn">
                            Access Dashboard
                        </button>
                    </form>
                </div>
            </div>
        );
    }

    if (loading) return <div className="admin-loading">Loading Officer Dashboard...</div>;
    if (error) return <div className="admin-error">{error}</div>;

    return (
        <div className="admin-container">
            <header className="admin-header">
                <h1>DidiGov Officer Portal</h1>
                <p>Review and verify citizen scheme applications</p>
            </header>

            <div className="admin-grid">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Scheme</th>
                            <th>Citizen Mobile</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {applications.map(app => (
                            <tr key={app.application_id}>
                                <td>{app.application_id.split('-')[1]}</td>
                                <td>{app.scheme_id}</td>
                                <td>{app.user_id}</td>
                                <td>
                                    <span className={`status-badge status-${app.status.toLowerCase()}`}>
                                        {app.status}
                                    </span>
                                </td>
                                <td>{new Date(app.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button
                                        className="btn-review"
                                        onClick={() => setSelectedApp(app)}
                                    >
                                        Review
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {applications.length === 0 && (
                            <tr>
                                <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                                    No pending applications found in the DynamoDB queue.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {selectedApp && (
                <div className="modal-overlay" onClick={() => setSelectedApp(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Review Application: {selectedApp.application_id}</h2>
                            <button className="btn-close" onClick={() => setSelectedApp(null)}>✕</button>
                        </div>

                        <div className="modal-body">
                            <div className="info-group">
                                <label>Citizen Identity</label>
                                <div className="info-value text-mono">{selectedApp.user_id}</div>
                            </div>
                            <div className="info-group">
                                <label>Government Scheme</label>
                                <div className="info-value">{selectedApp.scheme_id}</div>
                            </div>

                            <div className="data-payload-section">
                                <h3>Extracted Application Payload</h3>
                                <div className="json-viewer">
                                    {renderJsonWithHighlights(selectedApp.data)}
                                </div>
                            </div>

                            {selectedApp.status === 'PENDING' ? (
                                <div className="action-section">
                                    <label>Officer Review Notes / Reason</label>
                                    <textarea
                                        value={reason}
                                        onChange={e => setReason(e.target.value)}
                                        placeholder="e.g., Aadhaar fuzzy match failed, missing secondary document..."
                                        rows={3}
                                    />
                                    <div className="action-buttons">
                                        <button
                                            className="btn-reject"
                                            onClick={() => handleStatusUpdate('REJECTED')}
                                            disabled={actionLoading}
                                        >
                                            Reject Application
                                        </button>
                                        <button
                                            className="btn-approve"
                                            onClick={() => handleStatusUpdate('APPROVED')}
                                            disabled={actionLoading}
                                        >
                                            Approve & Disburse
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="action-section">
                                    <div className={`status-banner status-${selectedApp.status.toLowerCase()}`}>
                                        This application is already <strong>{selectedApp.status}</strong>.
                                        {selectedApp.reason && <p>Reason: {selectedApp.reason}</p>}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
