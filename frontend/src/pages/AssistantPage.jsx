import { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getScenarios, streamChat } from '../services/api';
import ResponseCard from '../components/ResponseCard';
import SourceViewer from '../components/SourceViewer';
import DetailsPopup from '../components/DetailsPopup';
import ToolTrace from '../components/ToolTrace';
import { VoiceInput, SpeakerToggle, useSpeaker } from '../components/VoiceControls';
import { AgentChip } from '../components/ui';

export default function AssistantPage() {
  const { persona, personaInfo, messages, addMessage, patchLastMessage, resetChat, sessionId } = useApp();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [liveSteps, setLiveSteps] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [llmInfo, setLlmInfo] = useState(null);
  const [source, setSource] = useState(null);
  const [details, setDetails] = useState(null);
  const [voiceLang, setVoiceLang] = useState('en');
  const speaker = useSpeaker();
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    getScenarios(persona).then((r) => {
      setScenarios(r.scenarios || []);
      setLlmInfo({ enabled: r.llm_enabled, model: r.model });
    }).catch(() => setScenarios([]));
  }, [persona]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, liveSteps, loading]);

  const send = async (text, scenarioId = null) => {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput('');
    addMessage({ role: 'user', content: q });
    setLoading(true);
    setLiveSteps([]);
    try {
      let finalData = null;
      await streamChat({ message: q, sessionId, persona, scenarioId }, (ev) => {
        if (ev.type === 'step') {
          setLiveSteps((prev) => [...prev, ev]);
        } else if (ev.type === 'final') {
          finalData = ev;
        }
      });
      if (finalData) {
        addMessage({ role: 'assistant', data: finalData, query: q });
        speaker.speak(finalData.answer);
      } else {
        addMessage({ role: 'assistant', error: 'The stream ended without an answer — try again.' });
      }
    } catch (e) {
      addMessage({ role: 'assistant', error: `Connection error: ${e.message}` });
    }
    setLoading(false);
    setLiveSteps([]);
    inputRef.current?.focus();
  };

  const liveVisible = liveSteps.filter((s) => s.status === 'done').slice(-6);

  return (
    <div className="h-full flex gap-4 p-4">
      {/* Left rail: scenario chips + agents online */}
      <div className="w-[280px] shrink-0 flex flex-col gap-4 min-h-0">
        <div className="glass-card p-4 shrink-0">
          <p className="panel-title mb-3">Suggested scenarios</p>
          <div className="flex flex-col gap-2">
            {scenarios.map((s) => (
              <button key={s.id} className="suggestion-chip !justify-start text-left"
                disabled={loading}
                onClick={() => send(s.question, s.id)}>
                <span className="chip-tag">{s.tag}</span>
                <span className="truncate">{s.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="glass-card p-4 flex-1 min-h-0 overflow-y-auto">
          <p className="panel-title mb-3">Agent system</p>
          {[
            ['nabd_supervisor', 'Gemini supervisor — plans & routes'],
            ['cohort_agent', 'HIE structured queries'],
            ['guideline_agent', 'Guideline RAG + citations'],
            ['risk_agent', 'ML scoring · simulation · forecast'],
            ['pophealth_agent', 'population-health MCP server ★'],
            ['action_agent', 'Human-in-the-loop drafts'],
          ].map(([a, d]) => (
            <div key={a} className="flex items-start gap-2 mb-2.5">
              <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                style={{ background: 'var(--green)', animation: 'pulse-dot 2.4s infinite' }} />
              <div className="min-w-0">
                <AgentChip agent={a} />
                <p className="text-[10px] mt-0.5 leading-snug" style={{ color: 'var(--text-dim)' }}>{d}</p>
              </div>
            </div>
          ))}
          <div className="mt-3 pt-3 border-t border-[rgba(15,23,42,0.07)] text-[10px]" style={{ color: 'var(--text-faint)' }}>
            {llmInfo?.enabled
              ? <>Live multi-agent · <b style={{ color: 'var(--text-dim)' }}>{llmInfo.model}</b></>
              : <>Scripted engine · live data (set GEMINI_API_KEY for free-form)</>}
          </div>
        </div>
      </div>

      {/* Chat column */}
      <div className="flex-1 glass-card flex flex-col relative min-w-0" style={{ boxShadow: 'var(--glass-shadow-lg)' }}>
        <img src="/nabd-mark.svg" alt="" className="chat-watermark" />

        <div className="flex items-center justify-between px-6 py-3 border-b border-[rgba(15,23,42,0.07)] relative z-[5]">
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-[3px] h-4 rounded shrink-0" style={{ background: 'var(--brand-grad)' }} />
            <span className="text-sm font-bold truncate" style={{ color: 'var(--text)' }}>
              Nabd Assistant
            </span>
            <span className="text-[10.5px] px-2 py-0.5 rounded-full font-semibold"
              style={{ background: 'rgba(26,115,232,0.08)', color: 'var(--brand-lo)' }}>
              {personaInfo.sub}
            </span>
          </div>
          <button onClick={resetChat}
            className="text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all"
            style={{ border: '1px dashed rgba(26,115,232,0.35)', color: 'var(--brand)' }}>
            + New conversation
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 relative z-[1]">
          {messages.length === 0 && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center px-8">
              <img src="/nabd-mark.svg" alt="" className="w-14 h-14 mb-4 opacity-90" />
              <p className="text-[15px] font-bold mb-1" style={{ color: 'var(--text)' }}>
                {persona === 'clinician' ? `Good morning, ${personaInfo.name.split(' ')[1]}.` : `Welcome, ${personaInfo.name}.`}
              </p>
              <p className="text-[12px] max-w-[400px] leading-relaxed" style={{ color: 'var(--text-dim)' }}>
                Ask anything about the {persona === 'clinician' ? 'panel' : 'national registry'} — I query the
                HIE, ground answers in national guidelines, score risk with deployed ML models, and draft
                actions for your approval. Try a scenario on the left, type, or use the mic.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-2.5 animate-fade-up ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {msg.role === 'user' ? (
                <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-[10px] font-bold text-white ${personaInfo.color}`}>
                  {personaInfo.avatar}
                </div>
              ) : (
                <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center p-1"
                  style={{ background: 'var(--nav-grad)', border: '1px solid rgba(66,133,244,0.3)' }}>
                  <img src="/nabd-mark.svg" alt="Nabd" className="w-full h-full object-contain" />
                </div>
              )}
              <div className="max-w-[78%] min-w-0">
                {msg.role === 'user' ? (
                  <div className="msg-user-bubble px-4 py-3 text-[13px] leading-[1.75]" style={{ color: 'var(--text)' }}>
                    {msg.content}
                  </div>
                ) : msg.error ? (
                  <div className="msg-bot-bubble px-4 py-3 text-[13px]" style={{ color: 'var(--red)' }}>
                    {msg.error}
                  </div>
                ) : (
                  <ResponseCard data={msg.data}
                    onOpenSource={setSource}
                    onOpenDetails={(d) => setDetails({ data: d, query: msg.query })} />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-2.5 animate-fade-up">
              <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center p-1"
                style={{ background: 'var(--nav-grad)', border: '1px solid rgba(66,133,244,0.3)' }}>
                <img src="/nabd-mark.svg" alt="" className="w-full h-full object-contain" />
              </div>
              <div className="msg-bot-bubble px-4 py-3 min-w-[240px]">
                {liveVisible.length > 0 && (
                  <div className="mb-2.5 space-y-1.5">
                    {liveVisible.map((s, i, arr) => (
                      <div key={i} className="flex items-center gap-2 text-[11.5px] animate-fade-up"
                        style={{ color: i === arr.length - 1 ? 'var(--brand-lo)' : 'var(--text-dim)' }}>
                        <AgentChip agent={s.agent} />
                        <span className="truncate font-mono text-[10.5px]">{s.tool}</span>
                        <span className="truncate text-[10.5px] flex-1">{s.detail}</span>
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" className="shrink-0">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map((j) => (
                      <span key={j} className="w-1.5 h-1.5 rounded-full"
                        style={{ background: 'var(--brand)', opacity: 0.3, animation: `pop 1.4s ease-in-out infinite ${j * 0.15}s` }} />
                    ))}
                  </div>
                  <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                    {liveSteps.filter((s) => s.status === 'done').length > 0
                      ? `${liveSteps.filter((s) => s.status === 'done').length} agent steps so far`
                      : 'agents working…'}
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input bar */}
        <div className="px-5 pb-4 pt-2 relative z-[1]">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-xl border border-[rgba(15,23,42,0.10)] transition-all focus-within:border-[var(--brand-hi)] focus-within:shadow-[0_0_0_3px_rgba(26,115,232,0.10)]"
            style={{ background: 'var(--glass-strong)', backdropFilter: 'blur(12px)' }}>
            <VoiceInput onTranscript={(t) => send(t)} disabled={loading} lang={voiceLang} />
            <button onClick={() => setVoiceLang(voiceLang === 'en' ? 'ar' : 'en')}
              title="Toggle voice language (English / العربية)"
              className="h-8 px-1.5 rounded-lg text-[10px] font-bold shrink-0 transition-all hover:bg-[rgba(26,115,232,0.08)]"
              style={{ color: 'var(--text-dim)' }}>
              {voiceLang === 'en' ? 'EN' : 'ع'}
            </button>
            <SpeakerToggle speaker={speaker} />
            <textarea ref={inputRef} rows="1" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={`Ask about the ${persona === 'clinician' ? 'panel' : 'population'} — data, guidelines, risk, what-ifs…`}
              className="flex-1 bg-transparent border-none outline-none text-[13px] py-2 px-2 resize-none leading-relaxed"
              style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--text)' }} />
            <button onClick={() => send()}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0 hover:scale-105 transition-transform"
              style={{ background: 'var(--brand-grad)', boxShadow: '0 3px 12px rgba(26,115,232,0.30)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {source && <SourceViewer source={source} onClose={() => setSource(null)} />}
      {details && (
        <DetailsPopup data={details.data} query={details.query}
          onClose={() => setDetails(null)} onOpenSource={setSource} />
      )}
    </div>
  );
}
