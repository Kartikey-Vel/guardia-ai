"use client";

import React, { createContext, useContext, ReactNode } from "react";
import { useRealTimeAlerts, SecurityAlert } from "./useRealTimeAlerts";

type RealTimeAlertsContextType = {
  alerts: SecurityAlert[];
  connected: boolean;
  error: string | null;
  clearAlerts: () => void;
  sendMessage: (message: any) => boolean;
};

const RealTimeAlertsContext = createContext<RealTimeAlertsContextType>({
  alerts: [],
  connected: false,
  error: null,
  clearAlerts: () => {},
  sendMessage: () => false,
});

export const useRealTimeAlertsContext = () => useContext(RealTimeAlertsContext);

export const RealTimeAlertsProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const alertsData = useRealTimeAlerts();

  return (
    <RealTimeAlertsContext.Provider value={alertsData}>
      {children}
    </RealTimeAlertsContext.Provider>
  );
};
