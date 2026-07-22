// import React, { useEffect, useMemo, useRef, useState } from "react";
// import { motion, AnimatePresence } from "framer-motion";
// // import { Activity, Brain, CheckCircle2, CloudUpload, Headphones, Loader2, Mic, PauseCircle, Play, RotateCcw, ShieldCheck, Sparkles, Upload, Waveform, XCircle } from "lucide-react";

// import {
//   Activity,
//   AlertTriangle,
//   AudioLines as Waveform,
//   Brain,
//   CalendarClock,
//   CheckCircle2,
//   ChevronDown,
//   CloudUpload,
//   Headphones,
//   History,
//   Loader2,
//   Mic,
//   PauseCircle,
//   Play,
//   RotateCcw,
//   ShieldCheck,
//   Sparkles,
//   TrendingDown,
//   TrendingUp,
//   Upload,
//   XCircle,
// } from "lucide-react";

// const API_BASE = "http://localhost:8000";
// const AMBIENT_RECORD_SECONDS = 8;
// const VOICE_RECORD_SECONDS = 30;

// const STEPS = [
//   { id: "welcome", label: "Welcome" },
//   { id: "intro", label: "Agent Intro" },
//   { id: "ambient", label: "Ambient Check" },
//   { id: "pre", label: "Pre Voice" },
//   { id: "vr", label: "VR Session" },
//   { id: "post", label: "Post Voice" },
//   { id: "processing", label: "Processing" },
//   { id: "report", label: "Report" },
// ];

// const AGENT_LINES = {
//   intro:
//     "Hi there, I’m Cognify, your AI cognitive state assessment companion. I’ll guide you through a short stress and cognitive energy check before and after your VR meditation session. First, I’ll check whether your environment is suitable for voice recording. Then, I’ll analyse your pre-session voice, guide you through the meditation flow, and compare your post-session voice to evaluate whether your cognitive stress state has changed. This system is designed for research-based wellness support, not medical diagnosis. Let’s begin when you’re ready.",
//   ambient:
//     "Before we begin, I need to check your surroundings. Please stay silent for a few seconds while I listen to the environment.",
//   pre:
//     "Now I’d like to understand your current mental state. Tell me honestly, how has your day been so far? Were there any deadlines, pressure, or tasks that stayed on your mind?",
//   vr:
//     "Your pre-session check is complete. Now begin the VR meditation session. Focus on your breathing and allow your mind to slow down.",
//   post:
//     "Welcome back. Take a moment and tell me how you feel now compared to before the session. Do your thoughts feel lighter, calmer, or still active?",
//   processing:
//     "Thank you. I’ll now analyse your pre-session and post-session voice patterns, compare cognitive stress change, validate the baseline with HRV data, and check whether this session follows an expected stress-reduction pattern.",
// };

// function classNames(...items) {
//   return items.filter(Boolean).join(" ");
// }

// function clamp(n, min, max) {
//   return Math.max(min, Math.min(max, n));
// }

// function getFemaleVoice() {
//   if (!("speechSynthesis" in window)) return null;

//   const voices = window.speechSynthesis.getVoices();
//   const preferredNames = [
//     "Microsoft Zira",
//     "Microsoft Sonia",
//     "Google UK English Female",
//     "Google US English",
//     "Samantha",
//     "Karen",
//     "Moira",
//   ];

//   for (const name of preferredNames) {
//     const found = voices.find((v) => v.name.toLowerCase().includes(name.toLowerCase()));
//     if (found) return found;
//   }

//   return voices.find((v) => v.lang.toLowerCase().startsWith("en")) || voices[0] || null;
// }

// function speak(text, onDone) {
//   if (!("speechSynthesis" in window)) {
//     onDone?.();
//     return;
//   }

//   window.speechSynthesis.cancel();
//   const utterance = new SpeechSynthesisUtterance(text);
//   utterance.rate = 0.9;
//   utterance.pitch = 1.05;
//   utterance.volume = 0.95;

//   const femaleVoice = getFemaleVoice();
//   if (femaleVoice) utterance.voice = femaleVoice;

//   utterance.onend = () => onDone?.();
//   utterance.onerror = () => onDone?.();
//   window.speechSynthesis.speak(utterance);
// }

// async function postForm(endpoint, fields = {}, files = {}) {
//   const form = new FormData();
//   Object.entries(fields).forEach(([k, v]) => form.append(k, v));
//   Object.entries(files).forEach(([k, v]) => form.append(k, v));
//   const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
//   if (!res.ok) {
//     let msg = `HTTP ${res.status}`;
//     try {
//       const data = await res.json();
//       msg = data.detail || msg;
//     } catch {}
//     throw new Error(msg);
//   }
//   return res.json();
// }

// async function postJson(endpoint, body) {
//   const res = await fetch(`${API_BASE}${endpoint}`, {
//     method: "POST",
//     headers: { "Content-Type": "application/json" },
//     body: JSON.stringify(body),
//   });
//   if (!res.ok) {
//     let msg = `HTTP ${res.status}`;
//     try {
//       const data = await res.json();
//       msg = data.detail || msg;
//     } catch {}
//     throw new Error(msg);
//   }
//   return res.json();
// }

// function encodeWav(float32Samples, sampleRate) {
//   const numChannels = 1;
//   const bytesPerSample = 2;
//   const blockAlign = numChannels * bytesPerSample;
//   const buffer = new ArrayBuffer(44 + float32Samples.length * bytesPerSample);
//   const view = new DataView(buffer);

//   const writeString = (offset, str) => {
//     for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
//   };

//   writeString(0, "RIFF");
//   view.setUint32(4, 36 + float32Samples.length * bytesPerSample, true);
//   writeString(8, "WAVE");
//   writeString(12, "fmt ");
//   view.setUint32(16, 16, true);
//   view.setUint16(20, 1, true);
//   view.setUint16(22, numChannels, true);
//   view.setUint32(24, sampleRate, true);
//   view.setUint32(28, sampleRate * blockAlign, true);
//   view.setUint16(32, blockAlign, true);
//   view.setUint16(34, 16, true);
//   writeString(36, "data");
//   view.setUint32(40, float32Samples.length * bytesPerSample, true);

//   let offset = 44;
//   for (let i = 0; i < float32Samples.length; i++, offset += 2) {
//     const s = Math.max(-1, Math.min(1, float32Samples[i]));
//     view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
//   }

//   return new Blob([view], { type: "audio/wav" });
// }

// function mergeFloat32(chunks) {
//   const length = chunks.reduce((sum, arr) => sum + arr.length, 0);
//   const result = new Float32Array(length);
//   let offset = 0;
//   chunks.forEach((arr) => {
//     result.set(arr, offset);
//     offset += arr.length;
//   });
//   return result;
// }

// function blobToFile(blob, name) {
//   return new File([blob], name, { type: blob.type || "audio/wav" });
// }

// function useAudioRecorder() {
//   const [isRecording, setIsRecording] = useState(false);
//   const [elapsed, setElapsed] = useState(0);
//   const [audioBlob, setAudioBlob] = useState(null);
//   const [levels, setLevels] = useState(Array.from({ length: 48 }, () => 0.08));
//   const [error, setError] = useState("");

//   const streamRef = useRef(null);
//   const audioContextRef = useRef(null);
//   const analyserRef = useRef(null);
//   const sourceRef = useRef(null);
//   const processorRef = useRef(null);
//   const chunksRef = useRef([]);
//   const timerRef = useRef(null);
//   const rafRef = useRef(null);
//   const stopTimeoutRef = useRef(null);

//   const cleanup = async () => {
//     if (rafRef.current) cancelAnimationFrame(rafRef.current);
//     rafRef.current = null;
//     clearInterval(timerRef.current);
//     clearTimeout(stopTimeoutRef.current);
//     timerRef.current = null;
//     stopTimeoutRef.current = null;

//     try {
//       if (processorRef.current) processorRef.current.disconnect();
//       if (sourceRef.current) sourceRef.current.disconnect();
//       if (analyserRef.current) analyserRef.current.disconnect();
//     } catch {}

//     processorRef.current = null;
//     sourceRef.current = null;
//     analyserRef.current = null;

//     if (streamRef.current) {
//       streamRef.current.getTracks().forEach((t) => t.stop());
//       streamRef.current = null;
//     }

//     if (audioContextRef.current && audioContextRef.current.state !== "closed") {
//       try {
//         await audioContextRef.current.close();
//       } catch {}
//     }
//     audioContextRef.current = null;
//   };

//   const stop = async () => {
//     if (!isRecording && chunksRef.current.length === 0) return;
//     const ctx = audioContextRef.current;
//     const sampleRate = ctx?.sampleRate || 44100;
//     const samples = mergeFloat32(chunksRef.current);
//     const wav = encodeWav(samples, sampleRate);
//     setAudioBlob(wav);
//     setIsRecording(false);
//     await cleanup();
//   };

//   const start = async ({ autoStopSeconds = null } = {}) => {
//     setError("");
//     setAudioBlob(null);
//     setElapsed(0);
//     chunksRef.current = [];

//     try {
//       const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//       streamRef.current = stream;

//       const AudioContextClass = window.AudioContext || window.webkitAudioContext;
//       const ctx = new AudioContextClass();
//       audioContextRef.current = ctx;

//       const source = ctx.createMediaStreamSource(stream);
//       const analyser = ctx.createAnalyser();
//       analyser.fftSize = 256;
//       const processor = ctx.createScriptProcessor(4096, 1, 1);

//       source.connect(analyser);
//       analyser.connect(processor);
//       processor.connect(ctx.destination);

//       processor.onaudioprocess = (event) => {
//         const input = event.inputBuffer.getChannelData(0);
//         chunksRef.current.push(new Float32Array(input));
//       };

//       sourceRef.current = source;
//       analyserRef.current = analyser;
//       processorRef.current = processor;

//       const data = new Uint8Array(analyser.frequencyBinCount);
//       const draw = () => {
//         analyser.getByteFrequencyData(data);
//         const bucketCount = 48;
//         const bucketSize = Math.max(1, Math.floor(data.length / bucketCount));
//         const next = Array.from({ length: bucketCount }, (_, i) => {
//           const startIndex = i * bucketSize;
//           const slice = data.slice(startIndex, startIndex + bucketSize);
//           const avg = slice.reduce((a, b) => a + b, 0) / Math.max(1, slice.length);
//           return clamp(avg / 255, 0.06, 1);
//         });
//         setLevels(next);
//         rafRef.current = requestAnimationFrame(draw);
//       };
//       draw();

//       setIsRecording(true);
//       timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
//       if (autoStopSeconds) stopTimeoutRef.current = setTimeout(() => stop(), autoStopSeconds * 1000);
//     } catch (err) {
//       setError(err.message || "Microphone access failed");
//       setIsRecording(false);
//       await cleanup();
//     }
//   };

//   useEffect(() => {
//     return () => cleanup();
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, []);

//   return { isRecording, elapsed, audioBlob, levels, error, start, stop, setAudioBlob };
// }

// function Shell({ children, step, setStep }) {
//   const index = STEPS.findIndex((s) => s.id === step);
//   return (
//     <div className="min-h-screen bg-[#07111f] text-white overflow-hidden">
//       <div className="fixed inset-0 pointer-events-none">
//         <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-cyan-500/20 blur-3xl" />
//         <div className="absolute top-1/3 -right-40 h-[32rem] w-[32rem] rounded-full bg-indigo-600/20 blur-3xl" />
//         <div className="absolute bottom-0 left-1/4 h-80 w-80 rounded-full bg-emerald-400/10 blur-3xl" />
//       </div>
//       <header className="relative z-10 border-b border-white/10 bg-white/[0.03] backdrop-blur-xl">
//         <div className="mx-auto max-w-7xl px-5 py-4 flex items-center justify-between">
//           <div className="flex items-center gap-3">
//             <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-cyan-300 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
//               <Brain className="h-6 w-6 text-white" />
//             </div>
//             <div>
//               <div className="font-bold tracking-wide text-lg">Cognify</div>
//               <div className="text-xs text-cyan-100/70">Cognitive Stress & Energy Assessment</div>
//             </div>
//           </div>
//           <div className="hidden md:flex items-center gap-2 text-xs text-white/60">
//             {STEPS.map((s, i) => (
//               <button
//                 key={s.id}
//                 onClick={() => setStep(s.id)}
//                 className={classNames(
//                   "px-3 py-2 rounded-full border transition",
//                   i <= index ? "border-cyan-300/50 bg-cyan-300/10 text-cyan-100" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"
//                 )}
//               >
//                 {i + 1}. {s.label}
//               </button>
//             ))}
//           </div>
//         </div>
//       </header>
//       <main className="relative z-10 mx-auto max-w-7xl px-5 py-8">{children}</main>
//     </div>
//   );
// }

// function AgentCard({ title, text, onSpeak }) {
//   const [visibleChars, setVisibleChars] = useState(0);
//   const [speaking, setSpeaking] = useState(false);
//   const typeTimerRef = useRef(null);

//   const shownText = text.slice(0, Math.max(visibleChars, 1));

//   const stopTyping = () => {
//     if (typeTimerRef.current) {
//       clearInterval(typeTimerRef.current);
//       typeTimerRef.current = null;
//     }
//   };

//   const startTyping = () => {
//     stopTyping();
//     setVisibleChars(0);
//     typeTimerRef.current = setInterval(() => {
//       setVisibleChars((current) => {
//         if (current >= text.length) {
//           stopTyping();
//           return text.length;
//         }
//         return current + 2;
//       });
//     }, 25);
//   };

//   const play = () => {
//     startTyping();
//     setSpeaking(true);
//     speak(text, () => {
//       setVisibleChars(text.length);
//       setSpeaking(false);
//       stopTyping();
//     });
//   };

//   useEffect(() => {
//     startTyping();
//     return () => stopTyping();
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, [text]);

//   return (
//     <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
//       <div className="flex items-start gap-4">
//         <motion.div
//           animate={speaking ? { scale: [1, 1.08, 1], boxShadow: ["0 0 0 rgba(34,211,238,0)", "0 0 32px rgba(34,211,238,.35)", "0 0 0 rgba(34,211,238,0)"] } : { scale: [1, 1.04, 1], rotate: [0, 2, -2, 0] }}
//           transition={{ duration: speaking ? 1.4 : 4, repeat: Infinity }}
//           className="h-16 w-16 rounded-3xl bg-gradient-to-br from-cyan-300 via-blue-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-cyan-500/20"
//         >
//           <Sparkles className="h-8 w-8" />
//         </motion.div>
//         <div className="flex-1">
//           <div className="mb-2 flex items-center gap-3">
//             <h2 className="text-xl font-semibold">{title}</h2>
//             {speaking && <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs text-cyan-100">speaking...</span>}
//           </div>
//           <div className="relative inline-block max-w-5xl rounded-3xl rounded-tl-md bg-slate-950/35 px-5 py-4 text-white/80 leading-8 border border-white/10">
//             {shownText}
//             {visibleChars < text.length && <span className="ml-1 animate-pulse text-cyan-200">▌</span>}
//           </div>
//           <div>
//             <button onClick={play} className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-white/10 px-4 py-2 text-sm hover:bg-white/15 transition">
//               <Headphones className="h-4 w-4" /> Play Agent Voice
//             </button>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }

// function Visualizer({ levels, active = false }) {
//   return (
//     <div className="relative rounded-[2rem] border border-cyan-300/20 bg-black/20 p-6 overflow-hidden">
//       <div className="absolute inset-0 bg-gradient-to-br from-cyan-300/10 via-transparent to-indigo-500/10" />
//       <div className="relative flex h-44 items-center justify-center gap-1.5">
//         {levels.map((l, i) => (
//           <motion.div
//             key={i}
//             animate={{ height: `${12 + l * 128}px`, opacity: active ? 1 : 0.35 }}
//             transition={{ type: "spring", stiffness: 220, damping: 24 }}
//             className="w-2 rounded-full bg-gradient-to-t from-cyan-400 to-white"
//           />
//         ))}
//       </div>
//       <div className="relative text-center text-sm text-cyan-100/70">{active ? "Live frequency visualizer — recording WAV audio" : "Visualizer ready"}</div>
//     </div>
//   );
// }

// function AudioInputPanel({ title, purpose, duration, uploadLabel, onAnalyze, result, loading }) {
//   const recorder = useAudioRecorder();
//   const [mode, setMode] = useState("record");
//   const [file, setFile] = useState(null);
//   const [localError, setLocalError] = useState("");

//   const selectedFile = useMemo(() => {
//     if (mode === "upload") return file;
//     if (recorder.audioBlob) return blobToFile(recorder.audioBlob, `${purpose}_${Date.now()}.wav`);
//     return null;
//   }, [mode, file, recorder.audioBlob, purpose]);

//   const handleAnalyze = async () => {
//     setLocalError("");
//     if (!selectedFile) {
//       setLocalError("Please record live audio or upload an audio file first.");
//       return;
//     }
//     await onAnalyze(selectedFile);
//   };

//   return (
//     <div className="grid lg:grid-cols-[1.1fr_.9fr] gap-6">
//       <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl">
//         <div className="flex items-center justify-between gap-3 mb-5">
//           <div>
//             <h3 className="text-2xl font-bold">{title}</h3>
//             <p className="text-white/60 mt-1">Choose live recording or upload a prepared file.</p>
//           </div>
//           <Waveform className="h-7 w-7 text-cyan-200" />
//         </div>

//         <div className="grid grid-cols-2 gap-3 mb-5">
//           <button onClick={() => setMode("record")} className={classNames("rounded-2xl px-4 py-3 border transition", mode === "record" ? "border-cyan-300 bg-cyan-300/15" : "border-white/10 bg-white/[0.04] hover:bg-white/[0.08]")}> <Mic className="inline h-4 w-4 mr-2" /> Record Live </button>
//           <button onClick={() => setMode("upload")} className={classNames("rounded-2xl px-4 py-3 border transition", mode === "upload" ? "border-cyan-300 bg-cyan-300/15" : "border-white/10 bg-white/[0.04] hover:bg-white/[0.08]")}> <Upload className="inline h-4 w-4 mr-2" /> Upload File </button>
//         </div>

//         <AnimatePresence mode="wait">
//           {mode === "record" ? (
//             <motion.div key="record" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
//               <Visualizer levels={recorder.levels} active={recorder.isRecording} />
//               <div className="mt-5 flex flex-wrap items-center gap-3">
//                 {!recorder.isRecording ? (
//                   <button onClick={() => recorder.start({ autoStopSeconds: duration })} className="rounded-2xl bg-cyan-300 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-200 transition inline-flex items-center gap-2"><Play className="h-4 w-4" /> Start {duration}s Recording</button>
//                 ) : (
//                   <button onClick={recorder.stop} className="rounded-2xl bg-rose-400 px-5 py-3 font-semibold text-white hover:bg-rose-300 transition inline-flex items-center gap-2"><PauseCircle className="h-4 w-4" /> Stop</button>
//                 )}
//                 <div className="rounded-2xl border border-white/10 px-4 py-3 text-white/70">Timer: {recorder.elapsed}s / {duration}s</div>
//                 {recorder.audioBlob && <div className="rounded-2xl bg-emerald-400/10 px-4 py-3 text-emerald-100 border border-emerald-300/20">Recording ready as WAV</div>}
//               </div>
//               {recorder.error && <p className="mt-3 text-sm text-rose-200">{recorder.error}</p>}
//             </motion.div>
//           ) : (
//             <motion.div key="upload" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
//               <label className="flex flex-col items-center justify-center rounded-[2rem] border border-dashed border-cyan-300/30 bg-black/20 p-10 cursor-pointer hover:bg-white/[0.05] transition">
//                 <CloudUpload className="h-12 w-12 text-cyan-200 mb-3" />
//                 <span className="font-semibold">{uploadLabel}</span>
//                 <span className="text-sm text-white/50 mt-1">WAV, WebM, MP3, FLAC supported by backend</span>
//                 <input type="file" accept="audio/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
//               </label>
//               {file && <p className="mt-3 text-sm text-cyan-100">Selected: {file.name}</p>}
//             </motion.div>
//           )}
//         </AnimatePresence>

//         {(localError || loading) && <p className={classNames("mt-4 text-sm", localError ? "text-rose-200" : "text-cyan-100")}>{localError || "Processing audio through backend..."}</p>}

//         <button onClick={handleAnalyze} disabled={loading} className="mt-5 w-full rounded-2xl bg-gradient-to-r from-cyan-300 to-indigo-400 px-5 py-4 font-bold text-slate-950 hover:opacity-90 disabled:opacity-60 transition inline-flex items-center justify-center gap-2">
//           {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Activity className="h-5 w-5" />} Analyze Audio
//         </button>
//       </div>

//       <ResultCard result={result} purpose={purpose} />
//     </div>
//   );
// }

// function AmbientQualityBar({ score }) {
//   const value = typeof score === "number" ? Math.max(0, Math.min(100, score)) : 0;
//   const good = value >= 70;
//   const medium = value >= 45 && value < 70;
//   return (
//     <div className="rounded-2xl bg-black/20 p-4">
//       <div className="mb-2 flex items-center justify-between text-sm">
//         <span className="text-white/55">Ambient Quality Score</span>
//         <span className={classNames("font-bold", good ? "text-emerald-100" : medium ? "text-amber-100" : "text-rose-100")}>{value}/100</span>
//       </div>
//       <div className="h-3 overflow-hidden rounded-full bg-white/10">
//         <div
//           className={classNames("h-full rounded-full transition-all", good ? "bg-emerald-300" : medium ? "bg-amber-300" : "bg-rose-300")}
//           style={{ width: `${value}%` }}
//         />
//       </div>
//       <p className="mt-2 text-xs text-white/45">Higher score means cleaner background audio for voice stress assessment.</p>
//     </div>
//   );
// }

// function AmbientIssues({ issues }) {
//   if (!issues || issues.length === 0) return null;
//   return (
//     <div className="rounded-2xl border border-rose-300/20 bg-rose-400/10 p-4">
//       <div className="mb-2 flex items-center gap-2 font-semibold text-rose-100">
//         <AlertTriangle className="h-4 w-4" /> Detected Issues
//       </div>
//       <ul className="list-disc space-y-1 pl-5 text-sm text-rose-100/80">
//         {issues.map((issue, index) => (
//           <li key={index}>{issue}</li>
//         ))}
//       </ul>
//     </div>
//   );
// }

// function ClassificationReasons({ reasons }) {
//   if (!reasons || reasons.length === 0) return null;

//   return (
//     <div className="rounded-2xl border border-cyan-300/20 bg-cyan-400/10 p-4">
//       <div className="mb-2 flex items-center gap-2 font-semibold text-cyan-100">
//         <Brain className="h-4 w-4" /> Why this classification?
//       </div>
//       <ul className="list-disc space-y-1 pl-5 text-sm text-cyan-100/80">
//         {reasons.map((reason, index) => (
//           <li key={index}>{reason}</li>
//         ))}
//       </ul>
//     </div>
//   );
// }

// function StressClassBadge({ result }) {
//   const label = result.stress_class_label || result.stress_label || "Unknown";
//   const stressClass = result.stress_class || result.stress_level || "";

//   const isStressed =
//     stressClass === "stressed" ||
//     stressClass === "borderline_stressed" ||
//     label.toLowerCase().includes("stress");

//   const isBaseline =
//     stressClass === "baseline" ||
//     label.toLowerCase().includes("baseline");

//   const className = isStressed
//     ? "bg-rose-400/10 border-rose-300/30 text-rose-100"
//     : isBaseline
//       ? "bg-amber-400/10 border-amber-300/30 text-amber-100"
//       : "bg-emerald-400/10 border-emerald-300/30 text-emerald-100";

//   return (
//     <div className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 ${className}`}>
//       {isStressed ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
//       {label}
//     </div>
//   );
// }

// function ResultCard({ result, purpose }) {
//   return (
//     <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl min-h-[28rem]">
//       <h3 className="text-xl font-bold mb-4">{purpose === "ambient" ? "Ambient Result" : "Voice Analysis Result"}</h3>
//       {!result ? (
//         <div className="h-full flex flex-col items-center justify-center text-center text-white/50">
//           <ShieldCheck className="h-12 w-12 mb-3 text-cyan-200/60" />
//           Result will appear here after analysis.
//         </div>
//       ) : purpose === "ambient" ? (
//         <div className="space-y-4">
//           <StatusPill good={result.suitable} label={result.suitable ? "Suitable for Recording" : "Not Suitable — Retest Needed"} />
//           <AmbientQualityBar score={result.quality_score} />
//           <Metric label="Noise Level" value={result.noise_level ?? "N/A"} />
//           <Metric label="Duration" value={result.duration_sec ? `${result.duration_sec}s` : "N/A"} />
//           <Metric label="RMS Energy" value={result.rms ?? "N/A"} />
//           {/* <Metric label="RMS P95" value={result.rms_p95 ?? "N/A"} /> */}
//           <Metric label="Peak Noise" value={result.peak ?? "N/A"} />
//           <Metric label="ZCR" value={result.zcr ?? "N/A"} />
//           {/* <Metric label="Spectral Flatness" value={result.spectral_flatness ?? "N/A"} /> */}
//           <AmbientIssues issues={result.issues} />
//           <p className={classNames("rounded-2xl p-4 leading-6", result.suitable ? "bg-emerald-400/10 text-emerald-100/85 border border-emerald-300/20" : "bg-rose-400/10 text-rose-100/85 border border-rose-300/20")}>{result.recording_recommendation || result.message}</p>
//         </div>
//       ) : (
//         <div className="space-y-4">
//           <div className="rounded-[2rem] bg-black/20 p-5 text-center">
//             <div className="text-sm text-white/50">Cognitive Stress Score</div>
//             <div className="text-5xl font-black mt-2">
//               {result.score}
//               <span className="text-xl text-white/50">/10</span>
//             </div>

//             <div className="mt-4 flex justify-center">
//               <StressClassBadge result={result} />
//             </div>

//             {result.raw_score !== undefined && (
//               <div className="mt-2 text-xs text-white/40">
//                 Raw score: {result.raw_score}/10
//               </div>
//             )}
//           </div>

//           <Metric label="Stress Class" value={result.stress_class_label || result.stress_label || "N/A"} />
//           <Metric label="Classification" value={result.label_name || "N/A"} />
//           <Metric label="Confidence" value={result.classification_confidence || "N/A"} />
//           {/* <Metric label="Classification Probability" value={result.classification_probability ?? result.probability ?? "N/A"} /> */}
//           {/* <Metric label="Detected Emotion" value={result.top_emotion || "Not returned"} />
//           <Metric label="Emotion Score" value={result.top_emotion_score ?? "N/A"} />
//           <Metric label="Scoring Method" value={result.scoring_method || "single"} /> */}

//           {/* {result.stressed_chunk_ratio !== undefined && (
//             // <Metric label="Stressed Chunk Ratio" value={result.stressed_chunk_ratio} />
//           )} */}

//           {/* {result.num_chunks !== undefined && (
//             <Metric label="Valid Chunks" value={result.num_chunks} />
//           )} */}

//           <ClassificationReasons reasons={result.classification_reasons} />

//           <p className="rounded-2xl bg-black/20 p-4 text-white/70 leading-6">
//             {result.classification_description || result.stress_description}
//           </p>
//         </div>
//       )}
//     </div>
//   );
// }

// function StatusPill({ good, label }) {
//   return <div className={classNames("inline-flex items-center gap-2 rounded-full px-4 py-2 border", good ? "bg-emerald-400/10 border-emerald-300/30 text-emerald-100" : "bg-rose-400/10 border-rose-300/30 text-rose-100")}>{good ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />} {label}</div>;
// }

// function Metric({ label, value }) {
//   return <div className="flex items-center justify-between rounded-2xl bg-black/20 px-4 py-3"><span className="text-white/50">{label}</span><span className="font-semibold text-right max-w-[60%] truncate">{String(value)}</span></div>;
// }

// function Welcome({ setStep }) {
//   return (
//     <div className="grid lg:grid-cols-[1fr_.9fr] gap-8 items-center py-8">
//       <div>
//         <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-cyan-100 mb-6"><Sparkles className="h-4 w-4" /> Research demo interface</div>
//         <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-tight">Cognify</h1>
//         <p className="mt-5 text-2xl text-white/75 max-w-2xl">Cognitive Stress & Energy Assessment for Adaptive VR Meditation</p>
//         <p className="mt-5 text-white/55 leading-7 max-w-2xl">A voice-based AI companion that checks environment quality, estimates cognitive stress from speech, compares pre/post meditation changes, validates with HRV baseline data, and flags unusual session patterns.</p>
//         <button onClick={() => setStep("intro")} className="mt-8 rounded-2xl bg-cyan-300 px-7 py-4 font-bold text-slate-950 hover:bg-cyan-200 transition inline-flex items-center gap-2"><Play className="h-5 w-5" /> Start Assessment</button>
//       </div>
//       <motion.div animate={{ y: [0, -12, 0] }} transition={{ duration: 5, repeat: Infinity }} className="rounded-[3rem] border border-white/10 bg-white/[0.06] p-8 shadow-2xl backdrop-blur-xl">
//         <div className="aspect-square rounded-[2.5rem] bg-gradient-to-br from-cyan-300/20 via-indigo-500/20 to-emerald-300/10 border border-white/10 flex items-center justify-center relative overflow-hidden">
//           <motion.div animate={{ scale: [1, 1.18, 1], opacity: [0.55, 0.85, 0.55] }} transition={{ duration: 3, repeat: Infinity }} className="absolute h-72 w-72 rounded-full border border-cyan-300/30" />
//           <motion.div animate={{ scale: [1.1, 1.35, 1.1], opacity: [0.25, 0.5, 0.25] }} transition={{ duration: 4, repeat: Infinity }} className="absolute h-96 w-96 rounded-full border border-indigo-300/20" />
//           <Brain className="h-32 w-32 text-cyan-100 drop-shadow-2xl" />
//         </div>
//       </motion.div>
//     </div>
//   );
// }

// function Intro({ setStep }) {
//   return (
//     <div className="space-y-6">
//       <AgentCard title="Cognify AI Companion" text={AGENT_LINES.intro} onSpeak={speak} />
//       <div className="grid md:grid-cols-5 gap-4">
//         {["Environment", "Pre Voice", "VR Session", "Post Voice", "Validation"].map((x, i) => <div key={x} className="rounded-3xl border border-white/10 bg-white/[0.05] p-5"><div className="text-cyan-100 text-2xl font-black">0{i + 1}</div><div className="mt-2 text-white/75">{x}</div></div>)}
//       </div>
//       <button onClick={() => setStep("ambient")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">Continue to Ambient Check</button>
//     </div>
//   );
// }

// function VRTimer({ setStep }) {
//   const [time, setTime] = useState(60);
//   const [running, setRunning] = useState(false);
//   useEffect(() => {
//     if (!running || time <= 0) return;
//     const t = setTimeout(() => setTime((x) => x - 1), 1000);
//     return () => clearTimeout(t);
//   }, [running, time]);
//   useEffect(() => { speak(AGENT_LINES.vr); }, []);
//   return (
//     <div className="grid lg:grid-cols-[.9fr_1.1fr] gap-6 items-stretch">
//       <AgentCard title="VR Meditation Placeholder" text={AGENT_LINES.vr} onSpeak={speak} />
//       <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-8 text-center backdrop-blur-xl">
//         <motion.div animate={{ scale: [1, 1.04, 1] }} transition={{ duration: 3, repeat: Infinity }} className="mx-auto h-64 w-64 rounded-full border border-cyan-300/30 bg-cyan-300/10 flex items-center justify-center">
//           <div>
//             <div className="text-7xl font-black">{time}</div>
//             <div className="text-white/50">seconds</div>
//           </div>
//         </motion.div>
//         <div className="mt-8 flex justify-center gap-3">
//           <button onClick={() => setRunning((r) => !r)} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">{running ? "Pause" : "Start"}</button>
//           <button onClick={() => setTime(60)} className="rounded-2xl bg-white/10 px-6 py-3 font-bold"><RotateCcw className="inline h-4 w-4 mr-2" /> Reset</button>
//           <button onClick={() => setStep("post")} className="rounded-2xl bg-indigo-400 px-6 py-3 font-bold text-white">Continue</button>
//         </div>
//       </div>
//     </div>
//   );
// }

// function Processing({ state, setState, setStep }) {
//   const [items, setItems] = useState([]);
//   const [error, setError] = useState("");

//   const run = async () => {
//     setError("");
//     const steps = [];
//     const add = (label) => { steps.push(label); setItems([...steps]); };
//     try {
//       add("Comparing pre-session and post-session voice scores");
//       const comparison = await postJson("/compare", { pre_score: state.preResult.score, post_score: state.postResult.score });
//       add("Validating voice baseline with HRV data");
//       const hrvPre = clamp(state.preResult.score + 0.4, 0, 10);
//       const cross = await postJson("/cross-validate", { voice_pre: state.preResult.score, hrv_pre: hrvPre });
//       add("Checking session anomaly pattern");
//       const anomaly = await postJson("/anomaly-check", {
//         pre_acoustic: state.preResult.score,
//         post_acoustic: state.postResult.score,
//         pre_hrv: hrvPre,
//         crossmodal_agreement: cross.agreement,
//       });
//       setState((s) => ({ ...s, comparison, cross, anomaly, hrvPre }));
//       add("Final report ready");
//       setTimeout(() => setStep("report"), 600);
//     } catch (e) {
//       setError(e.message);
//     }
//   };

//   useEffect(() => { speak(AGENT_LINES.processing); }, []);

//   return (
//     <div className="space-y-6">
//       <AgentCard title="Processing Pipeline" text={AGENT_LINES.processing} onSpeak={speak} />
//       <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl">
//         <button onClick={run} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 inline-flex items-center gap-2"><Activity className="h-5 w-5" /> Run Validation Pipeline</button>
//         <div className="mt-6 space-y-3">
//           {items.map((it) => <div key={it} className="rounded-2xl bg-emerald-400/10 border border-emerald-300/20 px-4 py-3 text-emerald-100"><CheckCircle2 className="inline h-4 w-4 mr-2" /> {it}</div>)}
//         </div>
//         {error && <p className="mt-4 text-rose-200">{error}</p>}
//       </div>
//     </div>
//   );
// }

// function Report({ state, setStep }) {
//   const improved = state.comparison?.outcome === "reduced";
//   const increased = state.comparison?.outcome === "increased";
//   const message = improved
//     ? "Your stress score decreased after the session. This suggests that the meditation session had a positive effect on your cognitive stress state."
//     : increased
//       ? "Your stress score increased after the session. This may happen due to external noise, emotional recall, fatigue, or natural variation in voice."
//       : "Your stress score stayed almost the same. That is okay. Stress reduction can require repeated sessions, especially when cognitive load is high.";

//   return (
//     <div className="space-y-6">
//       <AgentCard title="Session Report" text={message} onSpeak={speak} />
//       <div className="grid md:grid-cols-4 gap-4">
//         <BigMetric label="Pre-session" value={`${state.preResult?.score ?? "-"}/10`} />
//         <BigMetric label="Post-session" value={`${state.postResult?.score ?? "-"}/10`} />
//         <BigMetric label="Delta" value={state.comparison ? `${state.comparison.absolute_change > 0 ? "-" : "+"}${Math.abs(state.comparison.absolute_change)}` : "-"} />
//         <BigMetric label="Outcome" value={state.comparison?.outcome || "-"} />
//       </div>
//       <div className="grid lg:grid-cols-3 gap-4">
//         <JsonPanel title="Layer 3 — Comparison" data={state.comparison} />
//         <JsonPanel title="Layer 4 — Cross-modal" data={state.cross} />
//         <JsonPanel title="Layer 5 — Anomaly" data={state.anomaly} />
//       </div>
//       <button onClick={() => setStep("welcome")} className="rounded-2xl bg-white/10 px-6 py-3 font-bold">Start New Session</button>
//     </div>
//   );
// }

// function BigMetric({ label, value }) {
//   return <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6"><div className="text-sm text-white/50">{label}</div><div className="mt-2 text-3xl font-black capitalize">{value}</div></div>;
// }

// function JsonPanel({ title, data }) {
//   return <div className="rounded-[2rem] border border-white/10 bg-black/20 p-5 overflow-hidden"><h3 className="font-bold mb-3">{title}</h3><pre className="text-xs text-cyan-50/70 whitespace-pre-wrap break-words max-h-96 overflow-auto">{data ? JSON.stringify(data, null, 2) : "No data"}</pre></div>;
// }

// export default function App() {
//   const [step, setStep] = useState("welcome");
//   const [state, setState] = useState({});
//   const [loading, setLoading] = useState(false);

//   const analyzeAmbient = async (file) => {
//     setLoading(true);
//     try {
//       const result = await postForm("/ambient-check", {}, { file });
//       setState((s) => ({ ...s, ambientResult: result }));
//       if (result.suitable) {
//         speak("Your environment is suitable for voice assessment. You can continue to the pre-session voice recording.");
//       } else {
//         const firstIssue = result.issues?.[0] ? ` Main issue: ${result.issues[0]}` : "";
//         speak(`The environment is not suitable yet. Please reduce background noise and record the ambient check again.${firstIssue}`);
//       }
//     } finally {
//       setLoading(false);
//     }
//   };

//   const analyzeVoice = async (file, key) => {
//     setLoading(true);
//     try {
//       const result = await postForm("/infer?model=va_regression", {}, { file });
//       setState((s) => ({ ...s, [key]: result, [`${key}File`]: file }));

//       const stage = key === "preResult" ? "Pre-session" : "Post-session";
//       const classLabel = result.stress_class_label || result.stress_label;
//       const confidence = result.classification_confidence
//         ? ` with ${result.classification_confidence} confidence`
//         : "";

//       speak(`${stage} analysis completed. The cognitive stress score is ${result.score} out of ten. Classification: ${classLabel}${confidence}.`);
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <Shell step={step} setStep={setStep}>
//       <AnimatePresence mode="wait">
//         <motion.div key={step} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.25 }}>
//           {step === "welcome" && <Welcome setStep={setStep} />}
//           {step === "intro" && <Intro setStep={setStep} />}
//           {step === "ambient" && <div className="space-y-6"><AgentCard title="Ambient Environment Check" text={AGENT_LINES.ambient} onSpeak={speak} /><AudioInputPanel title="Ambient Check" purpose="ambient" duration={AMBIENT_RECORD_SECONDS} uploadLabel="Upload ambient audio" onAnalyze={analyzeAmbient} result={state.ambientResult} loading={loading} /><div className="flex flex-wrap items-center gap-3"><button onClick={() => setStep("pre")} disabled={!state.ambientResult?.suitable} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">Continue to Pre-session Voice</button>{!state.ambientResult?.suitable && <p className="text-sm text-amber-100/80">Run ambient check until the environment is suitable.</p>}</div></div>}
//           {step === "pre" && <div className="space-y-6"><AgentCard title="Pre-session Voice Assessment" text={AGENT_LINES.pre} onSpeak={speak} /><AudioInputPanel title="Pre-session Voice" purpose="pre" duration={VOICE_RECORD_SECONDS} uploadLabel="Upload pre-session voice file" onAnalyze={(file) => analyzeVoice(file, "preResult")} result={state.preResult} loading={loading} /><button onClick={() => setStep("vr")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">Continue to VR Session</button></div>}
//           {step === "vr" && <VRTimer setStep={setStep} />}
//           {step === "post" && <div className="space-y-6"><AgentCard title="Post-session Voice Assessment" text={AGENT_LINES.post} onSpeak={speak} /><AudioInputPanel title="Post-session Voice" purpose="post" duration={VOICE_RECORD_SECONDS} uploadLabel="Upload post-session voice file" onAnalyze={(file) => analyzeVoice(file, "postResult")} result={state.postResult} loading={loading} /><button disabled={!state.preResult || !state.postResult} onClick={() => setStep("processing")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 disabled:opacity-50">Continue to Processing</button></div>}
//           {step === "processing" && <Processing state={state} setState={setState} setStep={setStep} />}
//           {step === "report" && <Report state={state} setStep={setStep} />}
//         </motion.div>
//       </AnimatePresence>
//     </Shell>
//   );
// }


import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
// import { Activity, Brain, CheckCircle2, CloudUpload, Headphones, Loader2, Mic, PauseCircle, Play, RotateCcw, ShieldCheck, Sparkles, Upload, Waveform, XCircle } from "lucide-react";

import {
  Activity,
  AlertTriangle,
  AudioLines as Waveform,
  Brain,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  CloudUpload,
  Headphones,
  History,
  Loader2,
  Mic,
  PauseCircle,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Upload,
  XCircle,
} from "lucide-react";

// 8001, not 8000: port 8000 is often already taken by other local dev
// servers on this machine, and on macOS a process bound specifically to
// 127.0.0.1 silently wins loopback traffic over one bound to 0.0.0.0 -
// so a clash there fails invisibly instead of throwing "port in use".
const API_BASE = "http://localhost:8001";
const AMBIENT_RECORD_SECONDS = 8;
const VOICE_RECORD_SECONDS = 30;

const STEPS = [
  { id: "welcome", label: "Welcome" },
  { id: "intro", label: "Agent Intro" },
  { id: "ambient", label: "Ambient Check" },
  { id: "pre", label: "Pre Voice" },
  { id: "vr", label: "VR Session" },
  { id: "post", label: "Post Voice" },
  { id: "processing", label: "Processing" },
  { id: "report", label: "Report" },
  { id: "history", label: "History" },
];

const AGENT_LINES = {
  intro:
    "Hi there, I’m Cognify, your AI cognitive state assessment companion. I’ll guide you through a short stress and cognitive energy check before and after your VR meditation session. First, I’ll check whether your environment is suitable for voice recording. Then, I’ll analyse your pre-session voice, guide you through the meditation flow, and compare your post-session voice to evaluate whether your cognitive stress state has changed. This system is designed for research-based wellness support, not medical diagnosis. Let’s begin when you’re ready.",
  ambient:
    "Before we begin, I need to check your surroundings. Please stay silent for a few seconds while I listen to the environment.",
  pre:
    "Now I’d like to understand your current mental state. Tell me honestly, how has your day been so far? Were there any deadlines, pressure, or tasks that stayed on your mind?",
  vr:
    "Your pre-session check is complete. Now begin the VR meditation session. Focus on your breathing and allow your mind to slow down.",
  post:
    "Welcome back. Take a moment and tell me how you feel now compared to before the session. Do your thoughts feel lighter, calmer, or still active?",
  processing:
    "Thank you. I’ll now analyse your pre-session and post-session voice patterns, compare cognitive stress change, validate the baseline with HRV data, and check whether this session follows an expected stress-reduction pattern.",
};

function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

// The v2 backend returns a continuous 0-10 score, not a category label.
// This bucketing exists ONLY for display - the trained model's actual
// output is the continuous score (and valence/arousal behind it).
function stressLabel(score) {
  if (score < 3) return "Calm";
  if (score < 5) return "Mild Stress";
  if (score < 7) return "Moderate Stress";
  return "High Stress";
}

// Readable text for Layer 4's four named mismatch types
// (see src/layer4_crossmodal.py for the detection logic).
function mismatchDetail(type) {
  switch (type) {
    case "vocal_masking":
      return "Your voice sounds calmer than your body's heart-rate signal suggests - this can happen when stress is being consciously controlled in speech.";
    case "cognitive_persistence":
      return "Your body's stress signal recovered, but your voice still shows tension - this can happen when the mind is still processing something.";
    case "baseline_divergence":
      return "Voice and HRV read differently throughout this session, so the baseline comparison is less certain.";
    case "outcome_divergence":
      return "Voice and HRV agreed before the session but diverged afterward.";
    default:
      return "Cross-modal result will appear here.";
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatDate(ts) {
  return new Date(ts).toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getOutcomeStyle(outcome) {
  if (outcome === "reduced") return "border-emerald-300/30 bg-emerald-400/10 text-emerald-100";
  if (outcome === "increased") return "border-rose-300/30 bg-rose-400/10 text-rose-100";
  return "border-amber-300/30 bg-amber-400/10 text-amber-100";
}

function getFemaleVoice() {
  if (!("speechSynthesis" in window)) return null;

  const voices = window.speechSynthesis.getVoices();
  const preferredNames = [
    "Microsoft Zira",
    "Microsoft Sonia",
    "Google UK English Female",
    "Google US English",
    "Samantha",
    "Karen",
    "Moira",
  ];

  for (const name of preferredNames) {
    const found = voices.find((v) => v.name.toLowerCase().includes(name.toLowerCase()));
    if (found) return found;
  }

  return voices.find((v) => v.lang.toLowerCase().startsWith("en")) || voices[0] || null;
}

function speak(text, onDone) {
  if (!("speechSynthesis" in window)) {
    onDone?.();
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.9;
  utterance.pitch = 1.05;
  utterance.volume = 0.95;

  const femaleVoice = getFemaleVoice();
  if (femaleVoice) utterance.voice = femaleVoice;

  utterance.onend = () => onDone?.();
  utterance.onerror = () => onDone?.();
  window.speechSynthesis.speak(utterance);
}

async function postForm(endpoint, fields = {}, files = {}) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  Object.entries(files).forEach(([k, v]) => form.append(k, v));
  const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST", body: form });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      // The v2 API's Layer 1 rejection (422) sends an OBJECT detail:
      // {error, reasons: [...]}. Every other error sends a plain string.
      // Without this check a rejected recording would show "[object
      // Object]" instead of telling the user what was actually wrong.
      if (data.detail && typeof data.detail === "object") {
        msg = data.detail.reasons?.join(", ") || data.detail.error || msg;
      } else {
        msg = data.detail || msg;
      }
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

async function postJson(endpoint, body) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      msg = data.detail || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

function encodeWav(float32Samples, sampleRate) {
  const numChannels = 1;
  const bytesPerSample = 2;
  const blockAlign = numChannels * bytesPerSample;
  const buffer = new ArrayBuffer(44 + float32Samples.length * bytesPerSample);
  const view = new DataView(buffer);

  const writeString = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + float32Samples.length * bytesPerSample, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, float32Samples.length * bytesPerSample, true);

  let offset = 44;
  for (let i = 0; i < float32Samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, float32Samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function mergeFloat32(chunks) {
  const length = chunks.reduce((sum, arr) => sum + arr.length, 0);
  const result = new Float32Array(length);
  let offset = 0;
  chunks.forEach((arr) => {
    result.set(arr, offset);
    offset += arr.length;
  });
  return result;
}

function blobToFile(blob, name) {
  return new File([blob], name, { type: blob.type || "audio/wav" });
}

function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [levels, setLevels] = useState(Array.from({ length: 48 }, () => 0.08));
  const [error, setError] = useState("");

  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const rafRef = useRef(null);
  const stopTimeoutRef = useRef(null);

  const cleanup = async () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    clearInterval(timerRef.current);
    clearTimeout(stopTimeoutRef.current);
    timerRef.current = null;
    stopTimeoutRef.current = null;

    try {
      if (processorRef.current) processorRef.current.disconnect();
      if (sourceRef.current) sourceRef.current.disconnect();
      if (analyserRef.current) analyserRef.current.disconnect();
    } catch {}

    processorRef.current = null;
    sourceRef.current = null;
    analyserRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      try {
        await audioContextRef.current.close();
      } catch {}
    }
    audioContextRef.current = null;
  };

  const stop = async () => {
    if (!isRecording && chunksRef.current.length === 0) return;
    const ctx = audioContextRef.current;
    const sampleRate = ctx?.sampleRate || 44100;
    const samples = mergeFloat32(chunksRef.current);
    const wav = encodeWav(samples, sampleRate);
    setAudioBlob(wav);
    setIsRecording(false);
    await cleanup();
  };

  const start = async ({ autoStopSeconds = null } = {}) => {
    setError("");
    setAudioBlob(null);
    setElapsed(0);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContextClass();
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      const processor = ctx.createScriptProcessor(4096, 1, 1);

      source.connect(analyser);
      analyser.connect(processor);
      processor.connect(ctx.destination);

      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        chunksRef.current.push(new Float32Array(input));
      };

      sourceRef.current = source;
      analyserRef.current = analyser;
      processorRef.current = processor;

      const data = new Uint8Array(analyser.frequencyBinCount);
      const draw = () => {
        analyser.getByteFrequencyData(data);
        const bucketCount = 48;
        const bucketSize = Math.max(1, Math.floor(data.length / bucketCount));
        const next = Array.from({ length: bucketCount }, (_, i) => {
          const startIndex = i * bucketSize;
          const slice = data.slice(startIndex, startIndex + bucketSize);
          const avg = slice.reduce((a, b) => a + b, 0) / Math.max(1, slice.length);
          return clamp(avg / 255, 0.06, 1);
        });
        setLevels(next);
        rafRef.current = requestAnimationFrame(draw);
      };
      draw();

      setIsRecording(true);
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
      if (autoStopSeconds) stopTimeoutRef.current = setTimeout(() => stop(), autoStopSeconds * 1000);
    } catch (err) {
      setError(err.message || "Microphone access failed");
      setIsRecording(false);
      await cleanup();
    }
  };

  useEffect(() => {
    return () => cleanup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { isRecording, elapsed, audioBlob, levels, error, start, stop, setAudioBlob };
}

function Shell({ children, step, setStep }) {
  const index = STEPS.findIndex((s) => s.id === step);
  return (
    <div className="min-h-screen bg-[#07111f] text-white overflow-hidden">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-cyan-500/20 blur-3xl" />
        <div className="absolute top-1/3 -right-40 h-[32rem] w-[32rem] rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute bottom-0 left-1/4 h-80 w-80 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>
      <header className="relative z-10 border-b border-white/10 bg-white/[0.03] backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-cyan-300 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="font-bold tracking-wide text-lg">Cognify</div>
              <div className="text-xs text-cyan-100/70">Cognitive Stress & Energy Assessment</div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs text-white/60">
            {STEPS.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setStep(s.id)}
                className={classNames(
                  "px-3 py-2 rounded-full border transition",
                  i <= index ? "border-cyan-300/50 bg-cyan-300/10 text-cyan-100" : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]"
                )}
              >
                {i + 1}. {s.label}
              </button>
            ))}
          </div>
        </div>
      </header>
      <main className="relative z-10 mx-auto max-w-7xl px-5 py-8">{children}</main>
    </div>
  );
}

function AgentCard({ title, text, onSpeak }) {
  const [visibleChars, setVisibleChars] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const typeTimerRef = useRef(null);

  const shownText = text.slice(0, Math.max(visibleChars, 1));

  const stopTyping = () => {
    if (typeTimerRef.current) {
      clearInterval(typeTimerRef.current);
      typeTimerRef.current = null;
    }
  };

  const startTyping = () => {
    stopTyping();
    setVisibleChars(0);
    typeTimerRef.current = setInterval(() => {
      setVisibleChars((current) => {
        if (current >= text.length) {
          stopTyping();
          return text.length;
        }
        return current + 2;
      });
    }, 25);
  };

  const play = () => {
    startTyping();
    setSpeaking(true);
    speak(text, () => {
      setVisibleChars(text.length);
      setSpeaking(false);
      stopTyping();
    });
  };

  useEffect(() => {
    startTyping();
    return () => stopTyping();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
      <div className="flex items-start gap-4">
        <motion.div
          animate={speaking ? { scale: [1, 1.08, 1], boxShadow: ["0 0 0 rgba(34,211,238,0)", "0 0 32px rgba(34,211,238,.35)", "0 0 0 rgba(34,211,238,0)"] } : { scale: [1, 1.04, 1], rotate: [0, 2, -2, 0] }}
          transition={{ duration: speaking ? 1.4 : 4, repeat: Infinity }}
          className="h-16 w-16 rounded-3xl bg-gradient-to-br from-cyan-300 via-blue-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-cyan-500/20"
        >
          <Sparkles className="h-8 w-8" />
        </motion.div>
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-3">
            <h2 className="text-xl font-semibold">{title}</h2>
            {speaking && <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs text-cyan-100">speaking...</span>}
          </div>
          <div className="relative inline-block max-w-5xl rounded-3xl rounded-tl-md bg-slate-950/35 px-5 py-4 text-white/80 leading-8 border border-white/10">
            {shownText}
            {visibleChars < text.length && <span className="ml-1 animate-pulse text-cyan-200">▌</span>}
          </div>
          <div>
            <button onClick={play} className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-white/10 px-4 py-2 text-sm hover:bg-white/15 transition">
              <Headphones className="h-4 w-4" /> Play Agent Voice
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Visualizer({ levels, active = false }) {
  return (
    <div className="relative rounded-[2rem] border border-cyan-300/20 bg-black/20 p-6 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-300/10 via-transparent to-indigo-500/10" />
      <div className="relative flex h-44 items-center justify-center gap-1.5">
        {levels.map((l, i) => (
          <motion.div
            key={i}
            animate={{ height: `${12 + l * 128}px`, opacity: active ? 1 : 0.35 }}
            transition={{ type: "spring", stiffness: 220, damping: 24 }}
            className="w-2 rounded-full bg-gradient-to-t from-cyan-400 to-white"
          />
        ))}
      </div>
      <div className="relative text-center text-sm text-cyan-100/70">{active ? "Live frequency visualizer — recording WAV audio" : "Visualizer ready"}</div>
    </div>
  );
}

function AudioInputPanel({ title, purpose, duration, uploadLabel, onAnalyze, result, loading }) {
  const recorder = useAudioRecorder();
  const [mode, setMode] = useState("record");
  const [file, setFile] = useState(null);
  const [localError, setLocalError] = useState("");

  const selectedFile = useMemo(() => {
    if (mode === "upload") return file;
    if (recorder.audioBlob) return blobToFile(recorder.audioBlob, `${purpose}_${Date.now()}.wav`);
    return null;
  }, [mode, file, recorder.audioBlob, purpose]);

  const handleAnalyze = async () => {
    setLocalError("");
    if (!selectedFile) {
      setLocalError("Please record live audio or upload an audio file first.");
      return;
    }
    await onAnalyze(selectedFile);
  };

  return (
    <div className="grid lg:grid-cols-[1.1fr_.9fr] gap-6">
      <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3 mb-5">
          <div>
            <h3 className="text-2xl font-bold">{title}</h3>
            <p className="text-white/60 mt-1">Choose live recording or upload a prepared file.</p>
          </div>
          <Waveform className="h-7 w-7 text-cyan-200" />
        </div>

        <div className="grid grid-cols-2 gap-3 mb-5">
          <button onClick={() => setMode("record")} className={classNames("rounded-2xl px-4 py-3 border transition", mode === "record" ? "border-cyan-300 bg-cyan-300/15" : "border-white/10 bg-white/[0.04] hover:bg-white/[0.08]")}> <Mic className="inline h-4 w-4 mr-2" /> Record Live </button>
          <button onClick={() => setMode("upload")} className={classNames("rounded-2xl px-4 py-3 border transition", mode === "upload" ? "border-cyan-300 bg-cyan-300/15" : "border-white/10 bg-white/[0.04] hover:bg-white/[0.08]")}> <Upload className="inline h-4 w-4 mr-2" /> Upload File </button>
        </div>

        <AnimatePresence mode="wait">
          {mode === "record" ? (
            <motion.div key="record" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <Visualizer levels={recorder.levels} active={recorder.isRecording} />
              <div className="mt-5 flex flex-wrap items-center gap-3">
                {!recorder.isRecording ? (
                  <button onClick={() => recorder.start({ autoStopSeconds: duration })} className="rounded-2xl bg-cyan-300 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-200 transition inline-flex items-center gap-2"><Play className="h-4 w-4" /> Start {duration}s Recording</button>
                ) : (
                  <button onClick={recorder.stop} className="rounded-2xl bg-rose-400 px-5 py-3 font-semibold text-white hover:bg-rose-300 transition inline-flex items-center gap-2"><PauseCircle className="h-4 w-4" /> Stop</button>
                )}
                <div className="rounded-2xl border border-white/10 px-4 py-3 text-white/70">Timer: {recorder.elapsed}s / {duration}s</div>
                {recorder.audioBlob && <div className="rounded-2xl bg-emerald-400/10 px-4 py-3 text-emerald-100 border border-emerald-300/20">Recording ready as WAV</div>}
              </div>
              {recorder.error && <p className="mt-3 text-sm text-rose-200">{recorder.error}</p>}
            </motion.div>
          ) : (
            <motion.div key="upload" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
              <label className="flex flex-col items-center justify-center rounded-[2rem] border border-dashed border-cyan-300/30 bg-black/20 p-10 cursor-pointer hover:bg-white/[0.05] transition">
                <CloudUpload className="h-12 w-12 text-cyan-200 mb-3" />
                <span className="font-semibold">{uploadLabel}</span>
                <span className="text-sm text-white/50 mt-1">WAV, WebM, MP3, FLAC supported by backend</span>
                <input type="file" accept="audio/*" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              </label>
              {file && <p className="mt-3 text-sm text-cyan-100">Selected: {file.name}</p>}
            </motion.div>
          )}
        </AnimatePresence>

        {(localError || loading) && <p className={classNames("mt-4 text-sm", localError ? "text-rose-200" : "text-cyan-100")}>{localError || "Processing audio through backend..."}</p>}

        <button onClick={handleAnalyze} disabled={loading} className="mt-5 w-full rounded-2xl bg-gradient-to-r from-cyan-300 to-indigo-400 px-5 py-4 font-bold text-slate-950 hover:opacity-90 disabled:opacity-60 transition inline-flex items-center justify-center gap-2">
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Activity className="h-5 w-5" />} Analyze Audio
        </button>
      </div>

      <ResultCard result={result} purpose={purpose} />
    </div>
  );
}

function AmbientQualityBar({ score }) {
  const value = typeof score === "number" ? Math.max(0, Math.min(100, score)) : 0;
  const good = value >= 70;
  const medium = value >= 45 && value < 70;
  return (
    <div className="rounded-2xl bg-black/20 p-4">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-white/55">Ambient Quality Score</span>
        <span className={classNames("font-bold", good ? "text-emerald-100" : medium ? "text-amber-100" : "text-rose-100")}>{value}/100</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-white/10">
        <div
          className={classNames("h-full rounded-full transition-all", good ? "bg-emerald-300" : medium ? "bg-amber-300" : "bg-rose-300")}
          style={{ width: `${value}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-white/45">Higher score means cleaner background audio for voice stress assessment.</p>
    </div>
  );
}

function AmbientIssues({ issues }) {
  if (!issues || issues.length === 0) return null;
  return (
    <div className="rounded-2xl border border-rose-300/20 bg-rose-400/10 p-4">
      <div className="mb-2 flex items-center gap-2 font-semibold text-rose-100">
        <AlertTriangle className="h-4 w-4" /> Detected Issues
      </div>
      <ul className="list-disc space-y-1 pl-5 text-sm text-rose-100/80">
        {issues.map((issue, index) => (
          <li key={index}>{issue}</li>
        ))}
      </ul>
    </div>
  );
}

function ClassificationReasons({ reasons }) {
  if (!reasons || reasons.length === 0) return null;

  return (
    <div className="rounded-2xl border border-cyan-300/20 bg-cyan-400/10 p-4">
      <div className="mb-2 flex items-center gap-2 font-semibold text-cyan-100">
        <Brain className="h-4 w-4" /> Why this classification?
      </div>
      <ul className="list-disc space-y-1 pl-5 text-sm text-cyan-100/80">
        {reasons.map((reason, index) => (
          <li key={index}>{reason}</li>
        ))}
      </ul>
    </div>
  );
}

function StressClassBadge({ result }) {
  const label = result.stress_class_label || result.stress_label || "Unknown";
  const stressClass = result.stress_class || result.stress_level || "";

  const isStressed =
    stressClass === "stressed" ||
    stressClass === "borderline_stressed" ||
    label.toLowerCase().includes("stress");

  const isBaseline =
    stressClass === "baseline" ||
    label.toLowerCase().includes("baseline");

  const className = isStressed
    ? "bg-rose-400/10 border-rose-300/30 text-rose-100"
    : isBaseline
      ? "bg-amber-400/10 border-amber-300/30 text-amber-100"
      : "bg-emerald-400/10 border-emerald-300/30 text-emerald-100";

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 ${className}`}>
      {isStressed ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
      {label}
    </div>
  );
}

function ResultCard({ result, purpose }) {
  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl min-h-[28rem]">
      <h3 className="text-xl font-bold mb-4">{purpose === "ambient" ? "Ambient Result" : "Voice Analysis Result"}</h3>
      {!result ? (
        <div className="h-full flex flex-col items-center justify-center text-center text-white/50">
          <ShieldCheck className="h-12 w-12 mb-3 text-cyan-200/60" />
          Result will appear here after analysis.
        </div>
      ) : purpose === "ambient" ? (
        <div className="space-y-4">
          <StatusPill good={result.suitable} label={result.suitable ? "Suitable for Recording" : "Not Suitable — Retest Needed"} />
          <AmbientQualityBar score={result.quality_score} />
          <Metric label="Noise Level" value={result.noise_level ?? "N/A"} />
          <Metric label="Duration" value={result.duration_sec ? `${result.duration_sec}s` : "N/A"} />
          <Metric label="RMS Energy" value={result.rms ?? "N/A"} />
          {/* <Metric label="RMS P95" value={result.rms_p95 ?? "N/A"} /> */}
          <Metric label="Peak Noise" value={result.peak ?? "N/A"} />
          <Metric label="ZCR" value={result.zcr ?? "N/A"} />
          <Metric label="Spectral Flatness" value={result.spectral_flatness ?? "N/A"} />
          <AmbientIssues issues={result.issues} />
          <p className={classNames("rounded-2xl p-4 leading-6", result.suitable ? "bg-emerald-400/10 text-emerald-100/85 border border-emerald-300/20" : "bg-rose-400/10 text-rose-100/85 border border-rose-300/20")}>{result.recording_recommendation || result.message}</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-[2rem] bg-black/20 p-5 text-center">
            <div className="text-sm text-white/50">Cognitive Stress Score</div>
            <div className="text-5xl font-black mt-2">
              {result.score}
              <span className="text-xl text-white/50">/10</span>
            </div>

            <div className="mt-4 flex justify-center">
              <StressClassBadge result={result} />
            </div>

            {result.raw_score !== undefined && (
              <div className="mt-2 text-xs text-white/40">
                Raw score: {result.raw_score}/10
              </div>
            )}
          </div>

          <Metric label="Stress Class" value={result.stress_class_label || result.stress_label || "N/A"} />
          <Metric label="Signal Source" value={typeof result.gate_mean === "number" ? `${Math.round(result.gate_mean * 100)}% emotion / ${Math.round((1 - result.gate_mean) * 100)}% prosody` : "N/A"} />
          <Metric label="Confidence" value={result.classification_confidence || "N/A"} />
          {/* <Metric label="Classification Probability" value={result.classification_probability ?? result.probability ?? "N/A"} />
          <Metric label="Detected Emotion" value={result.top_emotion || "Not returned"} />
          <Metric label="Emotion Score" value={result.top_emotion_score ?? "N/A"} />
          <Metric label="Scoring Method" value={result.scoring_method || "single"} /> */}

          {result.stressed_chunk_ratio !== undefined && (
            <Metric label="Stressed Chunk Ratio" value={result.stressed_chunk_ratio} />
          )}

          {/* {result.num_chunks !== undefined && (
            <Metric label="Valid Chunks" value={result.num_chunks} />
          )} */}

          <ClassificationReasons reasons={result.classification_reasons} />

          <p className="rounded-2xl bg-black/20 p-4 text-white/70 leading-6">
            {result.classification_description || result.stress_description}
          </p>
        </div>
      )}
    </div>
  );
}

function StatusPill({ good, label }) {
  return <div className={classNames("inline-flex items-center gap-2 rounded-full px-4 py-2 border", good ? "bg-emerald-400/10 border-emerald-300/30 text-emerald-100" : "bg-rose-400/10 border-rose-300/30 text-rose-100")}>{good ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />} {label}</div>;
}

function Metric({ label, value }) {
  return <div className="flex items-center justify-between rounded-2xl bg-black/20 px-4 py-3"><span className="text-white/50">{label}</span><span className="font-semibold text-right max-w-[60%] truncate">{String(value)}</span></div>;
}

function Welcome({ setStep }) {
  return (
    <div className="grid lg:grid-cols-[1fr_.9fr] gap-8 items-center py-8">
      <div>
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-cyan-100 mb-6"><Sparkles className="h-4 w-4" /> Research demo interface</div>
        <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-tight">Cognify</h1>
        <p className="mt-5 text-2xl text-white/75 max-w-2xl">Cognitive Stress & Energy Assessment for Adaptive VR Meditation</p>
        <p className="mt-5 text-white/55 leading-7 max-w-2xl">A voice-based AI companion that checks environment quality, estimates cognitive stress from speech, compares pre/post meditation changes, validates with HRV baseline data, and flags unusual session patterns.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <button onClick={() => setStep("intro")} className="rounded-2xl bg-cyan-300 px-7 py-4 font-bold text-slate-950 hover:bg-cyan-200 transition inline-flex items-center gap-2"><Play className="h-5 w-5" /> Start Assessment</button>
          <button onClick={() => setStep("history")} className="rounded-2xl bg-white/10 px-7 py-4 font-bold hover:bg-white/15 transition inline-flex items-center gap-2"><History className="h-5 w-5" /> View Sessions</button>
        </div>
      </div>
      <motion.div animate={{ y: [0, -12, 0] }} transition={{ duration: 5, repeat: Infinity }} className="rounded-[3rem] border border-white/10 bg-white/[0.06] p-8 shadow-2xl backdrop-blur-xl">
        <div className="aspect-square rounded-[2.5rem] bg-gradient-to-br from-cyan-300/20 via-indigo-500/20 to-emerald-300/10 border border-white/10 flex items-center justify-center relative overflow-hidden">
          <motion.div animate={{ scale: [1, 1.18, 1], opacity: [0.55, 0.85, 0.55] }} transition={{ duration: 3, repeat: Infinity }} className="absolute h-72 w-72 rounded-full border border-cyan-300/30" />
          <motion.div animate={{ scale: [1.1, 1.35, 1.1], opacity: [0.25, 0.5, 0.25] }} transition={{ duration: 4, repeat: Infinity }} className="absolute h-96 w-96 rounded-full border border-indigo-300/20" />
          <Brain className="h-32 w-32 text-cyan-100 drop-shadow-2xl" />
        </div>
      </motion.div>
    </div>
  );
}

function Intro({ setStep }) {
  return (
    <div className="space-y-6">
      <AgentCard title="Cognify AI Companion" text={AGENT_LINES.intro} onSpeak={speak} />
      <div className="grid md:grid-cols-5 gap-4">
        {["Environment", "Pre Voice", "VR Session", "Post Voice", "Validation"].map((x, i) => <div key={x} className="rounded-3xl border border-white/10 bg-white/[0.05] p-5"><div className="text-cyan-100 text-2xl font-black">0{i + 1}</div><div className="mt-2 text-white/75">{x}</div></div>)}
      </div>
      <button onClick={() => setStep("ambient")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">Continue to Ambient Check</button>
    </div>
  );
}

function VRTimer({ setStep }) {
  const [time, setTime] = useState(60);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    if (!running || time <= 0) return;
    const t = setTimeout(() => setTime((x) => x - 1), 1000);
    return () => clearTimeout(t);
  }, [running, time]);
  useEffect(() => { speak(AGENT_LINES.vr); }, []);
  return (
    <div className="grid lg:grid-cols-[.9fr_1.1fr] gap-6 items-stretch">
      <AgentCard title="VR Meditation Placeholder" text={AGENT_LINES.vr} onSpeak={speak} />
      <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-8 text-center backdrop-blur-xl">
        <motion.div animate={{ scale: [1, 1.04, 1] }} transition={{ duration: 3, repeat: Infinity }} className="mx-auto h-64 w-64 rounded-full border border-cyan-300/30 bg-cyan-300/10 flex items-center justify-center">
          <div>
            <div className="text-7xl font-black">{time}</div>
            <div className="text-white/50">seconds</div>
          </div>
        </motion.div>
        <div className="mt-8 flex justify-center gap-3">
          <button onClick={() => setRunning((r) => !r)} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">{running ? "Pause" : "Start"}</button>
          <button onClick={() => setTime(60)} className="rounded-2xl bg-white/10 px-6 py-3 font-bold"><RotateCcw className="inline h-4 w-4 mr-2" /> Reset</button>
          <button onClick={() => setStep("post")} className="rounded-2xl bg-indigo-400 px-6 py-3 font-bold text-white">Continue</button>
        </div>
      </div>
    </div>
  );
}

function Processing({ state, setState, setStep, saveSession, backendSessionId, userId }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  const run = async () => {
    setError("");
    setRunning(true);
    const steps = [];
    const add = async (label) => {
      steps.push(label);
      setItems([...steps]);
      await sleep(450);
    };

    try {
      if (!backendSessionId) {
        throw new Error("No active session - please record pre and post voice first.");
      }

      await add("Pre-session and post-session voice scores received");
      // v2's /full-session runs Layers 3, 4 and 5 server-side in ONE call
      // (the server already holds both scores, keyed by session_id from
      // the two earlier /infer calls). use_mock_hrv is true because
      // Component B (the wearable) is not wired into this demo yet.
      const full = await postJson("/full-session", {
        session_id: backendSessionId,
        user_id: userId,
        use_mock_hrv: true,
      });

      await add("Stress change calculated");
      await add("HRV baseline validation completed");

      // Normalise the nested v2 response into the {comparison, cross,
      // anomaly} shape Report/HistoryPage already render, so those
      // components need no changes at all.
      const comparison = {
        ...full.comparison,
        outcome: full.comparison.direction === "improved" ? "reduced"
                : full.comparison.direction === "worsened" ? "increased"
                : "stable",
        absolute_change: Math.abs(full.comparison.delta),
        interpretation: !full.comparison.reliable
          ? "The stress level did not change by enough to be reliably measured - this is common and not a problem."
          : full.comparison.direction === "improved"
            ? `Stress decreased by ${Math.abs(full.comparison.delta)} points (${full.comparison.magnitude} change).`
            : `Stress increased by ${Math.abs(full.comparison.delta)} points (${full.comparison.magnitude} change).`,
      };
      const cross = full.crossmodal
        ? { ...full.crossmodal, mismatch_detail: mismatchDetail(full.crossmodal.mismatch_type) }
        : { agreement: null, validated: null };
      const anomaly = full.anomaly
        ? { ...full.anomaly, is_anomalous: full.anomaly.anomaly }
        : { is_anomalous: false, anomaly_direction: null };
      const hrvPre = full.crossmodal?.hrv?.pre ?? null;

      await add("Session flag generated by anomaly detector");
      const session = {
        id: `session_${Date.now()}`,
        createdAt: Date.now(),
        pre: state.preResult,
        post: state.postResult,
        comparison,
        cross,
        anomaly,
        hrvPre,
      };

      setState((s) => ({ ...s, comparison, cross, anomaly, hrvPre, currentSessionId: session.id }));
      saveSession(session);
      await add("Session stored in local history");
      setStep("report");
    } catch (e) {
      setError(e.message || "Validation failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <AgentCard title="Processing Pipeline" text={AGENT_LINES.processing} onSpeak={speak} />
      <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-2xl font-bold">Session Validation</h3>
            <p className="mt-1 text-white/55">This step converts raw scores into a user-friendly session outcome and stores the session.</p>
          </div>
          <button disabled={running} onClick={run} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 inline-flex items-center gap-2 disabled:opacity-50">
            {running ? <Loader2 className="h-5 w-5 animate-spin" /> : <Activity className="h-5 w-5" />} Run Validation
          </button>
        </div>
        <div className="mt-6 grid md:grid-cols-2 gap-3">
          {items.map((it) => (
            <div key={it} className="rounded-2xl bg-emerald-400/10 border border-emerald-300/20 px-4 py-3 text-emerald-100">
              <CheckCircle2 className="inline h-4 w-4 mr-2" /> {it}
            </div>
          ))}
        </div>
        {error && <p className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-400/10 p-4 text-rose-100">{error}</p>}
      </div>
    </div>
  );
}

function Report({ state, setStep }) {
  const pre = state.preResult?.score ?? 0;
  const post = state.postResult?.score ?? 0;
  const preClass = state.preResult?.stress_class_label || state.preResult?.stress_label || "N/A";
  const postClass = state.postResult?.stress_class_label || state.postResult?.stress_label || "N/A";

  const comparison = state.comparison;
  const cross = state.cross;
  const anomaly = state.anomaly;
  const outcome = comparison?.outcome || "pending";
  const reduced = outcome === "reduced";
  const increased = outcome === "increased";

  const mainMessage = reduced
    ? "Your post-session voice score is lower than your pre-session score. This suggests the session may have helped reduce your cognitive stress state."
    : increased
      ? "Your post-session score is higher than before. This does not mean something is wrong. It may be due to fatigue, environment, emotional recall, or natural voice variation. The session is saved for review."
      : "Your score stayed almost the same. That is common, because cognitive stress can take repeated sessions to change. This session is still useful for tracking your pattern.";

  // Layer 5 cannot tell a shockingly GOOD session from a shockingly bad
  // one from reconstruction error alone (see src/layer5_anomaly.py) - it
  // reports anomaly_direction to resolve this. A wellness app must never
  // present a user's best session as an unqualified alarm.
  const isGoodAnomaly = anomaly?.is_anomalous && anomaly?.anomaly_direction === "unusual_improvement";
  const flagLabel = !anomaly?.is_anomalous
    ? "Session Pattern Normal"
    : isGoodAnomaly
      ? "Exceptional Improvement"
      : "Review Suggested";
  const flagGood = !anomaly?.is_anomalous || isGoodAnomaly;

  return (
    <div className="space-y-6">
      <AgentCard title="Session Summary" text={mainMessage} onSpeak={speak} />
      <div className="grid md:grid-cols-4 gap-4">
        <BigMetric label="Before session" value={`${pre}/10`} subValue={preClass} />
        <BigMetric label="After session" value={`${post}/10`} subValue={postClass} />
        <BigMetric label="Change" value={comparison ? `${comparison.delta < 0 ? "↓" : comparison.delta > 0 ? "↑" : "→"} ${Math.abs(comparison.delta)}` : "-"} />
        <BigMetric label="Outcome" value={outcome} highlight={getOutcomeStyle(outcome)} />
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        <InsightCard
          icon={reduced ? TrendingDown : increased ? TrendingUp : Activity}
          title="Stress Change"
          tone={reduced ? "good" : increased ? "warn" : "neutral"}
          value={reduced ? "Reduced" : increased ? "Increased" : "No major change"}
          text={comparison?.interpretation || "The pre/post score comparison will appear here."}
        />
        <InsightCard
          icon={ShieldCheck}
          title="Baseline Validation"
          tone={cross?.validated ? "good" : "warn"}
          value={cross?.validated ? "Voice and HRV agree" : "Voice and HRV differ"}
          text={cross?.validated ? "The voice score and HRV baseline are close enough to support the baseline reading." : cross?.mismatch_detail || "Cross-modal result will appear here."}
        />
        <InsightCard
          icon={flagGood ? CheckCircle2 : AlertTriangle}
          title="Session Flag"
          tone={flagGood ? "good" : "warn"}
          value={flagLabel}
          text={
            isGoodAnomaly
              ? "This session's improvement was unusually large compared to typical sessions - a strong result, not a concern."
              : flagGood
                ? "The session follows the expected stress-reduction pattern."
                : "This session is not failed. It is only marked for review because the pattern was unusual."
          }
        />
      </div>

      <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6">
        <h3 className="text-xl font-bold mb-3">Student-friendly interpretation</h3>
        <p className="text-white/70 leading-7">
          This result is a wellness research estimate, not a medical diagnosis. A single session is only one data point. Cognify stores sessions so patterns can be reviewed over time, especially whether repeated VR meditation sessions gradually move the user from a higher cognitive stress state toward a calmer cognitive state.
        </p>
      </div>

      <AdvancedDetails comparison={comparison} cross={cross} anomaly={anomaly} />

      <div className="flex flex-wrap gap-3">
        <button onClick={() => setStep("history")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 inline-flex items-center gap-2">
          <History className="h-5 w-5" /> View Saved Sessions
        </button>
        <button onClick={() => setStep("welcome")} className="rounded-2xl bg-white/10 px-6 py-3 font-bold hover:bg-white/15">
          Start New Session
        </button>
      </div>
    </div>
  );
}

function BigMetric({ label, value, subValue, highlight }) {
  return (
    <div className={classNames("rounded-[2rem] border border-white/10 bg-white/[0.06] p-6", highlight)}>
      <div className="text-sm text-white/55">{label}</div>
      <div className="mt-2 text-3xl font-black capitalize">{value}</div>
      {subValue && <div className="mt-2 text-sm text-cyan-100/80">{subValue}</div>}
    </div>
  );
}

function InsightCard({ icon: Icon, title, value, text, tone = "neutral" }) {
  const toneClass = tone === "good" ? "text-emerald-100 bg-emerald-400/10 border-emerald-300/20" : tone === "warn" ? "text-amber-100 bg-amber-400/10 border-amber-300/20" : "text-cyan-100 bg-cyan-400/10 border-cyan-300/20";
  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-6">
      <div className={classNames("h-12 w-12 rounded-2xl flex items-center justify-center border mb-4", toneClass)}>
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="font-bold text-lg">{title}</h3>
      <div className="mt-2 text-2xl font-black">{value}</div>
      <p className="mt-3 text-white/60 leading-6 text-sm">{text}</p>
    </div>
  );
}

function AdvancedDetails({ comparison, cross, anomaly }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-[2rem] border border-white/10 bg-black/20 p-5">
      <button onClick={() => setOpen((x) => !x)} className="flex w-full items-center justify-between text-left">
        <div>
          <h3 className="font-bold">Examiner / Technical Details</h3>
          <p className="text-sm text-white/50">Hidden by default so normal users do not see raw JSON.</p>
        </div>
        <ChevronDown className={classNames("h-5 w-5 transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="mt-5 grid lg:grid-cols-3 gap-4">
          <JsonPanel title="Layer 3" data={comparison} />
          <JsonPanel title="Layer 4" data={cross} />
          <JsonPanel title="Layer 5" data={anomaly} />
        </div>
      )}
    </div>
  );
}

function JsonPanel({ title, data }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-950/60 p-5 overflow-hidden">
      <h3 className="font-bold mb-3">{title}</h3>
      <pre className="text-xs text-cyan-50/70 whitespace-pre-wrap break-words max-h-80 overflow-auto">{data ? JSON.stringify(data, null, 2) : "No data"}</pre>
    </div>
  );
}

function HistoryPage({ sessions, clearSessions, setStep, loadSession }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black">Saved Sessions</h1>
          <p className="mt-2 text-white/55">These sessions are stored locally in this browser for demo and progress tracking.</p>
        </div>
        <button onClick={clearSessions} className="rounded-2xl border border-rose-300/30 bg-rose-400/10 px-4 py-3 text-rose-100 hover:bg-rose-400/20">
          Clear History
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-10 text-center text-white/60">
          <CalendarClock className="mx-auto h-12 w-12 text-cyan-100/60 mb-3" />
          No sessions stored yet.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sessions.map((s) => {
            const outcome = s.comparison?.outcome || "unknown";
            const anomalous = s.anomaly?.is_anomalous;
            return (
              <div key={s.id} className="rounded-[2rem] border border-white/10 bg-white/[0.06] p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm text-white/50">{formatDate(s.createdAt)}</div>
                    <div className="mt-2 text-2xl font-black capitalize">{outcome}</div>
                  </div>
                  <StatusPill good={!anomalous} label={anomalous ? "Review" : "Normal"} />
                </div>
                <div className="mt-5 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-2xl bg-black/20 p-3">
                    <div className="text-xs text-white/40">Before</div>
                    <div className="font-bold">{s.pre?.score}</div>
                    <div className="mt-1 text-[10px] text-cyan-100/70">{s.pre?.stress_class_label || s.pre?.stress_label}</div>
                  </div>
                  <div className="rounded-2xl bg-black/20 p-3">
                    <div className="text-xs text-white/40">After</div>
                    <div className="font-bold">{s.post?.score}</div>
                    <div className="mt-1 text-[10px] text-cyan-100/70">{s.post?.stress_class_label || s.post?.stress_label}</div>
                  </div>
                  <div className="rounded-2xl bg-black/20 p-3">
                    <div className="text-xs text-white/40">Delta</div>
                    <div className="font-bold">{s.comparison?.absolute_change}</div>
                  </div>
                </div>
                <button onClick={() => loadSession(s)} className="mt-5 w-full rounded-2xl bg-cyan-300 px-4 py-3 font-bold text-slate-950">
                  Open Report
                </button>
              </div>
            );
          })}
        </div>
      )}

      <button onClick={() => setStep("welcome")} className="rounded-2xl bg-white/10 px-6 py-3 font-bold hover:bg-white/15">
        Back to Home
      </button>
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState("welcome");
  const [state, setState] = useState({});
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("cognify_sessions") || "[]");
    } catch {
      return [];
    }
  });

  // A stable per-installation user id, so Layer 5's anomaly detector
  // builds up a personal baseline across repeated demo sessions on this
  // browser (it switches from a global to a per-user threshold after 5
  // sessions - see src/layer5_anomaly.py on the backend).
  const [userId] = useState(() => {
    let id = localStorage.getItem("cognify_user_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("cognify_user_id", id);
    }
    return id;
  });

  // The backend groups a pre/post pair by session_id (server-side state -
  // see api_server.py's session_scores dict). A fresh id is generated at
  // the start of every pre-session recording so each attempt is isolated.
  const [backendSessionId, setBackendSessionId] = useState(null);

  const persistSessions = (next) => {
    setSessions(next);
    localStorage.setItem("cognify_sessions", JSON.stringify(next));
  };

  const saveSession = (session) => {
    persistSessions([session, ...sessions].slice(0, 30));
  };

  const clearSessions = () => persistSessions([]);

  const loadSession = (session) => {
    setState({
      preResult: session.pre,
      postResult: session.post,
      comparison: session.comparison,
      cross: session.cross,
      anomaly: session.anomaly,
      hrvPre: session.hrvPre,
      currentSessionId: session.id,
    });
    setStep("report");
  };

  const analyzeAmbient = async (file) => {
    setLoading(true);
    try {
      // v2 Layer 1 returns {ok, reasons, metrics}; normalise to the
      // {suitable, issues, message} shape the rest of this file expects,
      // so nothing below this line needs to know the backend changed.
      const raw = await postForm("/ambient-check", {}, { file });
      // v2 has no single 0-100 "quality score" (Layer 1 is pass/fail with
      // reasons, see src/layer1_quality.py) - synthesise one from SNR for
      // the existing progress-bar display, keeping it clearly in the
      // "good" zone (>=70) when passing and "bad" zone (<45) when not,
      // matching the bar's own colour thresholds.
      const qualityScore = raw.ok
        ? Math.round(clamp(70 + (raw.metrics?.snr_db ?? 0), 70, 100))
        : Math.round(clamp(40 - raw.reasons.length * 8, 5, 40));
      const result = {
        ...raw,
        suitable: raw.ok,
        issues: raw.reasons,
        quality_score: qualityScore,
        duration_sec: raw.metrics?.duration_sec,
        rms: raw.metrics?.rms,
        spectral_flatness: raw.metrics?.spectral_flatness,
        message: raw.ok
          ? "Environment is suitable for recording."
          : `Environment not suitable: ${raw.reasons.join(", ")}`,
      };
      setState((s) => ({ ...s, ambientResult: result }));
      if (result.suitable) {
        speak("Your environment is suitable for voice assessment. You can continue to the pre-session voice recording.");
      } else {
        const firstIssue = result.issues?.[0] ? ` Main issue: ${result.issues[0]}` : "";
        speak(`The environment is not suitable yet. Please reduce background noise and record the ambient check again.${firstIssue}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const analyzeVoice = async (file, key) => {
    setLoading(true);
    try {
      const phase = key === "preResult" ? "pre" : "post";

      // Pre-session recording starts a new backend session; post-session
      // must reuse the same id so /full-session can find both scores.
      let sid = backendSessionId;
      if (phase === "pre") {
        sid = crypto.randomUUID();
        setBackendSessionId(sid);
      }
      if (!sid) {
        throw new Error("No active session - please record the pre-session voice first.");
      }

      // v2 Layer 2 returns {stress_score, confidence, valence, arousal,
      // gate_mean, quality}; normalise to the {score, stress_class_label,
      // classification_confidence} shape the rest of this file expects.
      const raw = await postForm(`/infer?session_id=${sid}&phase=${phase}`, {}, { file });
      const result = {
        ...raw,
        score: raw.stress_score,
        stress_class_label: stressLabel(raw.stress_score),
        classification_confidence: `${Math.round(raw.confidence * 100)}%`,
        // Real explainability from the trained model's own internals
        // (not simulated): the gated-fusion weighting between the frozen
        // emotion embedding and the trainable prosody branch - see the
        // "gate" mechanism in src/layer2_fusion.py.
        classification_reasons: [
          `Valence ${raw.valence.toFixed(2)} (${raw.valence < 0 ? "unpleasant" : "pleasant"} tone detected)`,
          `Arousal ${raw.arousal.toFixed(2)} (${raw.arousal > 0 ? "energised/tense" : "calm/subdued"} delivery)`,
          `Fusion weighting: ${Math.round(raw.gate_mean * 100)}% emotional-content signal, ${Math.round((1 - raw.gate_mean) * 100)}% voice-physiology signal`,
        ],
        stress_description: `This score reflects a ${raw.valence < 0 ? "negative" : "positive"}, ${raw.arousal > 0 ? "energised" : "calm"} vocal tone, combined by the trained fusion model.`,
      };
      setState((s) => ({ ...s, [key]: result, [`${key}File`]: file }));

      const stage = key === "preResult" ? "Pre-session" : "Post-session";
      const classLabel = result.stress_class_label;
      const confidence = result.classification_confidence
        ? ` with ${result.classification_confidence} confidence`
        : "";

      speak(`${stage} analysis completed. The cognitive stress score is ${result.score} out of ten. Classification: ${classLabel}${confidence}.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell step={step} setStep={setStep}>
      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.25 }}>
          {step === "welcome" && <Welcome setStep={setStep} />}
          {step === "intro" && <Intro setStep={setStep} />}
          {step === "ambient" && <div className="space-y-6"><AgentCard title="Ambient Environment Check" text={AGENT_LINES.ambient} onSpeak={speak} /><AudioInputPanel title="Ambient Check" purpose="ambient" duration={AMBIENT_RECORD_SECONDS} uploadLabel="Upload ambient audio" onAnalyze={analyzeAmbient} result={state.ambientResult} loading={loading} /><div className="flex flex-wrap items-center gap-3"><button onClick={() => setStep("pre")} disabled={!state.ambientResult?.suitable} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">Continue to Pre-session Voice</button>{!state.ambientResult?.suitable && <p className="text-sm text-amber-100/80">Run ambient check until the environment is suitable.</p>}</div></div>}
          {step === "pre" && <div className="space-y-6"><AgentCard title="Pre-session Voice Assessment" text={AGENT_LINES.pre} onSpeak={speak} /><AudioInputPanel title="Pre-session Voice" purpose="pre" duration={VOICE_RECORD_SECONDS} uploadLabel="Upload pre-session voice file" onAnalyze={(file) => analyzeVoice(file, "preResult")} result={state.preResult} loading={loading} /><button onClick={() => setStep("vr")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950">Continue to VR Session</button></div>}
          {step === "vr" && <VRTimer setStep={setStep} />}
          {step === "post" && <div className="space-y-6"><AgentCard title="Post-session Voice Assessment" text={AGENT_LINES.post} onSpeak={speak} /><AudioInputPanel title="Post-session Voice" purpose="post" duration={VOICE_RECORD_SECONDS} uploadLabel="Upload post-session voice file" onAnalyze={(file) => analyzeVoice(file, "postResult")} result={state.postResult} loading={loading} /><button disabled={!state.preResult || !state.postResult} onClick={() => setStep("processing")} className="rounded-2xl bg-cyan-300 px-6 py-3 font-bold text-slate-950 disabled:opacity-50">Continue to Processing</button></div>}
          {step === "processing" && <Processing state={state} setState={setState} setStep={setStep} saveSession={saveSession} backendSessionId={backendSessionId} userId={userId} />}
          {step === "report" && <Report state={state} setStep={setStep} />}
          {step === "history" && <HistoryPage sessions={sessions} clearSessions={clearSessions} setStep={setStep} loadSession={loadSession} />}
        </motion.div>
      </AnimatePresence>
    </Shell>
  );
}
