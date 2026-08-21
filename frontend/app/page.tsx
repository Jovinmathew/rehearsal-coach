"use client";

import { useRef, useState } from "react";
import type { FeedbackCategory, ReviewError, ReviewResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Mirrors backend/app/limits.py — enforced there too, this just avoids
// recording (and uploading) more than the server will ever accept.
const MAX_TOPIC_LENGTH = 300;
const MAX_DURATION_SEC = 300;

type Status = "idle" | "recording" | "uploading" | "error";

const CATEGORY_STYLES: Record<FeedbackCategory, string> = {
  clarity: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  structure: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
  pacing: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  coverage: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
};

export default function Home() {
  const [topic, setTopic] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReviewResponse | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const autoStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function startRecording() {
    setError(null);
    setResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        if (autoStopTimerRef.current) clearTimeout(autoStopTimerRef.current);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        streamRef.current?.getTracks().forEach((t) => t.stop());
        submitReview(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      // Belt-and-suspenders against the server's own duration cap — stop on
      // the client before recording something it would just reject anyway.
      autoStopTimerRef.current = setTimeout(stopRecording, MAX_DURATION_SEC * 1000);
    } catch {
      setError("Couldn't access your microphone. Check your browser's permission settings.");
      setStatus("error");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  async function submitReview(blob: Blob) {
    setStatus("uploading");
    setError(null);
    try {
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      formData.append("topic", topic);

      const res = await fetch(`${API_URL}/review`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const body: ReviewError = await res.json();
        setError(body.error || "Something went wrong.");
        setStatus("error");
        return;
      }

      const body: ReviewResponse = await res.json();
      setResult(body);
      setStatus("idle");
    } catch {
      setError("Couldn't reach the server. Is the backend running?");
      setStatus("error");
    }
  }

  const canRecord = topic.trim().length > 0;
  const isRecording = status === "recording";
  const isUploading = status === "uploading";

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      <main className="mx-auto flex max-w-2xl flex-col gap-8 px-6 py-16">
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Rehearsal Coach
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Pick a topic, record yourself talking through it, and get feedback anchored to what you actually said.
          </p>
        </header>

        <section className="flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <label className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Topic</span>
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                {topic.length}/{MAX_TOPIC_LENGTH}
              </span>
            </div>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={isRecording || isUploading}
              maxLength={MAX_TOPIC_LENGTH}
              placeholder="e.g. why our onboarding flow is too long"
              className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 outline-none focus:border-zinc-500 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </label>

          <div className="flex items-center gap-3">
            {!isRecording ? (
              <button
                onClick={startRecording}
                disabled={!canRecord || isUploading}
                className="flex items-center gap-2 rounded-full bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
              >
                <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
                Record
              </button>
            ) : (
              <button
                onClick={stopRecording}
                className="flex items-center gap-2 rounded-full bg-red-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-white" />
                Stop
              </button>
            )}
            {isUploading && (
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                Transcribing and reviewing your take…
              </span>
            )}
            {!canRecord && !isRecording && (
              <span className="text-sm text-zinc-400 dark:text-zinc-500">Enter a topic first</span>
            )}
          </div>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-400">
              {error}
            </p>
          )}
        </section>

        {result && (
          <section className="flex flex-col gap-6">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Words" value={result.stats.word_count} />
              <Stat label="Duration" value={`${result.stats.duration_sec.toFixed(1)}s`} />
              <Stat label="WPM" value={result.stats.wpm.toFixed(0)} />
              <Stat label="Filler words" value={result.stats.filler_count} />
            </div>

            {result.stats.filler_examples.length > 0 && (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                Fillers used: {result.stats.filler_examples.join(", ")}
              </p>
            )}

            <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                Transcript
              </h2>
              <p className="text-zinc-800 dark:text-zinc-200">
                {result.transcript || <span className="italic text-zinc-400">No speech detected.</span>}
              </p>
            </div>

            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
                Feedback
              </h2>
              {result.feedback.length === 0 ? (
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  No feedback items passed grounding for this take.
                </p>
              ) : (
                result.feedback.map((item, i) => (
                  <div
                    key={i}
                    className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${CATEGORY_STYLES[item.category]}`}
                    >
                      {item.category}
                    </span>
                    <blockquote className="mt-3 border-l-2 border-zinc-300 pl-3 text-sm italic text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
                      &ldquo;{item.quote}&rdquo;
                    </blockquote>
                    <p className="mt-3 text-sm text-zinc-800 dark:text-zinc-200">{item.issue}</p>
                    <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">→ {item.suggestion}</p>
                  </div>
                ))
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{value}</div>
      <div className="text-xs text-zinc-500 dark:text-zinc-400">{label}</div>
    </div>
  );
}
