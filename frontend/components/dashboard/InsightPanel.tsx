"use client";

import { Card, Chip, ScrollShadow } from "@heroui/react";
import { MOCK_ALERTS, SeverityType } from "@/lib/data";
import { AlertCircle, Clock, Info, ShieldAlert, AlertTriangle } from "lucide-react";

const getSeverityColor = (severity: SeverityType) => {
  switch (severity) {
    case "CRITICAL":
      return "danger";
    case "HIGH":
      return "warning";
    case "MEDIUM":
      return "accent";
    case "LOW":
      return "default";
    default:
      return "default";
  }
};

const getSeverityIcon = (severity: SeverityType) => {
  switch (severity) {
    case "CRITICAL":
      return <ShieldAlert size={16} />;
    case "HIGH":
      return <AlertTriangle size={16} />;
    case "MEDIUM":
      return <AlertCircle size={16} />;
    case "LOW":
      return <Info size={16} />;
    default:
      return <Info size={16} />;
  }
};

export function InsightPanel() {
  return (
    <Card className="bg-background border-none h-full shadow-sm">
      <Card.Header className="flex justify-between items-center p-4 border-b border-divider">
        <div className="flex items-center gap-2">
          <AlertCircle className="text-primary" size={20} />
          <h3 className="text-lg font-bold">Recent Alerts</h3>
        </div>
        <Chip size="sm" variant="soft" color="danger">
          {MOCK_ALERTS.filter(a => a.severity === "CRITICAL" || a.severity === "HIGH").length} Critical
        </Chip>
      </Card.Header>
      
      <Card.Content className="p-0">
        <ScrollShadow className="max-h-[500px]">
          <div className="flex flex-col">
            {MOCK_ALERTS.map((alert, idx) => (
              <div 
                key={alert.id}
                className={`p-4 flex gap-4 ${
                  idx !== MOCK_ALERTS.length - 1 ? "border-b border-divider" : ""
                } hover:bg-default-50 transition-colors`}
              >
                <div className="pt-1">
                  <div className={`p-2 rounded-full bg-${getSeverityColor(alert.severity)}/10 text-${getSeverityColor(alert.severity)}`}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                </div>
                
                <div className="flex flex-col flex-1 gap-1">
                  <div className="flex justify-between items-start">
                    <p className="font-semibold text-sm">{alert.type}</p>
                    <div className="flex items-center gap-1 text-default-400 text-xs">
                      <Clock size={12} />
                      {alert.timestamp}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs font-medium text-default-500">{alert.source}</p>
                    <Chip 
                      size="sm" 
                      color={getSeverityColor(alert.severity)} 
                      variant="soft"
                      className="h-5 text-[10px]"
                    >
                      {alert.severity}
                    </Chip>
                  </div>
                  
                  <p className="text-sm text-default-600 mt-2">{alert.description}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollShadow>
      </Card.Content>
    </Card>
  );
}
