import React from "react";

const RecentAlerts = () => {
  // Mock data - in a real app, this would come from an API
  const alerts = [
    {
      id: 1,
      type: "Motion Detected",
      location: "Front Door",
      time: "10 minutes ago",
      severity: "high",
    },
    {
      id: 2,
      type: "Unknown Person",
      location: "Backyard",
      time: "1 hour ago",
      severity: "medium",
    },
    {
      id: 3,
      type: "Camera Offline",
      location: "Garage",
      time: "2 hours ago",
      severity: "low",
    },
  ];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "high":
        return "bg-red-100 text-red-800";
      case "medium":
        return "bg-yellow-100 text-yellow-800";
      case "low":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <h2 className="text-lg font-bold mb-4">Recent Alerts</h2>
      <div className="space-y-4">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="border-b pb-3 last:border-b-0 last:pb-0"
          >
            <div className="flex items-center justify-between mb-1">
              <div className="font-medium">{alert.type}</div>
              <span
                className={`text-xs font-medium px-2 py-1 rounded-full ${getSeverityColor(
                  alert.severity
                )}`}
              >
                {alert.severity}
              </span>
            </div>
            <div className="text-sm text-gray-500">
              <span>{alert.location}</span> • <span>{alert.time}</span>
            </div>
          </div>
        ))}
      </div>
      <button className="w-full mt-4 text-indigo-600 border border-indigo-600 py-2 rounded-md text-sm font-medium hover:bg-indigo-50 transition">
        View All Alerts
      </button>
    </div>
  );
};

export default RecentAlerts;
