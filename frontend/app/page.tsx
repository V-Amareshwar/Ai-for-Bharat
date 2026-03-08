"use client";

import { useState, useRef } from "react";
import Image from "next/image";

type AppState = "idle" | "listening" | "processing" | "success" | "error";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [statusText, setStatusText] = useState("अपनी भाषा में बोलें (Speak in your language)");
  
  const [extractedData, setExtractedData] = useState<Record<string, string | null> | null>(null);
  
  // NEW: State to track if Didi is currently speaking
  const [isSpeaking, setIsSpeaking] = useState(false); 
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setAppState("processing");
        setStatusText("दीदी आपकी बात समझ रही हैं... (Didi is processing...)");

        try {
          const formData = new FormData();
          formData.append("audio_file", audioBlob, "recording.webm");
          formData.append("user_id", "9876543210");
          formData.append("language", "hi-IN");

          const response = await fetch("http://localhost:8000/api/v1/process-voice", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) throw new Error(`API error: ${response.status}`);

          const data = await response.json();
          setAppState("success");
          
          setStatusText(data.ai_response || "जवाब तैयार है! (Response ready!)");
          
          if (data.extracted_data) {
            setExtractedData(data.extracted_data);
          }
          
          if (data.audio_url) {
             const audio = new Audio(`http://localhost:8000${data.audio_url}`);
             
             // LEVEL 1 ANIMATION: Start the avatar animation
             audio.play();
             setIsSpeaking(true); 
             
             audio.onended = () => {
                // Stop the animation when Didi finishes talking
                setIsSpeaking(false);
                setAppState("idle");
                setStatusText("अपनी जानकारी दें (Provide your details)");
             };
          } else {
             setTimeout(() => {
               setAppState("idle");
               setStatusText("अपनी जानकारी दें (Provide your details)");
             }, 4000);
          }

        } catch (error) {
          console.error(error);
          setAppState("error");
          setStatusText("Error connecting to AI. Check terminal.");
          setIsSpeaking(false);
        }
      };

      mediaRecorder.start();
      setAppState("listening");
      setStatusText("दीदी सुन रही हैं... (Didi is listening...)");
    } catch (error) {
      setAppState("error");
      setStatusText("Please allow microphone access.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && appState === "listening") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const toggleRecording = () => {
    if (appState === "listening") stopRecording();
    else startRecording();
  };

  const getAvatarRingStyle = () => {
    if (isSpeaking) return "ring-8 ring-orange-400 shadow-[0_0_30px_rgba(251,146,60,0.8)] animate-pulse";
    switch (appState) {
      case "listening": return "ring-8 ring-green-400 animate-pulse shadow-green-400/50";
      case "processing": return "ring-8 ring-blue-400 animate-spin-slow shadow-blue-400/50";
      case "error": return "ring-8 ring-red-400 shadow-red-400/50";
      default: return "ring-4 ring-gray-200 shadow-lg hover:ring-green-300 transition-all";
    }
  };

  return (
    <main className="flex flex-col h-screen w-full items-center py-6 px-4 sm:py-8 sm:px-8 overflow-y-auto bg-[#f8fafc]">
      
      <div className="w-full text-center flex-shrink-0 mb-4">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-green-700 mb-2 tracking-wide">जन-सहायक</h1>
        <p className="text-base text-gray-500 font-semibold italic">
          "आवाज़ ही आपकी ताकत है | Your Voice is Your Power"
        </p>
      </div>

      <div className="flex-shrink-0 flex items-center justify-center my-4">
        <div className={`relative rounded-full bg-white p-2 transition-all duration-300 shadow-xl ${getAvatarRingStyle()}`}>
          {/* LEVEL 1 ANIMATION: The inner avatar container scales up slightly while speaking */}
          <div className={`w-24 h-24 sm:w-32 sm:h-32 bg-orange-50 rounded-full flex items-center justify-center overflow-hidden border-2 border-orange-300 relative transition-transform duration-300 ${isSpeaking ? 'scale-110' : 'scale-100'}`}>
             <Image 
                src="/didi.svg" 
                alt="Didi Avatar" 
                fill 
                className={`object-cover p-2 transition-transform duration-200 ${isSpeaking ? 'animate-bounce' : ''}`} 
             />
          </div>
        </div>
      </div>

      <div className="flex flex-col items-center flex-shrink-0 w-full mb-6">
        <div className={`text-lg sm:text-xl font-semibold mb-4 text-center px-4 transition-colors duration-300 animate-pulse ${
          appState === 'error' ? 'text-red-600' : 'text-gray-700'
        }`}>
          {statusText}
        </div>

        <button
          onClick={toggleRecording}
          disabled={appState === "processing"}
          className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full flex items-center justify-center shadow-xl transition-all duration-300 ${
            appState === "listening" 
              ? "bg-red-500 hover:bg-red-600 scale-110 animate-bounce" 
              : appState === "processing"
              ? "bg-gray-400 cursor-not-allowed scale-95"
              : "bg-green-600 hover:bg-green-700 active:scale-95"
          }`}
        >
          <div className="flex items-center justify-center">
            {appState === "listening" ? (
              <Image src="/square.svg" alt="Stop" width={32} height={32} />
            ) : appState === "processing" ? (
              <Image src="/spinner.svg" alt="Loading" width={32} height={32} className="animate-spin" />
            ) : (
              <Image src="/mic.svg" alt="Microphone" width={40} height={40} />
            )}
          </div>
        </button>
      </div>

      {extractedData && (
        <div className="w-full max-w-md bg-white rounded-2xl shadow-lg border border-gray-100 p-5 mt-2 transition-all duration-500 animate-fade-in-up">
          <h3 className="text-lg font-bold text-gray-800 border-b pb-3 mb-4 flex items-center">
            <span className="mr-2">📝</span> लाइव एप्लीकेशन (Live Form)
          </h3>
          
          {/* PHASE 2: DYNAMIC ROWS */}
          <div className="space-y-3">
            {Object.keys(extractedData).length === 0 ? (
              <div className="text-center text-gray-400 py-4 font-medium">
                Waiting for details...
              </div>
            ) : (
              Object.entries(extractedData).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center p-3 rounded-xl bg-slate-50 border border-slate-100">
                  {/* Clean up the JSON keys (e.g., "crop_type" -> "Crop type") */}
                  <span className="font-semibold text-gray-700 text-sm capitalize">
                    {key.replace(/_/g, ' ')}
                  </span>
                  
                  {value ? (
                    <div className="flex items-center text-green-700 font-bold bg-green-100 px-3 py-1.5 rounded-full text-xs sm:text-sm shadow-sm">
                      <span>{String(value)}</span>
                      <svg className="w-4 h-4 ml-1.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                      </svg>
                    </div>
                  ) : (
                    <div className="flex items-center text-amber-600 font-medium bg-amber-50 px-3 py-1.5 rounded-full text-xs sm:text-sm border border-amber-100 animate-pulse">
                      <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
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