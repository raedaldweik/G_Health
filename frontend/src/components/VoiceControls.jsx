import { useCallback, useRef, useState } from 'react';

/**
 * Voice input (Web Speech API, English + Arabic) and optional spoken answers.
 * Phase 2 upgrades this to the Gemini Live API (GA) for native bidirectional audio.
 */
export function VoiceInput({ onTranscript, disabled, lang }) {
  const [listening, setListening] = useState(false);
  const recRef = useRef(null);

  const toggle = useCallback(() => {
    if (listening) {
      recRef.current?.stop();
      setListening(false);
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      alert('Speech recognition is not supported in this browser. Try Chrome.');
      return;
    }
    const rec = new SR();
    rec.lang = lang === 'ar' ? 'ar-QA' : 'en-US';
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      onTranscript?.(text);
      setListening(false);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recRef.current = rec;
    rec.start();
    setListening(true);
  }, [listening, onTranscript, lang]);

  return (
    <button onClick={toggle} disabled={disabled}
      title={`Speak instead of typing (${lang === 'ar' ? 'العربية' : 'English'})`}
      className={`relative w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all ${
        listening ? 'bg-red-500/15 text-red-500' : 'hover:bg-[rgba(138,21,56,0.08)]'
      } disabled:opacity-30`}
      style={!listening ? { color: 'var(--text-dim)' } : {}}>
      {listening && <span className="absolute w-10 h-10 rounded-lg border-2 border-red-400/40 animate-ping" />}
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    </button>
  );
}

const stripMd = (s) => (s || '')
  .replace(/\|[^\n]*\|/g, ' ')             // drop tables from speech
  .replace(/[*_#>`]/g, '')
  .replace(/\[(.*?)\]\(.*?\)/g, '$1')
  .replace(/\s+/g, ' ').trim();

export function useSpeaker() {
  const [speaking, setSpeaking] = useState(false);
  const [enabled, setEnabled] = useState(false);

  const speak = useCallback((text) => {
    if (!enabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(stripMd(text).slice(0, 900));
    u.rate = 1.04;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }, [enabled]);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  }, []);

  return { enabled, setEnabled, speaking, speak, stop };
}

export function SpeakerToggle({ speaker }) {
  return (
    <button
      onClick={() => {
        if (speaker.speaking) speaker.stop();
        speaker.setEnabled(!speaker.enabled);
      }}
      title={speaker.enabled ? 'Spoken answers: on' : 'Spoken answers: off'}
      className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all hover:bg-[rgba(138,21,56,0.08)]"
      style={{ color: speaker.enabled ? 'var(--brand)' : 'var(--text-dim)' }}>
      {speaker.enabled ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" /><path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <line x1="23" y1="9" x2="17" y2="15" /><line x1="17" y1="9" x2="23" y2="15" />
        </svg>
      )}
    </button>
  );
}
