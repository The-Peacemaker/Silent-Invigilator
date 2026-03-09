"use client";
import React, { useState, useEffect, useRef } from "react";
import { Camera, Video, Users, User, ShieldAlert, CheckCircle, Activity, LayoutDashboard, Search, Monitor, Smartphone, Volume2, AlertTriangle, Play, Pause } from "lucide-react";

export default function DemoDashboard() {
    const [activeTab, setActiveTab] = useState("invigilator");
    const [source, setSource] = useState("webcam");
    const [logs, setLogs] = useState<{ id: number, time: string, msg: string, type: string }[]>([]);
    const videoRef = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        // Add initial log
        setLogs([{ id: Date.now(), time: new Date().toLocaleTimeString(), msg: "System Initialized. Anti-cheat active.", type: "info" }]);

        const interval = setInterval(() => {
            const messages = [
                "Head pose: Normal (Pitch: 5°, Yaw: 2°)",
                "Gaze: Centered on screen",
                "Face match: 98% Confidence",
                "Audio level: Quiet (45 dB)",
                "No multiple persons detected",
                "No mobile devices detected",
                "Browser: Fullscreen maintains active"
            ];
            const newMsg = messages[Math.floor(Math.random() * messages.length)];
            setLogs((prev) => [{ id: Date.now(), time: new Date().toLocaleTimeString(), msg: newMsg, type: "success" }, ...prev].slice(0, 50));
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        let stream: MediaStream | null = null;
        if (source === "webcam") {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then((s) => {
                    stream = s;
                    if (videoRef.current) {
                        videoRef.current.srcObject = s;
                        videoRef.current.play().catch(e => console.error(e));
                    }
                })
                .catch(err => console.error("Webcam error:", err));
        }

        return () => {
            if (stream) stream.getTracks().forEach((track) => track.stop());
        };
    }, [source, activeTab]);

    return (
        <div className="min-h-screen bg-neutral-900 text-neutral-100 font-sans flex overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 bg-neutral-950 border-r border-neutral-800 flex flex-col">
                <div className="p-6 border-b border-neutral-800">
                    <h1 className="text-xl font-bold flex items-center gap-2 text-blue-400">
                        <ShieldAlert className="w-6 h-6" /> Silent Invigilator
                    </h1>
                    <p className="text-xs text-neutral-500 mt-1">Autonomous Detection System</p>
                </div>

                <nav className="flex-1 p-4 flex flex-col gap-2">
                    <button
                        onClick={() => setActiveTab("invigilator")}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === "invigilator" ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'hover:bg-neutral-800 text-neutral-400'}`}>
                        <Video className="w-5 h-5" /> Live Monitor (Invigilator)
                    </button>

                    <button
                        onClick={() => setActiveTab("teacher")}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === "teacher" ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'hover:bg-neutral-800 text-neutral-400'}`}>
                        <Users className="w-5 h-5" /> Class Dashboard (Teacher)
                    </button>

                    <button
                        onClick={() => setActiveTab("admin")}
                        className={`flex items-center gap-3 p-3 rounded-xl transition-all ${activeTab === "admin" ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'hover:bg-neutral-800 text-neutral-400'}`}>
                        <LayoutDashboard className="w-5 h-5" /> System Overview (Admin)
                    </button>
                </nav>

                <div className="p-4 border-t border-neutral-800">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-sm text-green-500">System Online</span>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 flex flex-col h-[100vh] overflow-hidden">
                {activeTab === "invigilator" && (
                    <div className="flex-1 flex flex-col p-6 overflow-hidden">
                        <header className="flex justify-between items-center mb-6">
                            <div>
                                <h2 className="text-2xl font-bold">Candidate Exam Session</h2>
                                <p className="text-neutral-400 text-sm">Exam: Final Term Data Structures • ID: CS-2026-45</p>
                            </div>

                            <div className="flex gap-2">
                                <button
                                    onClick={() => setSource("webcam")}
                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${source === "webcam" ? "bg-blue-600 text-white" : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"}`}>
                                    Live Webcam
                                </button>
                                <button
                                    onClick={() => setSource("video")}
                                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${source === "video" ? "bg-purple-600 text-white" : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"}`}>
                                    Pre-recorded Demo
                                </button>
                            </div>
                        </header>

                        <div className="flex-1 flex gap-6 overflow-hidden">
                            {/* Video Player Area */}
                            <div className="flex-1 bg-neutral-950 border border-neutral-800 rounded-2xl relative overflow-hidden flex items-center justify-center">
                                {source === "video" ? (
                                    <video
                                        src="https://www.w3schools.com/html/mov_bbb.mp4"
                                        autoPlay
                                        loop
                                        muted
                                        className="w-full h-full object-cover opacity-80"
                                    />
                                ) : (
                                    <video
                                        ref={videoRef}
                                        autoPlay
                                        playsInline
                                        muted
                                        className="w-full h-full object-cover transform -scale-x-100 opacity-90"
                                    />
                                )}

                                {/* Fake AI Overlays */}
                                <div className="absolute inset-0 pointer-events-none">
                                    {/* Fake Face Box */}
                                    <div className="absolute top-1/4 left-[35%] w-[30%] h-[45%] border-2 border-green-500/50 rounded-lg shadow-[0_0_15px_rgba(34,197,94,0.3)] flex justify-center">
                                        <div className="absolute -top-6 text-xs bg-green-500/90 text-black font-bold px-2 py-1 rounded">Face Detected: User ID #1042</div>
                                        <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-green-500/50 rounded-full animate-ping"></div>
                                    </div>
                                    {/* Overlay text */}
                                    <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur pb-2 px-3 pt-2 rounded-lg border border-neutral-800">
                                        <p className="text-xs text-neutral-400">Analysis Model: SI-Vision-v2</p>
                                        <p className="text-sm font-mono text-green-400 animate-pulse mt-1 flex items-center gap-2"><div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div> Scanning environment...</p>
                                    </div>
                                </div>
                            </div>

                            {/* Logs area */}
                            <div className="w-80 bg-neutral-950 border border-neutral-800 rounded-2xl flex flex-col overflow-hidden hidden lg:flex">
                                <div className="p-4 border-b border-neutral-800 bg-neutral-900/50">
                                    <h3 className="font-semibold flex items-center gap-2"><Activity className="w-4 h-4 text-blue-400" /> Behavioral Log</h3>
                                </div>
                                <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                                    {logs.map((log) => (
                                        <div key={log.id} className="text-sm border-l-2 border-green-500 pl-3 py-1 bg-green-500/5 rounded-r">
                                            <span className="text-neutral-500 text-xs mr-2 block mb-1">{log.time}</span>
                                            <span className="text-neutral-200">{log.msg}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Teacher / Admin mocked views */}
                {activeTab === "teacher" && (
                    <div className="p-8 h-full overflow-auto">
                        <h2 className="text-2xl font-bold mb-6">Teacher Dashboard • Active Exams</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {[1, 2, 3, 4, 5, 6].map(i => (
                                <div key={i} className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 hover:border-blue-500/50 transition-colors cursor-pointer">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 bg-neutral-800 rounded-full flex items-center justify-center">
                                                <User className="w-5 h-5 text-neutral-400" />
                                            </div>
                                            <div>
                                                <p className="font-semibold text-sm">Student {i}02{i}</p>
                                                <p className="text-xs text-neutral-500">In Progress</p>
                                            </div>
                                        </div>
                                        {i === 3 ? (
                                            <span className="bg-red-500/20 text-red-500 text-xs px-2 py-1 rounded font-bold flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Warning</span>
                                        ) : (
                                            <span className="bg-green-500/20 text-green-500 text-xs px-2 py-1 rounded font-bold flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Clear</span>
                                        )}
                                    </div>
                                    <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-500" style={{ width: `${Math.random() * 40 + 60}%` }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === "admin" && (
                    <div className="p-8 h-full overflow-auto">
                        <h2 className="text-2xl font-bold mb-6">System Overview (Admin)</h2>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl">
                                <p className="text-neutral-400 text-sm">Active Sessions</p>
                                <p className="text-3xl font-bold text-blue-400 mt-2">1,042</p>
                            </div>
                            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl">
                                <p className="text-neutral-400 text-sm">Flagged Users</p>
                                <p className="text-3xl font-bold text-red-400 mt-2">12</p>
                            </div>
                            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl">
                                <p className="text-neutral-400 text-sm">System Load</p>
                                <p className="text-3xl font-bold text-yellow-400 mt-2">34%</p>
                            </div>
                            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded-xl">
                                <p className="text-neutral-400 text-sm">API Latency</p>
                                <p className="text-3xl font-bold text-green-400 mt-2">42ms</p>
                            </div>
                        </div>
                        <div className="bg-neutral-900 border border-neutral-800 h-64 rounded-xl flex flex-col items-center justify-center p-6 text-center">
                            <Activity className="w-10 h-10 text-neutral-600 mb-4" />
                            <h3 className="text-lg font-medium text-neutral-300">Live Metrics Stream</h3>
                            <p className="text-neutral-500 text-sm max-w-sm mt-2">Server connection optimal. AI analysis models running at 99.8% uptime.</p>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
