import { useState, useRef, useCallback } from "react";
import { Api, type TranscribeResponse, type ChatResponse } from "../services/api";

type Status = "idle" | "listening" | "processing" | "playing" | "success" | "error";

export function useVoiceRecorder(sessionId: string | null, enableChat: boolean, initialLang: string = "") {
    const [status, setStatus] = useState<Status>("idle");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [result, setResult] = useState<TranscribeResponse | null>(null);
    const [chatReply, setChatReply] = useState<ChatResponse | null>(null);
    const [language, setLanguage] = useState<string>(initialLang);
    const [visualiserData, setVisualiserData] = useState<number[]>(new Array(8).fill(4));

    const mediaRecorder = useRef<MediaRecorder | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const audioChunks = useRef<Blob[]>([]);

    // Web Audio Context for App Visualiser
    const audioCtx = useRef<AudioContext | null>(null);
    const analyser = useRef<AnalyserNode | null>(null);
    const animFrameId = useRef<number | null>(null);

    // Track active AI speech playback to allow interruption
    const activeAudio = useRef<HTMLAudioElement | null>(null);

    const bestMimeType = () => {
        const types = [
            "audio/webm;codecs=opus",
            "audio/webm",
            "audio/ogg;codecs=opus",
            "audio/mp4",
        ];
        return types.find((t) => MediaRecorder.isTypeSupported(t)) || "audio/webm";
    };

    const extensionFor = (mime: string) => {
        if (mime.includes("ogg")) return "ogg";
        if (mime.includes("mp4")) return "mp4";
        return "webm";
    };

    const startVisualiser = (stream: MediaStream) => {
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        audioCtx.current = new AudioContextClass();
        analyser.current = audioCtx.current.createAnalyser();
        analyser.current.fftSize = 64;

        const source = audioCtx.current.createMediaStreamSource(stream);
        source.connect(analyser.current);

        const dataArr = new Uint8Array(analyser.current.frequencyBinCount);

        const draw = () => {
            animFrameId.current = requestAnimationFrame(draw);
            analyser.current?.getByteFrequencyData(dataArr);

            // Extract 8 specific bars for animation
            const newBars = [];
            for (let i = 0; i < 8; i++) {
                const val = dataArr[i % dataArr.length];
                const h = Math.max(4, (val / 255) * 44);
                newBars.push(h);
            }
            setVisualiserData(newBars);
        };
        draw();
    };

    const stopVisualiser = () => {
        if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
        if (audioCtx.current) {
            audioCtx.current.close();
            audioCtx.current = null;
        }
        setVisualiserData(new Array(8).fill(4));
    };

    const handleRecordingStop = async () => {
        const mime = bestMimeType();
        const ext = extensionFor(mime);
        const audioBlob = new Blob(audioChunks.current, { type: mime });
        const filename = `recording.${ext}`;

        try {
            // STEP 1: Transcribe the Audio
            const resp = await Api.transcribe(audioBlob, filename, language);
            setResult(resp);

            // We need an English text to generate an AI response.
            // If the user spoke English, use `text`. If they spoke Telugu, use `english_text` from DeepTranslator
            const textToProcess = resp.english_text || resp.text;

            if (!enableChat || !sessionId || !textToProcess) {
                setStatus("success");
                return;
            }

            // STEP 2: Send context to Bedrock RAG
            setStatus("processing");
            const chatResp = await Api.sendChatMessage(sessionId, textToProcess, resp.user_language || 'en');
            setChatReply(chatResp);

            // STEP 3: Auto-play the Audio Response buffer
            if (chatResp.audio_base64) {
                setStatus("playing");
                const audio = new Audio(`data:audio/mp3;base64,${chatResp.audio_base64}`);
                activeAudio.current = audio;

                // When Didi finishes speaking, switch status back to idle instead of auto-recording
                audio.onended = () => {
                    setStatus("idle");
                    activeAudio.current = null;
                };

                audio.play().catch(e => {
                    console.error("Auto-play prevented by browser:", e);
                    setStatus("success");
                    activeAudio.current = null;
                });
            } else {
                setStatus("success");
            }

        } catch (err: any) {
            console.error("Pipeline error:", err);
            setErrorMessage(err.message || "Could not process request — please try again");
            setStatus("error");
        }
    };

    const startRecording = async () => {
        // Interrupt any currently playing Polly Audio
        if (activeAudio.current) {
            activeAudio.current.pause();
            activeAudio.current.currentTime = 0;
            activeAudio.current = null;
        }

        setErrorMessage(null);
        setResult(null);
        setStatus("listening");

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            audioChunks.current = [];
            const mime = bestMimeType();
            mediaRecorder.current = new MediaRecorder(stream, { mimeType: mime });

            mediaRecorder.current.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) audioChunks.current.push(e.data);
            };

            mediaRecorder.current.onstop = handleRecordingStop;
            mediaRecorder.current.start(100);

            startVisualiser(stream);
        } catch (e) {
            setErrorMessage("Microphone access denied. Please allow microphone and try again.");
            setStatus("error");
        }
    };

    const stopRecording = useCallback(() => {
        if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
            mediaRecorder.current.stop();
        }
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setStatus("processing");
        stopVisualiser();
    }, []);

    const toggleRecording = useCallback(() => {
        if (status === "listening") {
            stopRecording();
        } else {
            startRecording();
        }
    }, [status, language, startRecording, stopRecording]);

    // An initial payload to get Didi to introduce herself automatically
    const autoGreet = useCallback(async () => {
        if (!enableChat || !sessionId || status !== "idle") return;

        try {
            setStatus("processing");
            // We just ping the backend with "Hello" so the LLM responds with a greeting
            const chatResp = await Api.sendChatMessage(sessionId, "Hello", language || 'en');
            setChatReply(chatResp);

            if (chatResp.audio_base64) {
                setStatus("playing");
                const audio = new Audio(`data:audio/mp3;base64,${chatResp.audio_base64}`);

                audio.onended = () => {
                    // Turn off auto-recording, just reset to idle
                    setStatus("idle");
                };

                audio.play().catch(e => {
                    console.error("Auto-play prevented by browser:", e);
                    setStatus("idle"); // If user hasn't interacted, auto-play will fail. Reset to idle.
                });
            } else {
                setStatus("idle");
            }
        } catch (err) {
            console.error("Auto-greet failed:", err);
            setStatus("idle");
        }
    }, [sessionId, enableChat, language]);

    return {
        status,
        errorMessage,
        result,
        chatReply,
        visualiserData,
        language,
        setLanguage,
        toggleRecording,
        autoGreet,
        setErrorMessage
    };
}
