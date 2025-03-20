import React, { useState } from "react";
import Image from "next/image";

const CameraOverview = () => {
  // Mock camera data - in a real app, this would come from API
  const cameras = [
    {
      id: 1,
      name: "Front Door",
      status: "online",
      thumbnailUrl: "https://placehold.co/300x200/333/FFF?text=Front+Door",
    },
    {
      id: 2,
      name: "Backyard",
      status: "online",
      thumbnailUrl: "https://placehold.co/300x200/333/FFF?text=Backyard",
    },
    {
      id: 3,
      name: "Garage",
      status: "offline",
      thumbnailUrl: "https://placehold.co/300x200/333/FFF?text=Garage",
    },
    {
      id: 4,
      name: "Living Room",
      status: "online",
      thumbnailUrl: "https://placehold.co/300x200/333/FFF?text=Living+Room",
    },
  ];

  const [selectedCamera, setSelectedCamera] = useState<number | null>(null);

  const getStatusColor = (status: string) => {
    return status === "online" ? "bg-green-500" : "bg-red-500";
  };

  return (
    <div className="bg-white rounded-lg shadow p-5">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">Cameras</h2>
        <button className="text-indigo-600 text-sm font-medium hover:text-indigo-800">
          Add Camera
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cameras.map((camera) => (
          <div
            key={camera.id}
            className={`relative overflow-hidden rounded-lg border ${
              selectedCamera === camera.id ? "ring-2 ring-indigo-500" : ""
            }`}
            onClick={() => setSelectedCamera(camera.id)}
          >
            <div className="aspect-video relative">
              <Image
                src={camera.thumbnailUrl}
                alt={camera.name}
                fill={true}
                className="object-cover"
              />
              <div className="absolute top-2 right-2 px-2 py-1 bg-black/50 text-white text-xs rounded">
                {camera.name}
              </div>
              <div
                className={`absolute bottom-2 left-2 flex items-center gap-1.5 px-2 py-1 bg-black/50 text-white text-xs rounded`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${getStatusColor(
                    camera.status
                  )}`}
                ></span>
                <span className="capitalize">{camera.status}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex justify-center">
        <button className="text-indigo-600 border border-indigo-600 px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-50 transition">
          View All Cameras
        </button>
      </div>
    </div>
  );
};

export default CameraOverview;
