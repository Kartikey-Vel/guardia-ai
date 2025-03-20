import React from "react";

const DashboardMetrics = () => {
  // In a real app, this data would come from API calls
  const metrics = [
    {
      id: 1,
      label: "Active Cameras",
      value: "12",
      change: "+2",
      isPositive: true,
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      ),
    },
    {
      id: 2,
      label: "Alerts Today",
      value: "3",
      change: "-2",
      isPositive: false,
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      ),
    },
    {
      id: 3,
      label: "Storage Used",
      value: "68%",
      change: "+5%",
      isPositive: false,
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
          />
        </svg>
      ),
    },
  ];

  return (
    <>
      {metrics.map((metric) => (
        <div key={metric.id} className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between">
            <span className="text-indigo-600 bg-indigo-100 p-2 rounded-lg">
              {metric.icon}
            </span>
            <span
              className={`text-sm font-medium ${
                metric.isPositive ? "text-green-600" : "text-red-600"
              }`}
            >
              {metric.change}
            </span>
          </div>
          <p className="mt-4 text-2xl font-semibold">{metric.value}</p>
          <p className="text-gray-500">{metric.label}</p>
        </div>
      ))}
    </>
  );
};

export default DashboardMetrics;
