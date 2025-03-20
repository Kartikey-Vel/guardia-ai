"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import Image from "next/image";

type Camera = {
  id: number;
  name: string;
  location: string;
  status: string;
  thumbnailUrl: string;
  lastActivity?: string;
};

export default function Cameras() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    // Mock API call to fetch cameras
    const fetchCameras = async () => {
      // In a real app, this would be an API call
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate API delay

      const mockCameras: Camera[] = [
        {
          id: 1,
          name: "Front Door",
          location: "Entrance",
          status: "online",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Front+Door",
          lastActivity: "2 minutes ago",
        },
        {
          id: 2,
          name: "Backyard",
          location: "Exterior",
          status: "online",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Backyard",
          lastActivity: "15 minutes ago",
        },
        {
          id: 3,
          name: "Garage",
          location: "Exterior",
          status: "offline",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Garage",
          lastActivity: "1 day ago",
        },
        {
          id: 4,
          name: "Living Room",
          location: "Interior",
          status: "online",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Living+Room",
          lastActivity: "Just now",
        },
        {
          id: 5,
          name: "Kitchen",
          location: "Interior",
          status: "online",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Kitchen",
          lastActivity: "5 minutes ago",
        },
        {
          id: 6,
          name: "Basement",
          location: "Interior",
          status: "online",
          thumbnailUrl: "https://placehold.co/400x300/333/FFF?text=Basement",
          lastActivity: "30 minutes ago",
        },
      ];

      setCameras(mockCameras);
      setIsLoading(false);
    };

    if (isAuthenticated) {
      fetchCameras();
    }
  }, [isAuthenticated]);

  const getStatusColor = (status: string) => {
    return status === "online" ? "bg-green-500" : "bg-red-500";
  };

  if (loading || (!isAuthenticated && loading)) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Cameras</h1>
        <button className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
          Add New Camera
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cameras.map((camera) => (
            <div
              key={camera.id}
              className="bg-white rounded-lg shadow overflow-hidden hover:shadow-md transition"
            >
              <div className="aspect-video relative">
                <Image
                  src={camera.thumbnailUrl}
                  alt={camera.name}
                  fill={true}
                  className="object-cover"
                />
              </div>
              <div className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{camera.name}</h3>
                    <p className="text-gray-500 text-sm">{camera.location}</p>
                  </div>
                  <div
                    className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
                      camera.status === "online"
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${getStatusColor(
                        camera.status
                      )}`}
                    ></span>
                    <span className="capitalize">{camera.status}</span>
                  </div>
                </div>

                <div className="mt-3 text-sm text-gray-500">
                  <p>Last activity: {camera.lastActivity}</p>
                </div>

                <div className="mt-4 flex space-x-2">
                  <button className="flex-1 bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded text-sm font-medium hover:bg-indigo-100">
                    View
                  </button>
                  <button className="flex-1 bg-gray-50 text-gray-600 px-3 py-1.5 rounded text-sm font-medium hover:bg-gray-100">
                    Settings
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
