"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Image from "next/image";

type AppState = "idle" | "listening" | "processing" | "speaking" | "error";

const API_BASE = "http://localhost:8000";
const AUTO_LISTEN_DELAY_MS = 1300; // wait after Didi stops before auto-recording

// ──────────────────────────────────────────────
// Stable browser-session device fingerprint
// ──────────────────────────────────────────────
function getOrCreateDeviceId(): string {
  const KEY = "jan_sahayak_device_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [statusText, setStatusText] = useState("जन-सहायक शुरू हो रही है... (Loading Didi...)");
  const [extractedData, setExtractedData] = useState<Record<string, string | null> | null>(null);
  const [changedKeys, setChangedKeys] = useState<Set<string>>(new Set());
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [micGranted, setMicGranted] = useState(false); // tracks browser permission

  const deviceIdRef = useRef("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const autoListenTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  // Greeting audio pre-fetched on mount; played on first user interaction
  const greetDataRef = useRef<{ audio_url: string; speech: string } | null>(null);
  const hasGreetedRef = useRef(false);

  // ──────────────────────────────────────────────
  // Play audio + after it ends, auto-start mic
  // ──────────────────────────────────────────────
  const playAudioAndAutoListen = useCallback((audioUrl: string, speechText: string) => {
    // Stop any currently playing audio
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current = null;
    }

    const audio = new Audio(`${API_BASE}${audioUrl}`);
    activeAudioRef.current = audio;

    setAppState("speaking");
    setIsSpeaking(true);
    setStatusText(speechText);
    audio.play().catch(console.error);

    audio.onended = () => {
      setIsSpeaking(false);
      setAppState("idle");
      setStatusText("दीदी सुन रही हैं... बोलिए! (Listening...)");
      activeAudioRef.current = null;

      // Auto-start mic after Didi finishes speaking (only if permission was granted)
      if (autoListenTimer.current) clearTimeout(autoListenTimer.current);
      autoListenTimer.current = setTimeout(() => {
        startRecording();
      }, AUTO_LISTEN_DELAY_MS);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ──────────────────────────────────────────────
  // Core recording logic
  // ──────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    // Don't start if already busy
    if (appState === "listening" || appState === "processing" || appState === "speaking") return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicGranted(true);

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setAppState("processing");
        setStatusText("दीदी आपकी बात समझ रही हैं... (Processing...)");

        try {
          const formData = new FormData();
          formData.append("audio_file", audioBlob, "recording.webm");
          formData.append("user_id", deviceIdRef.current);
          formData.append("language", "hi-IN");

          const res = await fetch(`${API_BASE}/api/v1/process-voice`, {
            method: "POST",
            body: formData,
          });
          if (!res.ok) throw new Error(`API error: ${res.status}`);

          const data = await res.json();

          // ── Phase 4: diff old vs new — flash changed fields ──
          if (data.extracted_data && Object.keys(data.extracted_data).length > 0) {
            setExtractedData((prev) => {
              const incoming: Record<string, string | null> = data.extracted_data;
              const changed = new Set<string>();
              for (const key of Object.keys(incoming)) {
                if (!prev || prev[key] !== incoming[key]) changed.add(key);
              }
              if (changed.size > 0) {
                setChangedKeys(changed);
                setTimeout(() => setChangedKeys(new Set()), 2000);
              }
              return { ...(prev ?? {}), ...incoming };
            });
          }

          // Play Didi's reply → then auto-listen
          if (data.audio_url) {
            playAudioAndAutoListen(data.audio_url, data.ai_response || "");
          } else {
            setAppState("idle");
            setStatusText(data.ai_response || "अपनी जानकारी दें | Provide your details");
          }
        } catch (err) {
          console.error(err);
          setAppState("error");
          setStatusText("Backend से कनेक्ट नहीं हो पाया। (Connection error)");
        }
      };

      mediaRecorder.start();
      setAppState("listening");
      setStatusText("दीदी सुन रही हैं... रुकने के लिए बटन दबाएं। (Tap to stop)");
    } catch {
      setAppState("error");
      setStatusText("माइक्रोफोन की अनुमति दें। (Please allow microphone access.)");
    }
  }, [appState, playAudioAndAutoListen]);

  const stopRecording = useCallback(() => {
    if (autoListenTimer.current) clearTimeout(autoListenTimer.current);
    if (mediaRecorderRef.current && appState === "listening") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
    }
  }, [appState]);

  const toggleRecording = useCallback(() => {
    if (appState === "listening") {
      stopRecording();
      return;
    }

    // ── First press: play greeting first (user gesture unlocks audio) ──
    if (!hasGreetedRef.current && greetDataRef.current) {
      hasGreetedRef.current = true;
      const { audio_url, speech } = greetDataRef.current;
      playAudioAndAutoListen(audio_url, speech);
      return; // after greeting ends, auto-mic starts
    }

    startRecording();
  }, [appState, startRecording, stopRecording, playAudioAndAutoListen]);

  // ──────────────────────────────────────────────
  // On mount: set device ID + PRE-FETCH greeting
  // (audio is NOT played here — browser blocks autoplay without user gesture)
  // ──────────────────────────────────────────────
  useEffect(() => {
    deviceIdRef.current = getOrCreateDeviceId();
    setStatusText("माइक बटन दबाकर शुरू करें | Tap mic to begin");

    // Silently pre-fetch the greet audio so it's ready instantly on first tap
    fetch(`${API_BASE}/api/v1/greet`)
      .then((r) => r.json())
      .then((data) => {
        if (data.audio_url) {
          greetDataRef.current = { audio_url: data.audio_url, speech: data.speech || "" };
        }
      })
      .catch(() => { /* silent — greeting is optional */ });
  }, []); // intentionally empty deps — run once on mount

  // ──────────────────────────────────────────────
  // Cleanup on unmount
  // ──────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (autoListenTimer.current) clearTimeout(autoListenTimer.current);
      if (activeAudioRef.current) activeAudioRef.current.pause();
    };
  }, []);

  // ──────────────────────────────────────────────
  // Avatar ring style
  // ──────────────────────────────────────────────
  const getAvatarRingStyle = () => {
    if (isSpeaking)
      return "ring-8 ring-orange-400 shadow-[0_0_30px_rgba(251,146,60,0.8)] animate-pulse";
    switch (appState) {
      case "listening":
        return "ring-8 ring-green-400 animate-pulse shadow-green-400/50";
      case "processing":
        return "ring-8 ring-blue-400 animate-spin-slow shadow-blue-400/50";
      case "error":
        return "ring-8 ring-red-400 shadow-red-400/50";
      default:
        return "ring-4 ring-gray-200 shadow-lg hover:ring-green-300 transition-all";
    }
  };

  // ──────────────────────────────────────────────
  // Field row style — flashes yellow when value changes
  // ──────────────────────────────────────────────
  const getFieldRowStyle = (key: string) => {
    const base = "flex justify-between items-center p-3 rounded-xl border transition-all duration-300";
    return changedKeys.has(key)
      ? `${base} bg-yellow-50 border-yellow-400 shadow-sm scale-[1.01]`
      : `${base} bg-slate-50 border-slate-100`;
  };

  // ──────────────────────────────────────────────
  // Mic button label
  // ──────────────────────────────────────────────
  const getMicLabel = () => {
    if (appState === "listening") return "रुकें | Stop";
    if (appState === "processing") return "...";
    if (appState === "speaking") return "सुन रहे हैं";
    return micGranted ? "बोलें | Speak" : "शुरू करें | Start";
  };

  return (
    <main className="flex flex-col h-screen w-full items-center py-6 px-4 sm:py-8 sm:px-8 overflow-y-auto bg-[#f8fafc]">

      {/* Header */}
      <div className="w-full text-center flex-shrink-0 mb-4">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-green-700 mb-2 tracking-wide">जन-सहायक</h1>
        <p className="text-base text-gray-500 font-semibold italic">
          &quot;आवाज़ ही आपकी ताकत है | Your Voice is Your Power&quot;
        </p>
      </div>

      {/* Avatar */}
      <div className="flex-shrink-0 flex items-center justify-center my-4">
        <div className={`relative rounded-full bg-white p-2 transition-all duration-300 shadow-xl ${getAvatarRingStyle()}`}>
          <div className={`w-24 h-24 sm:w-32 sm:h-32 bg-orange-50 rounded-full flex items-center justify-center overflow-hidden border-2 border-orange-300 relative transition-transform duration-300 ${isSpeaking ? "scale-110" : "scale-100"}`}>
            <Image
              src="/didi.svg"
              alt="Didi Avatar"
              fill
              className={`object-cover p-2 transition-transform duration-200 ${isSpeaking ? "animate-bounce" : ""}`}
            />
          </div>
        </div>
      </div>

      {/* Status text */}
      <div className={`text-base sm:text-lg font-semibold mb-4 text-center px-4 transition-colors duration-300 max-w-sm ${appState === "error" ? "text-red-600" : "text-gray-700"}`}>
        {statusText}
      </div>

      {/* Mic button */}
      <div className="flex flex-col items-center flex-shrink-0 w-full mb-6">
        <button
          onClick={toggleRecording}
          disabled={appState === "processing" || appState === "speaking"}
          className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex flex-col items-center justify-center shadow-xl transition-all duration-300 gap-1 ${appState === "listening"
            ? "bg-red-500 hover:bg-red-600 scale-110 animate-bounce"
            : appState === "processing" || appState === "speaking"
              ? "bg-gray-400 cursor-not-allowed scale-95 opacity-70"
              : "bg-green-600 hover:bg-green-700 active:scale-95"
            }`}
        >
          {appState === "listening" ? (
            <Image src="/square.svg" alt="Stop" width={28} height={28} />
          ) : appState === "processing" ? (
            <Image src="/spinner.svg" alt="Loading" width={28} height={28} className="animate-spin" />
          ) : (
            <Image src="/mic.svg" alt="Microphone" width={36} height={36} />
          )}
          <span className="text-white text-[9px] font-bold tracking-tight leading-none">
            {getMicLabel()}
          </span>
        </button>

        {/* Auto-listen indicator */}
        {micGranted && appState === "idle" && (
          <p className="mt-3 text-xs text-gray-400 animate-pulse">
            ● Auto-listening enabled · Press to speak anytime
          </p>
        )}
      </div>

      {/* Live Form Panel */}
      {extractedData && (
        <div className="w-full max-w-md bg-white rounded-2xl shadow-lg border border-gray-100 p-5 mt-2">
          <h3 className="text-lg font-bold text-gray-800 border-b pb-3 mb-4 flex items-center">
            <span className="mr-2">📝</span> लाइव एप्लीकेशन (Live Form)
          </h3>
          <div className="space-y-3">
            {Object.keys(extractedData).length === 0 ? (
              <div className="text-center text-gray-400 py-4 font-medium">Waiting for details...</div>
            ) : (
              Object.entries(extractedData).map(([key, value]) => (
                <div key={key} className={getFieldRowStyle(key)}>
                  <span className="font-semibold text-gray-700 text-sm capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  {value ? (
                    <div className={`flex items-center font-bold px-3 py-1.5 rounded-full text-xs sm:text-sm shadow-sm transition-all duration-300 ${changedKeys.has(key) ? "bg-yellow-100 text-yellow-800 ring-1 ring-yellow-400" : "bg-green-100 text-green-700"}`}>
                      <span>{String(value)}</span>
                      {changedKeys.has(key) ? (
                        <svg className="w-4 h-4 ml-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.5L16.732 3.732z" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 ml-1.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center text-amber-600 font-medium bg-amber-50 px-3 py-1.5 rounded-full text-xs sm:text-sm border border-amber-100 animate-pulse">
                      <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Pending...</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </main>
  );
}